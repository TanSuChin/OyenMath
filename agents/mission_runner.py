"""
OyenMath Autonomous AI Learning Platform - Mission Lifecycle Coordinator & Background Runner
Milestone M3: Manages lifecycle, concurrency locks, persistence, and resource budget enforcement.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set, Union

from langgraph.types import Command

from .checkpoint import (
    BaseMissionCheckpointer,
    CheckpointNotFoundError,
    get_default_checkpointer,
)
from .graph import build_autonomous_mission_graph
from .state import (
    ActivityStatus,
    BudgetState,
    MissionGoal,
    MissionState,
    MissionStatus,
    StudentResponse,
    create_initial_mission_state,
    mission_state_from_dict,
    mission_state_to_dict,
    now_utc_iso,
)

logger = logging.getLogger("oyen.mission_runner")


class MissionRunner:
    """
    Autonomous Mission Runner & Lifecycle Coordinator.
    Coordinates creation, execution, pause, resume, cancellation, and background execution
    of persistent autonomous learning missions with strict budget limits and atomic checkpoints.
    """

    def __init__(
        self,
        checkpointer: Optional[BaseMissionCheckpointer] = None,
        max_workers: int = 4,
        llm: Optional[Any] = None,
    ) -> None:
        self.checkpointer = checkpointer or get_default_checkpointer()
        self.langgraph_checkpointer = self.checkpointer.get_langgraph_checkpointer()
        self.llm = llm
        self.graph = build_autonomous_mission_graph(
            checkpointer=self.langgraph_checkpointer,
            llm=self.llm,
        )

        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="oyen_mission_worker_",
        )
        self._mission_locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.Lock()
        self._active_futures: Dict[str, Future] = {}
        self._paused_missions: Set[str] = set()
        self._cancelled_missions: Set[str] = set()

    def _get_mission_lock(self, mission_id: str) -> threading.RLock:
        """Retrieve or construct a thread-safe mutex lock for a specific mission."""
        with self._global_lock:
            if mission_id not in self._mission_locks:
                self._mission_locks[mission_id] = threading.RLock()
            return self._mission_locks[mission_id]

    def _sync_checkpoint(self, state: Union[MissionState, Dict[str, Any]]) -> MissionState:
        """Save state to persistent storage and return validated MissionState object."""
        if isinstance(state, dict):
            # Clean up non-serializable LangGraph internals if present
            clean_dict = dict(state)
            clean_dict.pop("__interrupt__", None)
            model_state = mission_state_from_dict(clean_dict)
        else:
            model_state = state

        self.checkpointer.save_checkpoint(model_state)
        return model_state

    def _check_and_enforce_budget(self, state: MissionState) -> bool:
        """Check if resource budget is exhausted; if so, transition status and persist."""
        budget = getattr(state, "budget", None)
        if budget and budget.is_exhausted():
            reason = budget.exhaustion_reason() or "step_budget_exhausted"
            state.status = MissionStatus.BUDGET_EXHAUSTED
            state.termination_reason = reason
            state.terminated_at = now_utc_iso()
            self._sync_checkpoint(state)
            return True
        return False

    # -------------------------------------------------------------------------
    # Mission Lifecycle Operations
    # -------------------------------------------------------------------------

    def create_mission(
        self,
        student_id: str = "dev-local",
        goal: Optional[Union[str, Dict[str, Any], MissionGoal]] = None,
        topic_id: str = "dif",
        target_mastery: float = 0.80,
        budget: Optional[Union[BudgetState, Dict[str, Any]]] = None,
        language: str = "ms",
        initial_mastery: Optional[Dict[str, float]] = None,
        **kwargs: Any,
    ) -> MissionState:
        """
        Create and persist a new autonomous learning mission.
        Initializes structured MissionState, validates defaults, and saves initial checkpoint.
        """
        # Normalize goal input into dict/MissionGoal for create_initial_mission_state
        goal_param = goal
        if isinstance(goal, str):
            goal_param = {
                "topic": topic_id,
                "description": goal,
                "target_mastery": target_mastery,
            }
        elif goal is None:
            goal_param = {
                "topic": topic_id,
                "description": f"Master SPM Additional Mathematics: {topic_id.upper()}",
                "target_mastery": target_mastery,
            }

        state = create_initial_mission_state(
            student_id=student_id,
            goal=goal_param,
            topic_id=topic_id,
            budget=budget,  # type: ignore[arg-type]
            initial_mastery=initial_mastery,
            **kwargs,
        )
        if language in ("ms", "en"):
            state.language = language  # type: ignore[assignment]

        state.status = MissionStatus.CREATED
        self._sync_checkpoint(state)
        logger.info(f"Created mission {state.mission_id} for student {student_id} (topic: {topic_id})")
        return state

    def start_mission(
        self,
        mission_id: str,
        student_id: Optional[str] = None,
        background: bool = False,
    ) -> MissionState:
        """
        Start execution of an existing mission.
        Runs through preparation nodes until pausing at student_interaction or completing.
        Can execute synchronously or asynchronously in a background worker thread.
        """
        lock = self._get_mission_lock(mission_id)
        with lock:
            state = self.get_mission(mission_id, student_id=student_id)
            if state is None:
                raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")

            # Terminal check
            if state.status in (
                MissionStatus.COMPLETED,
                MissionStatus.FAILED,
                MissionStatus.CANCELLED,
                MissionStatus.BUDGET_EXHAUSTED,
            ):
                return state

            # Check and enforce budget before starting
            if self._check_and_enforce_budget(state):
                return state

            if background:
                # Update state status to RUNNING in storage
                state.status = MissionStatus.RUNNING
                self._sync_checkpoint(state)
                future = self.executor.submit(
                    self._run_mission_worker,
                    mission_id=mission_id,
                    resume_value=None,
                    student_id=student_id,
                )
                with self._global_lock:
                    self._active_futures[mission_id] = future
                return state

            return self._run_mission_worker(
                mission_id=mission_id,
                resume_value=None,
                student_id=student_id,
            )

    def resume_mission(
        self,
        mission_id: str,
        student_response: Union[str, Dict[str, Any], StudentResponse],
        student_id: Optional[str] = None,
        background: bool = False,
    ) -> MissionState:
        """
        Resume execution of an interrupted mission with a student's answer.
        Supplies Command(resume=student_response) to the LangGraph execution cycle.
        """
        lock = self._get_mission_lock(mission_id)
        with lock:
            state = self.get_mission(mission_id, student_id=student_id)
            if state is None:
                raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")

            # Terminal check
            if state.status in (
                MissionStatus.COMPLETED,
                MissionStatus.FAILED,
                MissionStatus.CANCELLED,
                MissionStatus.BUDGET_EXHAUSTED,
            ):
                return state

            if self._check_and_enforce_budget(state):
                return state

            # Normalize response
            if isinstance(student_response, StudentResponse):
                resume_data = student_response.to_dict()
            elif isinstance(student_response, dict):
                resume_data = student_response
            else:
                resume_data = {"answer": str(student_response), "submitted_at": now_utc_iso()}

            # If mission is unstarted (CREATED), cleanly start it first without dropping response
            if state.status == MissionStatus.CREATED:
                state = self.start_mission(mission_id, student_id=student_id, background=False)
                if state.status in (
                    MissionStatus.COMPLETED,
                    MissionStatus.FAILED,
                    MissionStatus.CANCELLED,
                    MissionStatus.BUDGET_EXHAUSTED,
                ):
                    return state

            if background:
                state.status = MissionStatus.RUNNING
                self._sync_checkpoint(state)
                future = self.executor.submit(
                    self._run_mission_worker,
                    mission_id=mission_id,
                    resume_value=resume_data,
                    student_id=student_id,
                )
                with self._global_lock:
                    self._active_futures[mission_id] = future
                return state

            return self._run_mission_worker(
                mission_id=mission_id,
                resume_value=resume_data,
                student_id=student_id,
            )

    def pause_mission(
        self,
        mission_id: str,
        student_id: Optional[str] = None,
    ) -> MissionState:
        """Pause execution of a running mission."""
        lock = self._get_mission_lock(mission_id)
        with lock:
            state = self.get_mission(mission_id, student_id=student_id)
            if state is None:
                raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")
            if state.status not in (
                MissionStatus.COMPLETED,
                MissionStatus.FAILED,
                MissionStatus.CANCELLED,
                MissionStatus.BUDGET_EXHAUSTED,
            ):
                state.status = MissionStatus.PAUSED
                self._paused_missions.add(mission_id)
                state = self._sync_checkpoint(state)
                logger.info(f"Mission {mission_id} marked PAUSED.")
            return state

    def resume_paused_mission(
        self,
        mission_id: str,
        student_id: Optional[str] = None,
        background: bool = False,
    ) -> MissionState:
        """Resume execution of a paused mission."""
        lock = self._get_mission_lock(mission_id)
        with lock:
            state = self.get_mission(mission_id, student_id=student_id)
            if state is None:
                raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")
            self._paused_missions.discard(mission_id)
            if state.status == MissionStatus.PAUSED:
                state.status = MissionStatus.RUNNING
                state = self._sync_checkpoint(state)

            # Continue execution
            return self.start_mission(mission_id, student_id=student_id, background=background)

    def cancel_mission(
        self,
        mission_id: str,
        student_id: Optional[str] = None,
    ) -> MissionState:
        """Cancel and terminate a mission."""
        lock = self._get_mission_lock(mission_id)
        with lock:
            state = self.get_mission(mission_id, student_id=student_id)
            if state is None:
                raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")
            state.status = MissionStatus.CANCELLED
            state.terminated_at = now_utc_iso()
            state.termination_reason = "cancelled_by_student"
            self._cancelled_missions.add(mission_id)
            state = self._sync_checkpoint(state)
            logger.info(f"Mission {mission_id} marked CANCELLED.")
            return state

    def get_mission(
        self,
        mission_id: str,
        student_id: Optional[str] = None,
    ) -> MissionState:
        """Retrieve current MissionState from persistent storage."""
        return self.checkpointer.load_checkpoint(mission_id, student_id=student_id)

    def list_missions(
        self,
        student_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List summary metadata for missions owned by student (or all if omitted)."""
        return self.checkpointer.list_missions(student_id=student_id)

    # -------------------------------------------------------------------------
    # Core Graph Execution Worker
    # -------------------------------------------------------------------------

    def _run_mission_worker(
        self,
        mission_id: str,
        resume_value: Optional[Any] = None,
        student_id: Optional[str] = None,
    ) -> MissionState:
        """
        Worker routine executing the compiled StateGraph with mutex locking.
        Handles interrupts, checkpoint synchronization, and budget checking.
        """
        # Dynamically pick up newly added GROQ_API_KEY / ANTHROPIC_API_KEY from .env without requiring server restart
        if self.llm is None:
            from .graph import default_client
            live_client = default_client()
            if live_client is not None:
                self.llm = live_client
                self.graph = build_autonomous_mission_graph(
                    checkpointer=self.langgraph_checkpointer,
                    llm=self.llm,
                )

        lock = self._get_mission_lock(mission_id)
        with lock:
            state = self.get_mission(mission_id, student_id=student_id)
            if state is None:
                raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")

            # Check if cancelled or paused prior to execution
            if mission_id in self._cancelled_missions or state.status == MissionStatus.CANCELLED:
                return state
            if mission_id in self._paused_missions or state.status == MissionStatus.PAUSED:
                return state

            # Check resource budget
            if self._check_and_enforce_budget(state):
                return state

            config = {"configurable": {"thread_id": mission_id}}

            # Determine whether this is a fresh start or a resumption from interrupt
            if resume_value is not None:
                invoke_target = Command(resume=resume_value)
            else:
                # Mark status as RUNNING while executing
                state.status = MissionStatus.RUNNING
                self._sync_checkpoint(state)
                invoke_target = state

            try:
                # Execute graph until next interrupt or terminal END node
                raw_out = self.graph.invoke(invoke_target, config)

                # Process interrupt state or normal completion
                if isinstance(raw_out, dict):
                    clean_dict = dict(raw_out)
                    interrupts = clean_dict.pop("__interrupt__", None)
                    updated_state = mission_state_from_dict(clean_dict)

                    # If an interrupt was triggered, ensure status is WAITING_FOR_STUDENT
                    if interrupts and len(interrupts) > 0:
                        updated_state.status = MissionStatus.WAITING_FOR_STUDENT
                        int_val = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
                        if isinstance(int_val, dict):
                            updated_state.waiting_interaction = int_val
                elif isinstance(raw_out, MissionState):
                    updated_state = raw_out
                else:
                    updated_state = state

            except Exception as exc:
                logger.error(f"Error during graph execution of mission {mission_id}: {exc}", exc_info=True)
                state.status = MissionStatus.FAILED
                state.terminated_at = now_utc_iso()
                state.termination_reason = f"Execution error: {exc}"
                updated_state = state
                self._sync_checkpoint(updated_state)

            # Enforce budget post-step
            self._check_and_enforce_budget(updated_state)

            # Synchronize checkpoint to persistent storage
            saved_state = self._sync_checkpoint(updated_state)
            return saved_state

    def shutdown(self, wait: bool = True) -> None:
        """Cleanly shut down the background thread worker pool."""
        self.executor.shutdown(wait=wait)
        logger.info("MissionRunner background executor shut down.")
