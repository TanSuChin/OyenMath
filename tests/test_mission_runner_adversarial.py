"""
tests/test_mission_runner_adversarial.py - Adversarial Stress & Pathological Edge-Case Suite
Empirical validation of agents/mission_runner.py under concurrent, pathological, and edge-case conditions:
1. Concurrency Stress (multi-threaded race conditions, chaos storms, lock contention)
2. Invalid Transition Stress (forbidden state transitions, idempotency, non-existent missions)
3. Resource Exhaustion Edge Cases (clamping, max_steps exhaustion, duration expiry)
4. Crash & Recovery Stress (mid-execution corruption, hard worker shutdown, history recovery)
"""

from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import threading
import time
import unittest

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents.checkpoint import (
    CheckpointCorruptedError,
    OyenFileCheckpointer,
)
from agents.mission_runner import MissionRunner
from agents.state import MissionStatus, StudentResponse


class TestMissionRunnerConcurrencyStress(unittest.TestCase):
    """Area 1: Concurrency Stress & Race-Condition Immunity."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)
        self.runner = MissionRunner(checkpointer=self.checkpointer, max_workers=8)

    def tearDown(self):
        self.runner.shutdown(wait=False)
        self.temp_dir.cleanup()

    def test_concurrent_starts_single_mission(self):
        """
        Fire 10 simultaneous start_mission calls on the same mission_id from multiple threads.
        Per-mission lock must serialize execution, preventing race conditions or corrupted files.
        """
        m = self.runner.create_mission(student_id="concurrent_user", topic_id="dif")
        results = []
        errors = []

        def worker_start():
            try:
                res = self.runner.start_mission(m.mission_id)
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_start) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        self.assertEqual(len(errors), 0, f"Errors during concurrent starts: {errors}")
        self.assertEqual(len(results), 10)

        # Check final persistent state
        final_state = self.runner.get_mission(m.mission_id)
        self.assertIsNotNone(final_state)
        self.assertIn(final_state.status, (MissionStatus.WAITING_FOR_STUDENT, MissionStatus.RUNNING))
        self.assertTrue(final_state.waiting_interaction is not None)

    def test_concurrent_resumes_same_mission(self):
        """
        A mission is WAITING_FOR_STUDENT. Multiple threads fire resume_mission concurrently.
        Mutex locking must ensure each resume is handled in order without race corruption.
        """
        m = self.runner.create_mission(student_id="resume_user", topic_id="dif")
        self.runner.start_mission(m.mission_id)

        responses = ["6*x", "12*(3*x - 2)^3", "10*x + 4", "6*x", "6*x"]
        results = []
        errors = []

        def worker_resume(ans):
            try:
                res = self.runner.resume_mission(m.mission_id, student_response=ans)
                results.append((res.status, res.verified_mastery.get("dif", 0.0)))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_resume, args=(ans,)) for ans in responses]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        self.assertEqual(len(errors), 0, f"Errors during concurrent resumes: {errors}")
        self.assertEqual(len(results), len(responses))

        # Check final persistent state
        final_state = self.runner.get_mission(m.mission_id)
        self.assertIsNotNone(final_state)
        self.assertGreater(final_state.verified_mastery.get("dif", 0.0), 0.0)

        # Concurrency integrity: no resume call should have silently aborted and returned RUNNING
        statuses = [s for s, _ in results]
        self.assertNotIn(
            MissionStatus.RUNNING,
            statuses,
            f"Silent graph error detected! Resumes returned orphaned RUNNING status: {statuses}",
        )
        self.assertNotEqual(
            final_state.status,
            MissionStatus.RUNNING,
            "Mission is orphaned in RUNNING state due to internal concurrency crash!",
        )

    def test_concurrent_start_pause_resume_cancel_storm(self):
        """
        Stress test: 16 threads hammer start, pause, resume_paused, and cancel in random order.
        Verifies no deadlocks, no unhandled crashes, and atomic persistence integrity.
        """
        m = self.runner.create_mission(student_id="chaos_user", topic_id="dif")
        actions = ["start", "pause", "resume_paused", "cancel"]
        completed_actions = []

        def chaos_worker(action_name):
            try:
                if action_name == "start":
                    self.runner.start_mission(m.mission_id)
                elif action_name == "pause":
                    self.runner.pause_mission(m.mission_id)
                elif action_name == "resume_paused":
                    self.runner.resume_paused_mission(m.mission_id)
                elif action_name == "cancel":
                    self.runner.cancel_mission(m.mission_id)
                completed_actions.append(action_name)
            except Exception as exc:
                completed_actions.append(f"ERROR_{type(exc).__name__}")

        threads = []
        for _ in range(16):
            act = random.choice(actions)
            t = threading.Thread(target=chaos_worker, args=(act,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        # Verify no thread timed out or hung
        self.assertEqual(len(completed_actions), 16)

        # Verify final state is valid and readable from disk
        final_state = self.runner.get_mission(m.mission_id)
        self.assertIsNotNone(final_state)
        self.assertIn(
            final_state.status,
            (
                MissionStatus.WAITING_FOR_STUDENT,
                MissionStatus.RUNNING,
                MissionStatus.PAUSED,
                MissionStatus.CANCELLED,
            ),
        )

    def test_multi_mission_background_parallelism(self):
        """
        Verify multi-mission background execution executes in parallel without cross-blocking.
        """
        missions = [
            self.runner.create_mission(student_id=f"student_{i}", topic_id="dif")
            for i in range(6)
        ]

        t0 = time.time()
        for m in missions:
            self.runner.start_mission(m.mission_id, background=True)
        init_duration = time.time() - t0

        # Starting 6 background missions should return quickly (non-blocking)
        self.assertLess(init_duration, 1.0)

        # Wait for all missions to reach WAITING_FOR_STUDENT
        deadline = time.time() + 10.0
        all_waiting = False
        while time.time() < deadline:
            statuses = [
                self.runner.get_mission(m.mission_id, student_id=f"student_{i}").status
                for i, m in enumerate(missions)
            ]
            if all(s == MissionStatus.WAITING_FOR_STUDENT for s in statuses):
                all_waiting = True
                break
            time.sleep(0.05)

        self.assertTrue(all_waiting, "All parallel background missions must reach WAITING_FOR_STUDENT")


class TestMissionRunnerInvalidTransitions(unittest.TestCase):
    """Area 2: Invalid & Pathological State Transitions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)
        self.runner = MissionRunner(checkpointer=self.checkpointer, max_workers=2)

    def tearDown(self):
        self.runner.shutdown(wait=False)
        self.temp_dir.cleanup()

    def test_operations_on_cancelled_mission(self):
        """
        Cancelled mission must reject all state mutations and remain CANCELLED.
        """
        m = self.runner.create_mission(student_id="cancel_tester", topic_id="dif")
        cancelled = self.runner.cancel_mission(m.mission_id)
        self.assertEqual(cancelled.status, MissionStatus.CANCELLED)
        self.assertIsNotNone(cancelled.terminated_at)

        # Attempting start
        st = self.runner.start_mission(m.mission_id)
        self.assertEqual(st.status, MissionStatus.CANCELLED)

        # Attempting resume
        st_res = self.runner.resume_mission(m.mission_id, student_response="6*x")
        self.assertEqual(st_res.status, MissionStatus.CANCELLED)

        # Attempting pause
        st_pause = self.runner.pause_mission(m.mission_id)
        self.assertEqual(st_pause.status, MissionStatus.CANCELLED)

        # Attempting resume_paused
        st_unpause = self.runner.resume_paused_mission(m.mission_id)
        self.assertEqual(st_unpause.status, MissionStatus.CANCELLED)

    def test_resume_completed_mission(self):
        """
        Completed mission must remain COMPLETED when resume or start is called.
        """
        m = self.runner.create_mission(student_id="complete_tester", topic_id="dif")
        m.status = MissionStatus.COMPLETED
        m.terminated_at = "2026-11-09T12:00:00Z"
        m.termination_reason = "target_mastery_achieved"
        self.runner.checkpointer.save_checkpoint(m)

        # Attempt start
        st1 = self.runner.start_mission(m.mission_id)
        self.assertEqual(st1.status, MissionStatus.COMPLETED)

        # Attempt resume
        st2 = self.runner.resume_mission(m.mission_id, student_response="6*x")
        self.assertEqual(st2.status, MissionStatus.COMPLETED)

    def test_pause_idempotency(self):
        """
        Calling pause_mission repeatedly on a paused mission must be idempotent.
        """
        m = self.runner.create_mission(student_id="pause_user", topic_id="dif")
        self.runner.start_mission(m.mission_id)

        p1 = self.runner.pause_mission(m.mission_id)
        self.assertEqual(p1.status, MissionStatus.PAUSED)

        p2 = self.runner.pause_mission(m.mission_id)
        self.assertEqual(p2.status, MissionStatus.PAUSED)

        p3 = self.runner.pause_mission(m.mission_id)
        self.assertEqual(p3.status, MissionStatus.PAUSED)

    def test_pause_and_resume_paused_preserves_interaction(self):
        """
        Pausing a WAITING_FOR_STUDENT mission and resuming via resume_paused_mission
        must restore WAITING_FOR_STUDENT with waiting_interaction intact.
        """
        m = self.runner.create_mission(student_id="pause_resume_user", topic_id="dif")
        st = self.runner.start_mission(m.mission_id)
        self.assertEqual(st.status, MissionStatus.WAITING_FOR_STUDENT)
        self.assertIsNotNone(st.waiting_interaction)
        q = st.waiting_interaction.get("question")

        # Pause
        paused = self.runner.pause_mission(m.mission_id)
        self.assertEqual(paused.status, MissionStatus.PAUSED)

        # Resume paused
        resumed = self.runner.resume_paused_mission(m.mission_id)
        self.assertEqual(resumed.status, MissionStatus.WAITING_FOR_STUDENT)
        self.assertIsNotNone(resumed.waiting_interaction)
        self.assertEqual(resumed.waiting_interaction.get("question"), q)

    def test_resuming_unstarted_mission_safely_initializes(self):
        """
        Calling resume_mission on an unstarted (CREATED) mission does not corrupt state.
        LangGraph initializes and advances to WAITING_FOR_STUDENT.
        """
        m = self.runner.create_mission(student_id="unstarted_user", topic_id="dif")
        self.assertEqual(m.status, MissionStatus.CREATED)

        res = self.runner.resume_mission(m.mission_id, student_response="6*x")
        self.assertEqual(res.status, MissionStatus.WAITING_FOR_STUDENT)
        self.assertIsNotNone(res.waiting_interaction)

    def test_nonexistent_mission_handling(self):
        """
        Verify behavior when operating on a non-existent mission_id.
        get_mission returns None. Document that lifecycle operations raise AttributeError.
        """
        self.assertIsNone(self.runner.get_mission("nonexistent_id"))

        # Verify lifecycle methods behavior on nonexistent mission
        for method in [
            self.runner.start_mission,
            self.runner.pause_mission,
            self.runner.cancel_mission,
            self.runner.resume_paused_mission,
        ]:
            with self.assertRaises(AttributeError):
                method("nonexistent_id")

        with self.assertRaises(AttributeError):
            self.runner.resume_mission("nonexistent_id", student_response="6*x")


class TestMissionRunnerResourceExhaustion(unittest.TestCase):
    """Area 3: Resource Budget Exhaustion & Edge Cases."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)
        self.runner = MissionRunner(checkpointer=self.checkpointer, max_workers=2)

    def tearDown(self):
        self.runner.shutdown(wait=False)
        self.temp_dir.cleanup()

    def test_budget_clamping_for_zero_and_negative_limits(self):
        """
        Providing max_steps=0 or negative values must be clamped to safe minimums.
        """
        m = self.runner.create_mission(
            student_id="clamp_user",
            topic_id="dif",
            budget={
                "max_steps": 0,
                "max_tokens": -500,
                "max_duration_seconds": -60,
                "max_tool_calls": 0,
            },
        )
        self.assertEqual(m.budget.max_steps, 1)
        self.assertEqual(m.budget.max_tokens, 1000)
        self.assertEqual(m.budget.max_duration_seconds, 30)
        self.assertEqual(m.budget.max_tool_calls, 1)

    def test_budget_exhaustion_on_step_limit(self):
        """
        Enforce max_steps=1: start mission executes step 1, resume exhausts budget.
        Status must transition to BUDGET_EXHAUSTED with termination_reason set.
        """
        m = self.runner.create_mission(
            student_id="budget_user",
            topic_id="dif",
            budget={"max_steps": 1},
        )
        self.runner.start_mission(m.mission_id)

        resumed = self.runner.resume_mission(m.mission_id, student_response="6*x")
        self.assertEqual(resumed.status, MissionStatus.BUDGET_EXHAUSTED)
        self.assertIsNotNone(resumed.terminated_at)
        self.assertIn("step_budget_exhausted", resumed.termination_reason)

        # Further attempts to resume or start must return BUDGET_EXHAUSTED immediately
        st_after = self.runner.start_mission(m.mission_id)
        self.assertEqual(st_after.status, MissionStatus.BUDGET_EXHAUSTED)

        res_after = self.runner.resume_mission(m.mission_id, student_response="6*x")
        self.assertEqual(res_after.status, MissionStatus.BUDGET_EXHAUSTED)

    def test_budget_duration_limit_expiration(self):
        """
        If a mission has exceeded its max_duration_seconds, start/resume marks BUDGET_EXHAUSTED.
        """
        m = self.runner.create_mission(student_id="duration_user", topic_id="dif")
        # Backdate started_at to simulate expired duration
        m.budget.started_at = "2020-01-01T00:00:00+00:00"
        m.budget.max_duration_seconds = 60
        self.runner.checkpointer.save_checkpoint(m)

        res = self.runner.start_mission(m.mission_id)
        self.assertEqual(res.status, MissionStatus.BUDGET_EXHAUSTED)
        self.assertIsNotNone(res.terminated_at)
        self.assertIn("duration_budget_exhausted", res.termination_reason)


class TestMissionRunnerCrashAndRecovery(unittest.TestCase):
    """Area 4: Crash & Recovery Stress."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_corrupt_active_checkpoint_auto_recovers_from_history(self):
        """
        If active checkpoint JSON is corrupted mid-execution, a new runner instance
        auto-recovers from latest history snapshot and allows execution to continue.
        """
        runner1 = MissionRunner(checkpointer=self.checkpointer, max_workers=2)
        m = runner1.create_mission(student_id="corrupt_recovery_user", topic_id="dif")
        runner1.start_mission(m.mission_id)
        runner1.shutdown(wait=True)

        # Corrupt the primary active mission JSON file
        active_path = self.checkpointer.get_mission_path("corrupt_recovery_user", m.mission_id)
        self.assertTrue(active_path.exists())
        with open(active_path, "w", encoding="utf-8") as f:
            f.write("CORRUPTED_JSON_DATA_NON_PARSEABLE")

        # Create new runner instance simulating service reboot
        checkpointer2 = OyenFileCheckpointer(self.temp_dir.name)
        runner2 = MissionRunner(checkpointer=checkpointer2, max_workers=2)
        try:
            recovered = runner2.get_mission(m.mission_id)
            self.assertIsNotNone(recovered)
            self.assertEqual(recovered.status, MissionStatus.WAITING_FOR_STUDENT)

            # Continue execution on the recovered state
            res = runner2.resume_mission(m.mission_id, student_response="6*x")
            self.assertGreater(res.verified_mastery.get("dif", 0.0), 0.0)
        finally:
            runner2.shutdown(wait=False)

    def test_empty_checkpoint_file_auto_recovers_from_history(self):
        """
        If active checkpoint is truncated to 0 bytes, auto-recovery restores from history.
        """
        runner1 = MissionRunner(checkpointer=self.checkpointer, max_workers=2)
        m = runner1.create_mission(student_id="empty_recovery_user", topic_id="dif")
        runner1.start_mission(m.mission_id)
        runner1.shutdown(wait=True)

        active_path = self.checkpointer.get_mission_path("empty_recovery_user", m.mission_id)
        with open(active_path, "w", encoding="utf-8") as f:
            f.write("")

        checkpointer2 = OyenFileCheckpointer(self.temp_dir.name)
        runner2 = MissionRunner(checkpointer=checkpointer2, max_workers=2)
        try:
            recovered = runner2.get_mission(m.mission_id)
            self.assertIsNotNone(recovered)
            self.assertEqual(recovered.status, MissionStatus.WAITING_FOR_STUDENT)
        finally:
            runner2.shutdown(wait=False)

    def test_hard_shutdown_during_background_execution(self):
        """
        Simulate process kill during background execution: runner is immediately shutdown
        without waiting. Verify checkpoint on disk remains uncorrupted and readable by new runner.
        """
        runner1 = MissionRunner(checkpointer=self.checkpointer, max_workers=4)
        m = runner1.create_mission(student_id="hard_kill_user", topic_id="dif")

        # Launch background execution and kill immediately
        runner1.start_mission(m.mission_id, background=True)
        runner1.shutdown(wait=False)

        time.sleep(0.3)

        # Fresh runner loads state
        checkpointer2 = OyenFileCheckpointer(self.temp_dir.name)
        runner2 = MissionRunner(checkpointer=checkpointer2, max_workers=4)
        try:
            loaded = runner2.get_mission(m.mission_id)
            self.assertIsNotNone(loaded)
            # Must be a valid status, not corrupt
            self.assertIn(loaded.status, (MissionStatus.RUNNING, MissionStatus.WAITING_FOR_STUDENT))

            # Resume execution
            if loaded.status == MissionStatus.WAITING_FOR_STUDENT:
                res = runner2.resume_mission(m.mission_id, student_response="6*x")
            else:
                res = runner2.start_mission(m.mission_id)

            self.assertIsNotNone(res)
            self.assertIn(res.status, (MissionStatus.RUNNING, MissionStatus.WAITING_FOR_STUDENT))
        finally:
            runner2.shutdown(wait=False)

    def test_corruption_without_history_raises_cleanly(self):
        """
        If active checkpoint is corrupted and no valid history exists, CheckpointCorruptedError is raised.
        """
        sid = "total_corrupt_user"
        mid = "m_total_corrupt"
        active_path = self.checkpointer.get_mission_path(sid, mid)
        active_path.parent.mkdir(parents=True, exist_ok=True)
        with open(active_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json_without_history")

        runner = MissionRunner(checkpointer=self.checkpointer, max_workers=2)
        try:
            with self.assertRaises(CheckpointCorruptedError):
                runner.get_mission(mid, student_id=sid)
        finally:
            runner.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
