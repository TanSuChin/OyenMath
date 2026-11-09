"""
OyenMath Autonomous AI Learning Platform - Core Mission State Schema
Milestone M1: Persistent Typed State Model for LangGraph 1.2.14 & REST APIs.

Provides:
- MissionState model with dual compatibility: LangGraph StateGraph, Pydantic v2, and dictionary access
- Enums: MissionStatus, GoalType, ActivityType, ActivityStatus
- Models: MissionGoal, ActivityDef, LearningPlan, BudgetState, VerificationResult, StudentResponse, MisconceptionDef
- Reducer: append_trace for StateGraph trace channel
- Serialization helpers: mission_state_to_dict, mission_state_from_dict, validate_mission_state
- State factory: create_initial_mission_state
- Budget and lifecycle transition helpers: is_budget_exhausted, can_transition, is_terminal_status, is_active_status
- 100% backward compatibility with legacy AgentState (from_legacy, to_legacy_dict)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import json
import math
import time
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    TypedDict,
    Union,
    cast,
)
import uuid
from typing_extensions import Annotated
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


# =====================================================================
# Reducer Functions for LangGraph
# =====================================================================

def append_trace(
    existing: Optional[List[str]],
    update: Union[str, List[str], None]
) -> List[str]:
    """
    Binary operator reducer for StateGraph(MissionState) trace channel.
    Safely appends a single string or list of strings to the existing trace list.
    Preserves order, handles None, and prevents TypeErrors when nodes yield single strings.
    """
    res = list(existing) if existing is not None else []
    if update is None:
        return res
    if isinstance(update, str):
        if update:
            res.append(update)
    elif isinstance(update, (list, tuple)):
        for item in update:
            if item is not None and str(item):
                res.append(str(item))
    return res


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


# =====================================================================
# Status Enums and Transition Rules
# =====================================================================

class MissionStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_STUDENT = "WAITING_FOR_STUDENT"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


VALID_MISSION_STATUSES: Set[str] = {s.value for s in MissionStatus}
TERMINAL_STATUSES: Set[str] = {
    MissionStatus.COMPLETED.value,
    MissionStatus.FAILED.value,
    MissionStatus.CANCELLED.value,
}
ACTIVE_STATUSES: Set[str] = {
    MissionStatus.RUNNING.value,
    MissionStatus.WAITING_FOR_STUDENT.value,
    MissionStatus.QUEUED.value,
}

VALID_TRANSITIONS: Dict[str, Set[str]] = {
    MissionStatus.CREATED.value: {
        MissionStatus.QUEUED.value,
        MissionStatus.RUNNING.value,
        MissionStatus.CANCELLED.value,
        MissionStatus.FAILED.value,
    },
    MissionStatus.QUEUED.value: {
        MissionStatus.RUNNING.value,
        MissionStatus.CANCELLED.value,
        MissionStatus.PAUSED.value,
        MissionStatus.FAILED.value,
    },
    MissionStatus.RUNNING.value: {
        MissionStatus.WAITING_FOR_STUDENT.value,
        MissionStatus.PAUSED.value,
        MissionStatus.COMPLETED.value,
        MissionStatus.FAILED.value,
        MissionStatus.CANCELLED.value,
        MissionStatus.BUDGET_EXHAUSTED.value,
    },
    MissionStatus.WAITING_FOR_STUDENT.value: {
        MissionStatus.RUNNING.value,
        MissionStatus.PAUSED.value,
        MissionStatus.CANCELLED.value,
        MissionStatus.FAILED.value,
        MissionStatus.BUDGET_EXHAUSTED.value,
    },
    MissionStatus.PAUSED.value: {
        MissionStatus.RUNNING.value,
        MissionStatus.CANCELLED.value,
        MissionStatus.FAILED.value,
    },
    MissionStatus.COMPLETED.value: set(),
    MissionStatus.FAILED.value: set(),
    MissionStatus.CANCELLED.value: set(),
    MissionStatus.BUDGET_EXHAUSTED.value: {
        MissionStatus.RUNNING.value,
        MissionStatus.CANCELLED.value,
        MissionStatus.PAUSED.value,
    },
}

class ActivityStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class ActivityType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    TEACHING = "teaching"
    CHALLENGE = "challenge"
    PREREQUISITE = "prerequisite"
    REVIEW = "review"


class GoalType(str, Enum):
    MASTER_TOPIC = "mastery"
    REMEDIATION = "remediation"
    PREREQUISITE_REVIEW = "prerequisite_review"
    EXAM_DRILL = "exam_drill"


# =====================================================================
# Base Model with Dictionary-like Access Protocol
# =====================================================================

class DictCompatibleModel(BaseModel):
    """
    Pydantic v2 BaseModel providing full dictionary interface protocol:
    __getitem__, __setitem__, __contains__, get, keys, values, items, __iter__.
    Allows seamless usage in LangGraph nodes, legacy dict functions, and object access.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def __getitem__(self, item: str) -> Any:
        if item in self:
            return getattr(self, item)
        raise KeyError(item)

    def __setitem__(self, item: str, value: Any) -> None:
        setattr(self, item, value)

    def __contains__(self, item: str) -> bool:
        if not isinstance(item, str):
            return False
        return (item in type(self).model_fields) or (
            self.__pydantic_extra__ is not None and item in self.__pydantic_extra__
        )

    def get(self, item: str, default: Any = None) -> Any:
        if item in self:
            return getattr(self, item)
        return default

    def keys(self) -> Any:
        return self.model_dump().keys()

    def values(self) -> Any:
        return self.model_dump().values()

    def items(self) -> Any:
        return self.model_dump().items()

    def __iter__(self) -> Iterator[str]:
        return iter(self.model_dump())


# =====================================================================
# Sub-Models
# =====================================================================

class MissionGoal(DictCompatibleModel):
    """Learning goal specification."""
    topic_id: str = "dif"
    topic: str = "dif"
    target_mastery: float = Field(default=0.80, ge=0.0, le=1.0)
    goal_type: str = "mastery"
    type: str = "mastery"
    description: Optional[str] = None

    @field_validator("topic_id", "topic", mode="before")
    @classmethod
    def sync_topic_id(cls, v: Any, info: Any = None) -> str:
        return str(v or "dif")


GoalDef = MissionGoal
GoalModel = MissionGoal


class ActivityDef(DictCompatibleModel):
    """Definition of a single learning activity or challenge within a plan."""
    activity_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    type: str = "challenge"
    topic: str = "dif"
    level: int = 1
    difficulty: int = 1
    title: str = ""
    description: Optional[str] = None
    content: Optional[str] = None
    question: Optional[str] = None
    expected_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    student_answer: Optional[str] = None
    solution_steps: List[str] = Field(default_factory=list)
    status: str = "PENDING"
    agent_assigned: str = "teaching"
    target_concept: Optional[str] = None
    target_score: float = 0.80
    is_prerequisite: bool = False
    metadata: Optional[Dict[str, Any]] = None


ActivityModel = ActivityDef


class LearningPlan(DictCompatibleModel):
    """Adaptive learning plan comprising ordered activities."""
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    topic: str = "dif"
    target_topic: str = "dif"
    target_mastery: float = Field(default=0.80, ge=0.0, le=1.0)
    current_step_index: int = 0
    current_index: int = 0
    activities: List[ActivityDef] = Field(default_factory=list)
    estimated_steps: int = 5
    adaptive_replan_count: int = 0
    created_at: str = Field(default_factory=now_utc_iso)
    updated_at: str = Field(default_factory=now_utc_iso)


LearningPlanModel = LearningPlan


class BudgetState(DictCompatibleModel):
    """Resource budget and execution counter limits."""
    max_steps: int = Field(default=30, ge=1)
    steps_taken: int = Field(default=0, ge=0)
    max_tokens: int = Field(default=100000, ge=1000)
    tokens_used: int = Field(default=0, ge=0)
    max_duration_seconds: int = Field(default=1800, ge=30)
    elapsed_seconds: float = Field(default=0.0, ge=0.0)
    started_at: Optional[Union[float, str]] = None
    tool_calls_count: int = Field(default=0, ge=0)
    max_tool_calls: int = Field(default=50, ge=1)
    max_retries: int = Field(default=3, ge=1)
    retry_count: int = Field(default=0, ge=0)
    cost_estimate_usd: float = Field(default=0.0, ge=0.0)

    @field_validator("max_steps", mode="before")
    @classmethod
    def validate_max_steps(cls, v: Any) -> int:
        try:
            return max(1, int(v))
        except (ValueError, TypeError):
            return 30

    @field_validator("max_tokens", mode="before")
    @classmethod
    def validate_max_tokens(cls, v: Any) -> int:
        try:
            return max(1000, int(v))
        except (ValueError, TypeError):
            return 100000

    @field_validator("max_duration_seconds", mode="before")
    @classmethod
    def validate_max_duration(cls, v: Any) -> int:
        try:
            return max(30, int(v))
        except (ValueError, TypeError):
            return 1800

    @field_validator("max_tool_calls", mode="before")
    @classmethod
    def validate_max_tool_calls(cls, v: Any) -> int:
        try:
            return max(1, int(v))
        except (ValueError, TypeError):
            return 50

    @field_validator("max_retries", mode="before")
    @classmethod
    def validate_max_retries(cls, v: Any) -> int:
        try:
            return max(1, int(v))
        except (ValueError, TypeError):
            return 3

    def is_exhausted(self) -> bool:
        """Return True if any resource limit is met or exceeded."""
        if self.steps_taken >= self.max_steps:
            return True
        if self.tool_calls_count >= self.max_tool_calls:
            return True
        if self.tokens_used >= self.max_tokens:
            return True
        if self.started_at:
            now_sec = time.time()
            start_sec = None
            if isinstance(self.started_at, (int, float)):
                start_sec = float(self.started_at)
            elif isinstance(self.started_at, str):
                try:
                    dt = datetime.fromisoformat(self.started_at)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    start_sec = dt.timestamp()
                except Exception:
                    pass
            if start_sec is not None and (now_sec - start_sec) >= self.max_duration_seconds:
                return True
        return False

    def exhaustion_reason(self) -> Optional[str]:
        """Return human-readable explanation of exhausted limit, or None."""
        if self.steps_taken >= self.max_steps:
            return f"step_budget_exhausted (steps {self.steps_taken}/{self.max_steps})"
        if self.tool_calls_count >= self.max_tool_calls:
            return f"tool_call_budget_exhausted (calls {self.tool_calls_count}/{self.max_tool_calls})"
        if self.tokens_used >= self.max_tokens:
            return f"token_budget_exhausted (tokens {self.tokens_used}/{self.max_tokens})"
        if self.started_at:
            now_sec = time.time()
            start_sec = None
            if isinstance(self.started_at, (int, float)):
                start_sec = float(self.started_at)
            elif isinstance(self.started_at, str):
                try:
                    dt = datetime.fromisoformat(self.started_at)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    start_sec = dt.timestamp()
                except Exception:
                    pass
            if start_sec is not None:
                elapsed = now_sec - start_sec
                if elapsed >= self.max_duration_seconds:
                    return f"duration_budget_exhausted (elapsed {int(elapsed)}s/{self.max_duration_seconds}s)"
        return None

    def record_step(self) -> None:
        self.steps_taken += 1

    def record_tool_call(self) -> None:
        self.tool_calls_count += 1

    def record_tokens(self, count: int) -> None:
        self.tokens_used += max(0, count)


BudgetModel = BudgetState


class VerificationResult(DictCompatibleModel):
    """Deterministic mathematical verification output from SymPy engine."""
    verified_by: str = "none"  # "sympy" | "rule" | "mock" | "none" | "unverified"
    is_correct: bool = False
    is_valid_syntax: bool = True
    is_mathematically_equivalent: bool = False
    algebraic_difference: Optional[str] = None
    symbolic_diff: Optional[str] = None
    constant_of_integration_valid: Optional[bool] = None
    sympy_verified: bool = False
    error_type: Optional[str] = None
    error_tag: Optional[str] = None
    feedback: Optional[str] = None
    diagnostic_explanation: Optional[str] = None
    execution_time_ms: Optional[float] = None


VerificationResultModel = VerificationResult


class StudentResponse(DictCompatibleModel):
    """Student submission received by /api/missions/{id}/respond."""
    answer: str = ""
    raw_answer: str = ""
    image_data: Optional[str] = None
    submitted_at: Optional[Union[float, str]] = Field(default_factory=now_utc_iso)
    ocr_result: Optional[Dict[str, Any]] = None


StudentResponseModel = StudentResponse


class MisconceptionDef(DictCompatibleModel):
    """Diagnosed misconception or prerequisite knowledge gap."""
    tag: str = ""
    description: str = ""
    confidence: str = "sederhana"
    count: int = Field(default=1, ge=1)
    prerequisite_gap: bool = False
    first_observed_at: Optional[str] = Field(default_factory=now_utc_iso)
    last_observed_at: Optional[str] = Field(default_factory=now_utc_iso)
    resolved: bool = False


MisconceptionModel = MisconceptionDef


class MissionHistoryItem(DictCompatibleModel):
    """Archival record of a completed activity step."""
    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    activity: Optional[Dict[str, Any]] = None
    student_response: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=now_utc_iso)


MissionHistoryItemModel = MissionHistoryItem


# =====================================================================
# Top-Level MissionState Model
# =====================================================================

class MissionState(DictCompatibleModel):
    """
    Core persistent state model for OyenMath Autonomous Platform.
    Compatible with:
    1. LangGraph 1.2.14 StateGraph(MissionState) with Annotated[List[str], append_trace]
    2. Python dictionary subscript access: state["topic_id"], state.get("trace", [])
    3. Python attribute access: state.mission_id, state.budget.steps_taken
    4. Pydantic v2 validation, serialization, and round-trip JSON conversion
    5. Legacy AgentState compatibility via from_legacy and to_legacy_dict
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Core Identifiers
    mission_id: str = Field(default_factory=lambda: f"m_{uuid.uuid4().hex[:12]}")
    student_id: str = "dev-local"
    topic_id: str = "dif"
    language: Literal["ms", "en"] = "ms"

    # Execution & Lifecycle Status
    status: MissionStatus = MissionStatus.CREATED

    # Planning & Objective
    goal: MissionGoal = Field(default_factory=MissionGoal)
    plan: LearningPlan = Field(default_factory=LearningPlan)
    current_activity: Optional[ActivityDef] = None
    current_agent: str = "goal_understanding"

    # Student Interaction & Deterministic Verification
    student_response: Optional[StudentResponse] = None
    verification: Optional[VerificationResult] = None
    waiting_interaction: Optional[Dict[str, Any]] = None

    # Student Mastery & Diagnostics
    mastery: Dict[str, float] = Field(default_factory=dict)
    verified_mastery: Dict[str, float] = Field(default_factory=dict)
    initial_mastery: Dict[str, float] = Field(default_factory=dict)
    identified_misconceptions: List[MisconceptionDef] = Field(default_factory=list)
    error_tags: Dict[str, int] = Field(default_factory=dict)
    completed_activities: List[Dict[str, Any]] = Field(default_factory=list)
    learning_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Gamification
    hearts: int = Field(default=5, ge=0)
    max_hearts: int = Field(default=5, ge=1)
    xp_points: int = Field(default=0, ge=0)
    fish_coins: int = Field(default=0, ge=0)
    streak: int = Field(default=0, ge=0)

    # Resource Limiting & Budget
    budget: BudgetState = Field(default_factory=BudgetState)

    # Execution Trace (aggregated across nodes via append_trace reducer)
    trace: Annotated[List[str], append_trace] = Field(default_factory=list)

    # Timestamps & Lifecycle Metadata
    created_at: str = Field(default_factory=now_utc_iso)
    updated_at: str = Field(default_factory=now_utc_iso)
    terminated_at: Optional[str] = None
    termination_reason: Optional[str] = None

    # Historical Activity Trail
    history: List[MissionHistoryItem] = Field(default_factory=list)

    # Legacy AgentState Compatibility Fields (agents/graph.py:20-27)
    payload: Optional[Dict[str, Any]] = None
    diagnosis: Optional[Dict[str, Any]] = None
    action: Optional[str] = None
    message: Optional[str] = None
    next_topic: Optional[str] = None

    # -----------------------------------------------------------------
    # Field Validators
    # -----------------------------------------------------------------

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> MissionStatus:
        if isinstance(v, MissionStatus):
            return v
        if isinstance(v, str):
            clean = v.strip().upper()
            if clean in VALID_MISSION_STATUSES:
                return MissionStatus(clean)
            raise ValueError(f"Invalid mission status '{v}'. Allowed: {sorted(VALID_MISSION_STATUSES)}")
        return v

    @field_validator(
        "trace",
        "completed_activities",
        "learning_history",
        "history",
        "identified_misconceptions",
        mode="before",
    )
    @classmethod
    def coerce_none_to_list(cls, v: Any) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            return list(v)
        return [v]

    @field_validator(
        "mastery",
        "verified_mastery",
        "initial_mastery",
        "error_tags",
        mode="before",
    )
    @classmethod
    def coerce_none_to_dict(cls, v: Any) -> Dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return dict(v)
        return {}

    @field_validator("mastery", "initial_mastery", "verified_mastery")
    @classmethod
    def validate_mastery_range(cls, v: Dict[str, float]) -> Dict[str, float]:
        res = {}
        for topic, score in v.items():
            try:
                val = float(score)
                if math.isnan(val) or (math.isinf(val) and val < 0):
                    res[str(topic)] = 0.0
                elif math.isinf(val) and val > 0:
                    res[str(topic)] = 1.0
                else:
                    res[str(topic)] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                res[str(topic)] = 0.0
        return res

    # -----------------------------------------------------------------
    # Export & Backward Compatibility Helpers
    # -----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to a clean JSON-serializable dictionary."""
        return self.model_dump(mode="json")

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Export to legacy AgentState output format expected by test_agents.py."""
        return {
            "diagnosis": self.diagnosis or {},
            "action": self.action or "teach",
            "next_topic": self.next_topic,
            "message": self.message or "",
            "trace": list(self.trace),
            "llm": False,
        }

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "MissionState":
        """
        Construct a valid MissionState from a legacy AgentState or /api/agent request payload.
        Ensures zero regression with legacy tests.
        """
        if not isinstance(data, dict):
            data = {}
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        topic = str(payload.get("topic") or data.get("topic") or "dif")
        now = now_utc_iso()

        # Extract trace
        raw_tr = data.get("trace") or payload.get("trace") or []
        trace_list = [str(t) for t in raw_tr] if isinstance(raw_tr, (list, tuple)) else []

        goal = MissionGoal(
            topic_id=topic,
            topic=topic,
            target_mastery=float(payload.get("target_mastery", 0.8)),
            goal_type="mastery",
        )

        return cls(
            mission_id=f"m_legacy_{uuid.uuid4().hex[:8]}",
            student_id="dev-local",
            topic_id=topic,
            status=MissionStatus.CREATED,
            goal=goal,
            plan=LearningPlan(topic=topic, target_topic=topic),
            payload=payload if isinstance(payload, dict) else None,
            diagnosis=data.get("diagnosis"),
            action=data.get("action"),
            message=data.get("message"),
            next_topic=data.get("next_topic"),
            trace=trace_list,
            created_at=now,
            updated_at=now,
        )


MissionStateModel = MissionState
AgentState = MissionState


# Optional TypedDict representation for static type checkers
class MissionStateDict(TypedDict, total=False):
    mission_id: str
    student_id: str
    topic_id: str
    language: str
    status: str
    goal: Dict[str, Any]
    plan: Dict[str, Any]
    current_activity: Optional[Dict[str, Any]]
    current_agent: str
    student_response: Optional[Dict[str, Any]]
    verification: Optional[Dict[str, Any]]
    mastery: Dict[str, float]
    verified_mastery: Dict[str, float]
    initial_mastery: Dict[str, float]
    identified_misconceptions: List[Dict[str, Any]]
    hearts: int
    max_hearts: int
    xp_points: int
    fish_coins: int
    streak: int
    budget: Dict[str, Any]
    trace: List[str]
    created_at: str
    updated_at: str
    history: List[Dict[str, Any]]
    payload: Optional[Dict[str, Any]]
    diagnosis: Optional[Dict[str, Any]]
    action: Optional[str]
    message: Optional[str]
    next_topic: Optional[str]


# =====================================================================
# Factory Functions
# =====================================================================

def create_initial_budget(
    max_steps: int = 30,
    max_tokens: int = 100000,
    max_duration_seconds: int = 1800,
    max_tool_calls: int = 50,
) -> BudgetState:
    """Create a new initialized BudgetState model."""
    return BudgetState(
        max_steps=max(1, int(max_steps)),
        steps_taken=0,
        max_tokens=max(1000, int(max_tokens)),
        tokens_used=0,
        max_duration_seconds=max(30, int(max_duration_seconds)),
        elapsed_seconds=0.0,
        started_at=None,
        tool_calls_count=0,
        max_tool_calls=max(1, int(max_tool_calls)),
    )


def create_initial_plan(topic: str = "dif", target_mastery: float = 0.8) -> LearningPlan:
    """Create an empty initialized LearningPlan model."""
    now = now_utc_iso()
    return LearningPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        topic=topic,
        target_topic=topic,
        target_mastery=target_mastery,
        activities=[],
        current_step_index=0,
        current_index=0,
        created_at=now,
        updated_at=now,
        adaptive_replan_count=0,
    )


def create_initial_mission_state(
    mission_id: Optional[str] = None,
    student_id: str = "dev-local",
    topic_id: Optional[str] = "dif",
    goal: Optional[Dict[str, Any]] = None,
    budget: Optional[Dict[str, Any]] = None,
    initial_mastery: Optional[Dict[str, float]] = None,
    hearts: int = 5,
    max_hearts: int = 5,
    xp_points: int = 0,
    fish_coins: int = 0,
    streak: int = 0,
) -> MissionState:
    """
    Construct a clean, valid MissionState ready for LangGraph StateGraph execution.
    Populates all defaults, generates mission_id if omitted, and harmonizes mastery.
    """
    mid = mission_id or f"m_{uuid.uuid4().hex[:12]}"
    now = now_utc_iso()

    # Harmonize goal & topic
    top = str(topic_id or "dif")
    g_topic = str(goal.get("topic") or top) if goal else top
    target_m = float(goal.get("target_mastery", 0.8)) if goal else 0.8
    g_type = str(goal.get("type", "mastery")) if goal else "mastery"
    goal_obj = MissionGoal(
        topic_id=g_topic,
        topic=g_topic,
        target_mastery=target_m,
        goal_type=g_type,
        type=g_type,
        description=goal.get("description") if goal else None,
    )

    # Harmonize budget with strict validation & clamping
    if isinstance(budget, BudgetState):
        b_obj = budget
    elif isinstance(budget, dict):
        b_dict = {
            "max_steps": max(1, int(budget.get("max_steps", 30))) if "max_steps" in budget else 30,
            "max_tokens": max(1000, int(budget.get("max_tokens", 100000))) if "max_tokens" in budget else 100000,
            "max_duration_seconds": max(30, int(budget.get("max_duration_seconds", 1800))) if "max_duration_seconds" in budget else 1800,
            "max_tool_calls": max(1, int(budget.get("max_tool_calls", 50))) if "max_tool_calls" in budget else 50,
        }
        b_obj = create_initial_budget(**b_dict)
        if "max_retries" in budget:
            b_obj.max_retries = max(1, int(budget["max_retries"]))
        if "started_at" in budget and budget["started_at"] is not None:
            b_obj.started_at = budget["started_at"]
        if "steps_taken" in budget:
            b_obj.steps_taken = max(0, int(budget["steps_taken"]))
        if "tokens_used" in budget:
            b_obj.tokens_used = max(0, int(budget["tokens_used"]))
        if "tool_calls_count" in budget:
            b_obj.tool_calls_count = max(0, int(budget["tool_calls_count"]))
        if "cost_estimate_usd" in budget:
            b_obj.cost_estimate_usd = max(0.0, float(budget["cost_estimate_usd"]))
    else:
        b_obj = create_initial_budget()

    # Harmonize mastery
    init_m = {str(k): float(v) for k, v in (initial_mastery or {}).items()}
    current_m = dict(init_m)
    if g_topic not in current_m:
        current_m[g_topic] = 0.0

    return MissionState(
        mission_id=mid,
        student_id=student_id or "dev-local",
        topic_id=g_topic,
        status=MissionStatus.CREATED,
        goal=goal_obj,
        plan=create_initial_plan(topic=g_topic, target_mastery=target_m),
        current_activity=None,
        current_agent="goal_understanding",
        student_response=None,
        verification=None,
        mastery=current_m,
        verified_mastery=dict(current_m),
        initial_mastery=init_m,
        identified_misconceptions=[],
        hearts=max(0, int(hearts)),
        max_hearts=max(1, int(max_hearts)),
        xp_points=max(0, int(xp_points)),
        fish_coins=max(0, int(fish_coins)),
        streak=max(0, int(streak)),
        budget=b_obj,
        trace=[f"Mission created at {now}"],
        created_at=now,
        updated_at=now,
        terminated_at=None,
        termination_reason=None,
        history=[],
    )


# =====================================================================
# Serialization & Deserialization Helpers
# =====================================================================

def mission_state_to_dict(state: Union[MissionState, Dict[str, Any], BaseModel]) -> Dict[str, Any]:
    """
    Serialize a MissionState or dictionary into a pure JSON-serializable dictionary.
    Handles nested models, Pydantic objects, UUIDs, and datetime values.
    """
    if isinstance(state, BaseModel):
        return state.model_dump(mode="json")

    if not isinstance(state, dict):
        raise TypeError(f"Expected dict or BaseModel, got {type(state).__name__}")

    try:
        model = MissionState.model_validate(state)
        return model.model_dump(mode="json")
    except Exception:
        return _sanitize_dict(dict(state))


def _sanitize_dict(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable primitives."""
    if isinstance(obj, dict):
        return {str(k): _sanitize_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_sanitize_dict(x) for x in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    elif hasattr(obj, "__dict__"):
        return _sanitize_dict(vars(obj))
    return obj


def mission_state_from_dict(data: Dict[str, Any], validate: bool = True) -> MissionState:
    """
    Reconstruct a typed MissionState from a dictionary.
    If validate=True, executes Pydantic v2 validation and fills missing defaults.
    If validate=False, fills missing defaults via lightweight dict merging.
    """
    if not isinstance(data, dict):
        raise TypeError(f"data must be a dict, got {type(data).__name__}")

    if validate:
        return MissionState.model_validate(data)

    raw = dict(data)
    mid = str(raw.get("mission_id") or f"m_{uuid.uuid4().hex[:12]}")
    stu = str(raw.get("student_id") or "dev-local")
    top = str(raw.get("topic_id") or "dif")
    now = now_utc_iso()

    raw.setdefault("mission_id", mid)
    raw.setdefault("student_id", stu)
    raw.setdefault("topic_id", top)
    raw.setdefault("status", MissionStatus.CREATED)
    raw.setdefault("current_agent", "goal_understanding")
    raw.setdefault("mastery", {})
    raw.setdefault("initial_mastery", {})
    raw.setdefault("verified_mastery", {})
    raw.setdefault("identified_misconceptions", [])
    raw.setdefault("hearts", 5)
    raw.setdefault("max_hearts", 5)
    raw.setdefault("xp_points", 0)
    raw.setdefault("fish_coins", 0)
    raw.setdefault("streak", 0)
    raw.setdefault("trace", [])
    raw.setdefault("history", [])
    raw.setdefault("created_at", now)
    raw.setdefault("updated_at", now)

    return MissionState.model_validate(raw)


def validate_mission_state(state: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a mission state dictionary against MissionState.
    Returns (True, []) on success, or (False, [error_messages]) on validation failure.
    """
    try:
        MissionState.model_validate(state)
        return True, []
    except ValidationError as err:
        errors = [f"{e['loc']}: {e['msg']}" for e in err.errors()]
        return False, errors
    except Exception as ex:
        return False, [str(ex)]


# =====================================================================
# Lifecycle & Transition Helper Functions
# =====================================================================

def can_transition(current_status: Union[str, MissionStatus], target_status: Union[str, MissionStatus]) -> bool:
    """Check if transitioning from current_status to target_status is allowed."""
    c_str = current_status.value if isinstance(current_status, MissionStatus) else str(current_status).strip().upper()
    t_str = target_status.value if isinstance(target_status, MissionStatus) else str(target_status).strip().upper()
    allowed = VALID_TRANSITIONS.get(c_str, set())
    return t_str in allowed


def is_terminal_status(status: Union[str, MissionStatus]) -> bool:
    """Return True if status is a terminal mission state (COMPLETED, FAILED, CANCELLED)."""
    s_str = status.value if isinstance(status, MissionStatus) else str(status).strip().upper()
    return s_str in TERMINAL_STATUSES


def is_active_status(status: Union[str, MissionStatus]) -> bool:
    """Return True if mission is currently active or runnable."""
    s_str = status.value if isinstance(status, MissionStatus) else str(status).strip().upper()
    return s_str in ACTIVE_STATUSES


def is_budget_exhausted(budget: Union[BudgetState, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Evaluate whether execution resource limits have been exceeded.
    Returns (True, reason) if exhausted, or (False, None) if budget remains.
    """
    if isinstance(budget, BudgetState):
        return budget.is_exhausted(), budget.exhaustion_reason()

    if not isinstance(budget, dict):
        return False, None

    max_steps = int(budget.get("max_steps", 30))
    steps_taken = int(budget.get("steps_taken", 0))
    if steps_taken >= max_steps:
        return True, f"step_budget_exhausted (steps {steps_taken}/{max_steps})"

    max_tokens = int(budget.get("max_tokens", 100000))
    tokens_used = int(budget.get("tokens_used", 0))
    if tokens_used >= max_tokens:
        return True, f"token_budget_exhausted (tokens {tokens_used}/{max_tokens})"

    max_tool_calls = int(budget.get("max_tool_calls", 50))
    tool_calls_count = int(budget.get("tool_calls_count", 0))
    if tool_calls_count >= max_tool_calls:
        return True, f"tool_call_budget_exhausted (calls {tool_calls_count}/{max_tool_calls})"

    max_dur = int(budget.get("max_duration_seconds", 1800))
    started_at = budget.get("started_at")
    if started_at:
        try:
            if isinstance(started_at, (int, float)):
                st = datetime.fromtimestamp(float(started_at), timezone.utc)
            else:
                st = datetime.fromisoformat(str(started_at))
                if st.tzinfo is None:
                    st = st.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - st).total_seconds()
            if elapsed >= max_dur:
                return True, f"duration_budget_exhausted (elapsed {int(elapsed)}s/{max_dur}s)"
        except Exception:
            pass

    return False, None
