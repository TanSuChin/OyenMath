"""
tests/test_mission_runner.py - Unit & Integration Tests for Autonomous Background Mission Runner
Covers:
- Mission lifecycle operations (create, start, pause, resume, cancel, list, get)
- Non-blocking background execution with ThreadPoolExecutor
- Concurrency isolation across multiple student missions
- Resource budget limits (max_steps exhaustion)
- Persistence across server / runner restarts
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents.checkpoint import OyenFileCheckpointer
from agents.mission_runner import MissionRunner
from agents.state import MissionStatus, StudentResponse


class TestMissionRunnerLifecycle(unittest.TestCase):
    """Lifecycle test suite: create, start, pause, resume, cancel, get, list."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)
        self.runner = MissionRunner(checkpointer=self.checkpointer, max_workers=2)

    def tearDown(self):
        self.runner.shutdown(wait=False)
        self.temp_dir.cleanup()

    def test_create_mission(self):
        """Verifies mission initialization, schema validation, and disk persistence."""
        m = self.runner.create_mission(
            student_id="student_ali",
            goal="Kuasai topik pembezaan sekurang-kurangnya 80%",
            topic_id="dif",
            target_mastery=0.80,
            language="ms",
        )
        self.assertEqual(m.student_id, "student_ali")
        self.assertEqual(m.topic_id, "dif")
        self.assertEqual(m.status, MissionStatus.CREATED)
        self.assertAlmostEqual(m.goal.target_mastery, 0.80)

        # Verify disk checkpoint file exists
        loaded = self.runner.get_mission(m.mission_id, student_id="student_ali")
        self.assertEqual(loaded.mission_id, m.mission_id)

    def test_start_and_resume_mission_sync(self):
        """Executes mission synchronously until interrupt, then resumes with student answer."""
        m = self.runner.create_mission(
            student_id="student_siti",
            goal="Master differentiation to 80%",
            topic_id="dif",
        )
        # Start mission
        started = self.runner.start_mission(m.mission_id)
        self.assertEqual(started.status, MissionStatus.WAITING_FOR_STUDENT)
        self.assertIsNotNone(started.waiting_interaction)
        q = started.waiting_interaction.get("question")
        self.assertTrue(len(q) > 0)

        # Resume with correct answer: 6*x
        resumed = self.runner.resume_mission(m.mission_id, student_response="6*x")
        self.assertIn("dif", resumed.verified_mastery)
        self.assertGreater(resumed.verified_mastery["dif"], 0.0)
        self.assertGreater(resumed.xp_points, 0)

    def test_pause_and_resume_paused_mission(self):
        """Tests pausing active mission and continuing execution."""
        m = self.runner.create_mission(student_id="student_abu", topic_id="dif")
        self.runner.start_mission(m.mission_id)

        # Pause
        paused = self.runner.pause_mission(m.mission_id)
        self.assertEqual(paused.status, MissionStatus.PAUSED)

        # Resuming paused mission
        unpaused = self.runner.resume_paused_mission(m.mission_id)
        self.assertIn(unpaused.status, (MissionStatus.RUNNING, MissionStatus.WAITING_FOR_STUDENT))

    def test_cancel_mission(self):
        """Cancels a mission and verifies it enters terminal CANCELLED status."""
        m = self.runner.create_mission(student_id="student_tan", topic_id="dif")
        cancelled = self.runner.cancel_mission(m.mission_id)
        self.assertEqual(cancelled.status, MissionStatus.CANCELLED)
        self.assertIsNotNone(cancelled.terminated_at)

        # Attempting to start a cancelled mission returns cancelled status
        retry = self.runner.start_mission(m.mission_id)
        self.assertEqual(retry.status, MissionStatus.CANCELLED)

    def test_list_missions_isolation(self):
        """Verifies students only list their own missions."""
        self.runner.create_mission(student_id="student_a", topic_id="dif")
        self.runner.create_mission(student_id="student_a", topic_id="integ")
        self.runner.create_mission(student_id="student_b", topic_id="quad")

        list_a = self.runner.list_missions(student_id="student_a")
        list_b = self.runner.list_missions(student_id="student_b")

        self.assertEqual(len(list_a), 2)
        self.assertEqual(len(list_b), 1)
        self.assertTrue(all(item["student_id"] == "student_a" for item in list_a))
        self.assertTrue(all(item["student_id"] == "student_b" for item in list_b))


class TestMissionRunnerBackground(unittest.TestCase):
    """Background execution and concurrency test suite."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)
        self.runner = MissionRunner(checkpointer=self.checkpointer, max_workers=4)

    def tearDown(self):
        self.runner.shutdown(wait=False)
        self.temp_dir.cleanup()

    def test_start_mission_background(self):
        """Verifies background thread execution returns immediately without blocking."""
        m = self.runner.create_mission(student_id="student_bg", topic_id="dif")

        t0 = time.time()
        res = self.runner.start_mission(m.mission_id, background=True)
        elapsed = time.time() - t0

        # Background start should return in under 0.5 seconds
        self.assertLess(elapsed, 0.5)

        # Poll for completion to WAITING_FOR_STUDENT state
        deadline = time.time() + 5.0
        final_state = None
        while time.time() < deadline:
            st = self.runner.get_mission(m.mission_id)
            if st.status == MissionStatus.WAITING_FOR_STUDENT:
                final_state = st
                break
            time.sleep(0.05)

        self.assertIsNotNone(final_state)
        self.assertEqual(final_state.status, MissionStatus.WAITING_FOR_STUDENT)

    def test_concurrent_missions_isolation(self):
        """Verifies concurrent missions execute independently without cross-talk."""
        m1 = self.runner.create_mission(student_id="user_1", topic_id="dif")
        m2 = self.runner.create_mission(student_id="user_2", topic_id="integ")

        # Start both in background
        self.runner.start_mission(m1.mission_id, background=True)
        self.runner.start_mission(m2.mission_id, background=True)

        # Wait for both to reach waiting state
        deadline = time.time() + 5.0
        s1 = s2 = None
        while time.time() < deadline:
            st1 = self.runner.get_mission(m1.mission_id)
            st2 = self.runner.get_mission(m2.mission_id)
            if st1.status == MissionStatus.WAITING_FOR_STUDENT and st2.status == MissionStatus.WAITING_FOR_STUDENT:
                s1, s2 = st1, st2
                break
            time.sleep(0.05)

        self.assertIsNotNone(s1)
        self.assertIsNotNone(s2)
        self.assertEqual(s1.topic_id, "dif")
        self.assertEqual(s2.topic_id, "integ")


class TestMissionRunnerBudgetAndPersistence(unittest.TestCase):
    """Resource budget enforcement and persistence across runner restarts."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpointer = OyenFileCheckpointer(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_budget_exhaustion_enforcement(self):
        """Verifies runner enforces max_steps limit and marks status BUDGET_EXHAUSTED."""
        runner = MissionRunner(checkpointer=self.checkpointer, max_workers=2)
        try:
            m = runner.create_mission(
                student_id="budget_student",
                topic_id="dif",
                budget={"max_steps": 1},  # Restrict to single step
            )
            # Step 1
            runner.start_mission(m.mission_id)
            # Resuming exhausts budget limit
            resumed = runner.resume_mission(m.mission_id, student_response="6*x")
            self.assertEqual(resumed.status, MissionStatus.BUDGET_EXHAUSTED)
            self.assertIsNotNone(resumed.terminated_at)
        finally:
            runner.shutdown(wait=False)

    def test_persistence_across_runner_restart(self):
        """
        Simulates backend restart:
        1. Initialize Runner A, create & execute mission step 1.
        2. Shut down Runner A completely.
        3. Initialize Runner B pointing to identical disk directory.
        4. Load and resume mission in Runner B, verifying state continuity.
        """
        # Session 1: Runner A
        runner_a = MissionRunner(checkpointer=self.checkpointer, max_workers=2)
        mission_a = runner_a.create_mission(student_id="restart_student", topic_id="dif")
        runner_a.start_mission(mission_a.mission_id)
        mid = mission_a.mission_id

        # Resume once with correct answer
        step1_out = runner_a.resume_mission(mid, student_response="6*x")
        verified_m_1 = step1_out.verified_mastery.get("dif", 0.0)
        self.assertGreater(verified_m_1, 0.0)

        # Shut down Runner A completely
        runner_a.shutdown(wait=True)

        # Session 2: Runner B (simulating fresh server process)
        checkpointer_b = OyenFileCheckpointer(self.temp_dir.name)
        runner_b = MissionRunner(checkpointer=checkpointer_b, max_workers=2)
        try:
            loaded_b = runner_b.get_mission(mid)
            self.assertEqual(loaded_b.mission_id, mid)
            self.assertEqual(loaded_b.verified_mastery.get("dif"), verified_m_1)

            # Continue execution on Runner B
            step2_out = runner_b.resume_mission(mid, student_response="12*(3*x - 2)^3")
            verified_m_2 = step2_out.verified_mastery.get("dif", 0.0)
            self.assertGreaterEqual(verified_m_2, verified_m_1)
        finally:
            runner_b.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
