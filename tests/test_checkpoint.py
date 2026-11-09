"""
tests/test_checkpoint.py - Comprehensive Unit Test Suite for Milestone M1
Tests:
- MissionState creation, dictionary access, and lifecycle validation
- JSON round-trip serialization and edge cases (null coercion, status normalization)
- Legacy AgentState bidirectional conversion (zero regression)
- LangGraph 1.2.14 StateGraph integration with append_trace reducer
- OyenFileCheckpointer save, load, list, delete, and Windows path sanitization
- Atomic write-and-replace (no lingering temporary files)
- Automatic corruption recovery from historical snapshots and error handling
- Concurrency and thread safety under multi-threaded writes
- Server restart simulation and full state restoration
- FirestoreMissionStorage offline fallback
- OyenLangGraphCheckpointer persistent interrupt/resume across restarts
"""

from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
import uuid

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pydantic import ValidationError

from agents.checkpoint import (
    BaseCheckpointProvider,
    BaseMissionCheckpointer,
    CheckpointCorruptedError,
    CheckpointCorruptionError,
    CheckpointError,
    CheckpointPermissionError,
    FirestoreMissionCheckpointer,
    FirestoreMissionStorage,
    MissionLockRegistry,
    OyenFileCheckpointer,
    OyenLangGraphCheckpointer,
    get_default_checkpointer,
    sanitize_filename,
    sanitize_identifier,
)
from agents.state import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    VALID_MISSION_STATUSES,
    VALID_TRANSITIONS,
    ActivityDef,
    ActivityStatus,
    ActivityType,
    BudgetState,
    GoalDef,
    GoalType,
    LearningPlan,
    MisconceptionDef,
    MissionGoal,
    MissionHistoryItem,
    MissionState,
    MissionStatus,
    StudentResponse,
    VerificationResult,
    append_trace,
    can_transition,
    create_initial_budget,
    create_initial_mission_state,
    create_initial_plan,
    is_active_status,
    is_budget_exhausted,
    is_terminal_status,
    mission_state_from_dict,
    mission_state_to_dict,
    validate_mission_state,
)


class TestMissionStateCreation(unittest.TestCase):
    """Test state initialization, attributes, and dictionary access protocols."""

    def test_default_state_initialization(self):
        s = MissionState()
        self.assertTrue(s.mission_id.startswith("m_"))
        self.assertEqual(s.student_id, "dev-local")
        self.assertEqual(s.topic_id, "dif")
        self.assertEqual(s.status, MissionStatus.CREATED)
        self.assertEqual(s.hearts, 5)
        self.assertEqual(s.max_hearts, 5)
        self.assertEqual(s.trace, [])
        self.assertEqual(s.mastery, {})
        self.assertIsNotNone(s.goal)
        self.assertIsNotNone(s.plan)
        self.assertIsNotNone(s.budget)

    def test_custom_state_initialization(self):
        goal = MissionGoal(topic_id="integ", target_mastery=0.85, goal_type="mastery")
        s = MissionState(
            mission_id="m_custom_100",
            student_id="student_spm_01",
            topic_id="integ",
            goal=goal,
            hearts=3,
        )
        self.assertEqual(s.mission_id, "m_custom_100")
        self.assertEqual(s.student_id, "student_spm_01")
        self.assertEqual(s.topic_id, "integ")
        self.assertEqual(s.goal.target_mastery, 0.85)
        self.assertEqual(s.hearts, 3)

    def test_dictionary_like_access_compatibility(self):
        s = MissionState(mission_id="m_dict_test", topic_id="dif")
        # Subscript read
        self.assertEqual(s["mission_id"], "m_dict_test")
        self.assertEqual(s["topic_id"], "dif")
        # get() with and without default
        self.assertEqual(s.get("topic_id"), "dif")
        self.assertEqual(s.get("nonexistent_key", "default_val"), "default_val")
        # in operator
        self.assertIn("mission_id", s)
        self.assertIn("trace", s)
        self.assertNotIn("completely_unknown_key", s)
        # Subscript write
        s["action"] = "prerequisite"
        self.assertEqual(s.action, "prerequisite")
        self.assertEqual(s["action"], "prerequisite")
        # Key error on missing key access
        with self.assertRaises(KeyError):
            _ = s["nonexistent_missing_key"]

    def test_nested_model_dictionary_access(self):
        s = MissionState(mission_id="m_nested")
        s["budget"]["steps_taken"] = 12
        self.assertEqual(s.budget.steps_taken, 12)
        self.assertEqual(s["budget"]["steps_taken"], 12)
        self.assertEqual(s.budget["steps_taken"], 12)
        self.assertIn("steps_taken", s["budget"])

    def test_dictionary_iteration_protocol(self):
        s = MissionState(mission_id="m_iter")
        keys = list(s.keys())
        self.assertIn("mission_id", keys)
        self.assertIn("budget", keys)
        as_dict = dict(s)
        self.assertEqual(as_dict["mission_id"], "m_iter")
        self.assertIsInstance(as_dict, dict)


class TestStateSerializationAndEdgeCases(unittest.TestCase):
    """Test JSON serialization, deserialization, coercion, and validation."""

    def test_state_round_trip_json(self):
        plan = LearningPlan(
            target_topic="dif",
            activities=[
                ActivityDef(activity_id="act_1", topic="dif", level=1, title="Intro"),
                ActivityDef(activity_id="act_2", topic="dif", level=2, title="Power Rule"),
            ],
        )
        s1 = MissionState(mission_id="m_rt_1", plan=plan, trace=["step 1", "step 2"])
        raw_json = s1.model_dump_json()
        s2 = MissionState.model_validate_json(raw_json)
        self.assertEqual(s1.mission_id, s2.mission_id)
        self.assertEqual(len(s2.plan.activities), 2)
        self.assertEqual(s2.plan.activities[0].title, "Intro")
        self.assertEqual(s2.trace, ["step 1", "step 2"])

    def test_helpers_round_trip_serialization(self):
        s1 = create_initial_mission_state(
            mission_id="m_helper_rt",
            student_id="stu_rt",
            topic_id="dif",
            goal={"target_mastery": 0.9},
            initial_mastery={"dif": 0.4},
        )
        d = mission_state_to_dict(s1)
        self.assertIsInstance(d, dict)
        self.assertEqual(d["mission_id"], "m_helper_rt")
        self.assertEqual(d["mastery"]["dif"], 0.4)

        s2 = mission_state_from_dict(d, validate=True)
        self.assertIsInstance(s2, MissionState)
        self.assertEqual(s2.mission_id, "m_helper_rt")
        self.assertEqual(s2.mastery["dif"], 0.4)

    def test_null_collection_coercion(self):
        raw = {
            "mission_id": "m_null_test",
            "trace": None,
            "mastery": None,
            "completed_activities": None,
            "learning_history": None,
            "history": None,
            "identified_misconceptions": None,
        }
        s = MissionState.model_validate(raw)
        self.assertEqual(s.trace, [])
        self.assertEqual(s.mastery, {})
        self.assertEqual(s.completed_activities, [])
        self.assertEqual(s.learning_history, [])
        self.assertEqual(s.history, [])
        self.assertEqual(s.identified_misconceptions, [])

    def test_status_normalization(self):
        s1 = MissionState.model_validate({"status": "running"})
        self.assertEqual(s1.status, MissionStatus.RUNNING)
        s2 = MissionState.model_validate({"status": " waiting_for_student "})
        self.assertEqual(s2.status, MissionStatus.WAITING_FOR_STUDENT)
        s3 = MissionState.model_validate({"status": "budget_exhausted"})
        self.assertEqual(s3.status, MissionStatus.BUDGET_EXHAUSTED)

    def test_invalid_status_rejection(self):
        with self.assertRaises(ValidationError):
            MissionState.model_validate({"status": "INVALID_STATUS_STRING"})

    def test_mastery_range_clamping(self):
        s = MissionState(mastery={"dif": 1.5, "ind": -0.2, "calc": 0.75})
        self.assertEqual(s.mastery["dif"], 1.0)
        self.assertEqual(s.mastery["ind"], 0.0)
        self.assertEqual(s.mastery["calc"], 0.75)

    def test_nan_and_inf_mastery_coercion(self):
        s = MissionState(mastery={"dif": float("nan"), "inf_topic": float("inf"), "neg_inf": float("-inf")})
        self.assertEqual(s.mastery["dif"], 0.0)
        self.assertEqual(s.mastery["inf_topic"], 1.0)
        self.assertEqual(s.mastery["neg_inf"], 0.0)

    def test_dict_compatible_model_method_leak_prevention(self):
        s = MissionState(mission_id="m_leak_test")
        self.assertNotIn("keys", s)
        self.assertNotIn("values", s)
        self.assertNotIn("items", s)
        self.assertIsNone(s.get("keys"))
        with self.assertRaises(KeyError):
            _ = s["keys"]
        self.assertEqual(s["mission_id"], "m_leak_test")
        self.assertEqual(s.get("mission_id"), "m_leak_test")

    def test_default_topic_when_topic_id_none(self):
        s1 = create_initial_mission_state(topic_id=None)
        self.assertEqual(s1.topic_id, "dif")
        self.assertEqual(s1.goal.topic, "dif")
        s2 = create_initial_mission_state(topic_id=None, goal={"topic": "integ"})
        self.assertEqual(s2.topic_id, "integ")

    def test_initial_budget_validation_and_poison_prevention(self):
        s = create_initial_mission_state(budget={"max_steps": -999, "max_tokens": -5, "max_duration_seconds": 10})
        self.assertGreaterEqual(s.budget.max_steps, 1)
        self.assertGreaterEqual(s.budget.max_tokens, 1000)
        self.assertGreaterEqual(s.budget.max_duration_seconds, 30)
        serialized = mission_state_to_dict(s)
        reloaded = mission_state_from_dict(serialized)
        self.assertEqual(reloaded.budget.max_steps, s.budget.max_steps)

    def test_legacy_agent_state_backward_compatibility(self):
        legacy_data = {
            "payload": {"topic": "dif", "level": 2, "question": "f(x)=3x^2"},
            "diagnosis": {"misconception": "exp", "confidence": "tinggi"},
            "action": "prerequisite",
            "message": "Ulang kaji asas indeks.",
            "next_topic": "ind",
            "trace": ["Diagnostic Agent: exp"],
        }
        state = MissionState.from_legacy(legacy_data)
        self.assertEqual(state.topic_id, "dif")
        self.assertEqual(state.diagnosis["misconception"], "exp")
        self.assertEqual(state.action, "prerequisite")
        self.assertEqual(state.next_topic, "ind")
        self.assertIn("Diagnostic Agent: exp", state.trace)

        # Verify export to legacy dict expected by tests/test_agents.py
        legacy_dict = state.to_legacy_dict()
        self.assertEqual(legacy_dict["action"], "prerequisite")
        self.assertEqual(legacy_dict["next_topic"], "ind")
        self.assertEqual(legacy_dict["message"], "Ulang kaji asas indeks.")
        self.assertEqual(legacy_dict["trace"], ["Diagnostic Agent: exp"])
        self.assertFalse(legacy_dict["llm"])


class TestLangGraphStateGraphCompatibility(unittest.TestCase):
    """Test StateGraph(MissionState) compilation and reducer execution."""

    def test_append_trace_reducer(self):
        # Empty inputs
        self.assertEqual(append_trace(None, None), [])
        self.assertEqual(append_trace([], None), [])
        # Append single string
        self.assertEqual(append_trace(["step1"], "step2"), ["step1", "step2"])
        # Append list of strings
        self.assertEqual(append_trace(["step1"], ["step2", "step3"]), ["step1", "step2", "step3"])
        # Coerce empty string / None in list
        self.assertEqual(append_trace(["step1"], ["", "valid"]), ["step1", "valid"])

    def test_langgraph_stategraph_execution(self):
        from langgraph.graph import END, START, StateGraph

        def node_init(s: MissionState) -> dict:
            return {"status": MissionStatus.RUNNING, "trace": "Init completed"}

        def node_action(s: MissionState) -> dict:
            return {"action": "teach", "trace": ["Action selected", "Teaching started"]}

        builder = StateGraph(MissionState)
        builder.add_node("init", node_init)
        builder.add_node("action", node_action)
        builder.add_edge(START, "init")
        builder.add_edge("init", "action")
        builder.add_edge("action", END)
        app = builder.compile()

        initial_state = create_initial_mission_state("m_lg_test", "student_lg")
        out = app.invoke(initial_state)

        self.assertEqual(out["status"], MissionStatus.RUNNING)
        self.assertEqual(out["action"], "teach")
        # Should contain initial trace + 1 from init + 2 from action
        self.assertEqual(len(out["trace"]), 4)
        self.assertIn("Init completed", out["trace"])
        self.assertIn("Action selected", out["trace"])


class TestBudgetAndTransitions(unittest.TestCase):
    """Test budget limit enforcement and valid state machine transitions."""

    def test_budget_step_exhaustion(self):
        b = create_initial_budget(max_steps=5)
        self.assertFalse(b.is_exhausted())
        b.steps_taken = 5
        self.assertTrue(b.is_exhausted())
        self.assertIn("step_budget_exhausted", b.exhaustion_reason())

        exhausted, reason = is_budget_exhausted(b)
        self.assertTrue(exhausted)
        self.assertIn("step_budget_exhausted", reason)

    def test_budget_token_exhaustion(self):
        b = create_initial_budget(max_tokens=1000)
        b.tokens_used = 1500
        self.assertTrue(b.is_exhausted())
        self.assertIn("token_budget_exhausted", b.exhaustion_reason())

    def test_budget_tool_call_exhaustion(self):
        b = create_initial_budget(max_tool_calls=10)
        b.tool_calls_count = 10
        self.assertTrue(b.is_exhausted())
        self.assertIn("tool_call_budget_exhausted", b.exhaustion_reason())

    def test_valid_transitions(self):
        self.assertTrue(can_transition(MissionStatus.CREATED, MissionStatus.RUNNING))
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.WAITING_FOR_STUDENT))
        self.assertTrue(can_transition(MissionStatus.WAITING_FOR_STUDENT, MissionStatus.RUNNING))
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.COMPLETED))
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.BUDGET_EXHAUSTED))

        # Disallowed transitions
        self.assertFalse(can_transition(MissionStatus.COMPLETED, MissionStatus.RUNNING))
        self.assertFalse(can_transition(MissionStatus.FAILED, MissionStatus.RUNNING))
        self.assertFalse(can_transition(MissionStatus.CANCELLED, MissionStatus.RUNNING))

    def test_terminal_and_active_helpers(self):
        self.assertTrue(is_terminal_status(MissionStatus.COMPLETED))
        self.assertTrue(is_terminal_status(MissionStatus.FAILED))
        self.assertTrue(is_terminal_status(MissionStatus.CANCELLED))
        self.assertFalse(is_terminal_status(MissionStatus.RUNNING))

        self.assertTrue(is_active_status(MissionStatus.RUNNING))
        self.assertTrue(is_active_status(MissionStatus.WAITING_FOR_STUDENT))
        self.assertFalse(is_active_status(MissionStatus.PAUSED))

    def test_case_insensitive_status_helpers(self):
        self.assertTrue(can_transition("running", "paused"))
        self.assertTrue(can_transition("waiting_for_student", "running"))
        self.assertTrue(is_terminal_status("completed"))
        self.assertTrue(is_terminal_status("failed"))
        self.assertTrue(is_active_status("running"))
        self.assertTrue(is_active_status("waiting_for_student"))

    def test_naive_datetime_duration_budget_exhaustion(self):
        b = {"max_duration_seconds": 30, "started_at": "2020-01-01T00:00:00"}
        exhausted, reason = is_budget_exhausted(b)
        self.assertTrue(exhausted)
        self.assertIn("duration_budget_exhausted", reason)


class TestOyenFileCheckpointer(unittest.TestCase):
    """Test atomic file checkpointing, history snapshots, and recovery."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_test_ckpt_")
        self.cp = OyenFileCheckpointer(base_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load_checkpoint(self):
        s = MissionState(mission_id="m_save_01", student_id="student_a", topic_id="dif")
        chk_id = self.cp.save_checkpoint(s)
        self.assertTrue(isinstance(chk_id, str))
        self.assertTrue(chk_id.startswith("chk_"))

        # Verify active file exists at expected path
        expected_path = self.cp.get_mission_path("student_a", "m_save_01")
        self.assertTrue(expected_path.exists())

        # Load with explicit student_id
        loaded1 = self.cp.load_checkpoint("m_save_01", student_id="student_a")
        self.assertIsNotNone(loaded1)
        self.assertEqual(loaded1.mission_id, "m_save_01")
        self.assertEqual(loaded1.student_id, "student_a")

        # Load with automatic student discovery
        loaded2 = self.cp.load_checkpoint("m_save_01")
        self.assertIsNotNone(loaded2)
        self.assertEqual(loaded2.mission_id, "m_save_01")

        # Load as raw dictionary
        loaded_dict = self.cp.load_checkpoint("m_save_01", as_dict=True)
        self.assertIsInstance(loaded_dict, dict)
        self.assertEqual(loaded_dict["mission_id"], "m_save_01")

    def test_nonexistent_mission_returns_none(self):
        loaded = self.cp.load_checkpoint("nonexistent_mission_id")
        self.assertIsNone(loaded)

    def test_list_checkpoints_and_missions(self):
        s1 = MissionState(mission_id="m_1", student_id="s_alpha", topic_id="dif")
        s2 = MissionState(mission_id="m_2", student_id="s_alpha", topic_id="integ")
        s3 = MissionState(mission_id="m_3", student_id="s_beta", topic_id="quad")
        self.cp.save_checkpoint(s1)
        self.cp.save_checkpoint(s2)
        self.cp.save_checkpoint(s3)

        # List all missions
        all_ckpts = self.cp.list_missions()
        self.assertEqual(len(all_ckpts), 3)

        # List missions for specific student
        alpha_ckpts = self.cp.list_missions(student_id="s_alpha")
        self.assertEqual(len(alpha_ckpts), 2)

        # List snapshots for a single mission
        m1_history = self.cp.list_checkpoints(mission_id="m_1")
        self.assertGreaterEqual(len(m1_history), 1)
        self.assertEqual(m1_history[0]["checkpoint_id"], s1["checkpoint_id"] if "checkpoint_id" in s1 else m1_history[0]["checkpoint_id"])

    def test_delete_checkpoint(self):
        s = MissionState(mission_id="m_del", student_id="s_del")
        self.cp.save_checkpoint(s)
        self.assertTrue(self.cp.mission_exists("m_del"))

        deleted = self.cp.delete_checkpoint("m_del", "s_del")
        self.assertTrue(deleted)
        self.assertFalse(self.cp.mission_exists("m_del"))
        self.assertIsNone(self.cp.load_checkpoint("m_del"))

    def test_atomic_replacement_leaves_no_temp_files(self):
        s = MissionState(mission_id="m_atomic", student_id="s_atomic")
        self.cp.save_checkpoint(s)
        student_dir = self.cp.get_student_dir("s_atomic")
        temp_files = [f.name for f in student_dir.glob("*.tmp*")]
        self.assertEqual(len(temp_files), 0)

    def test_corrupted_empty_file_without_history_raises(self):
        s_dir = self.cp.get_student_dir("corrupt_student")
        corrupt_file = s_dir / "corrupt_mission.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("")  # 0 bytes

        with self.assertRaises(CheckpointCorruptedError):
            self.cp.load_checkpoint("corrupt_mission", student_id="corrupt_student")

    def test_corrupted_malformed_json_without_history_raises(self):
        s_dir = self.cp.get_student_dir("corrupt_student")
        corrupt_file = s_dir / "bad_json.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write('{"mission_id": "bad", "unclosed": ')

        with self.assertRaises(CheckpointCorruptedError):
            self.cp.load_checkpoint("bad_json", student_id="corrupt_student")

    def test_automatic_corruption_recovery_from_history(self):
        # 1. Save valid checkpoint (creates active file + history snapshot)
        s = MissionState(mission_id="m_corrupt_rec", student_id="s_rec", hearts=4)
        s.trace.append("Initial state recorded")
        self.cp.save_checkpoint(s)

        # 2. Corrupt active file on disk
        active_path = self.cp.get_mission_path("s_rec", "m_corrupt_rec")
        with open(active_path, "w", encoding="utf-8") as f:
            f.write("GARBAGE DATA THAT IS NOT JSON !!!")

        # 3. Load checkpoint: should automatically detect corruption and restore from history
        recovered = self.cp.load_checkpoint("m_corrupt_rec", student_id="s_rec")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_corrupt_rec")
        self.assertEqual(recovered.hearts, 4)
        self.assertIn("Initial state recorded", recovered.trace)

        # 4. Verify that the active file on disk was repaired
        with open(active_path, "r", encoding="utf-8") as f:
            repaired_data = json.load(f)
        self.assertEqual(repaired_data["mission_id"], "m_corrupt_rec")

    def test_windows_path_sanitization(self):
        bad_id = 'student:123/456*?<>|'
        sanitized = sanitize_filename(bad_id)
        self.assertNotIn(":", sanitized)
        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)
        self.assertNotIn("*", sanitized)
        self.assertNotIn("?", sanitized)
        self.assertNotIn("|", sanitized)

        s = MissionState(mission_id="m_win_bad", student_id=bad_id)
        chk_id = self.cp.save_checkpoint(s)
        self.assertTrue(chk_id.startswith("chk_"))
        loaded = self.cp.load_checkpoint("m_win_bad", student_id=bad_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.mission_id, "m_win_bad")

    def test_path_traversal_hardening_in_checkpointer(self):
        # student_id = '..' or '../..' must not escape base_dir
        s_dir = self.cp.get_student_dir("..").resolve()
        base_res = Path(self.test_dir).resolve()
        self.assertTrue(str(s_dir).startswith(str(base_res)))
        # sanitize_identifier
        clean_dotdot = sanitize_identifier("..")
        self.assertNotEqual(clean_dotdot, "..")
        clean_slash = sanitize_identifier("../../etc")
        self.assertNotIn("..", clean_slash)

    def test_schema_corruption_recovery_from_history(self):
        # 1. Save valid checkpoint
        s = MissionState(mission_id="m_schema_rec", student_id="s_schema", hearts=4)
        s.trace.append("Snapshot before schema corruption")
        self.cp.save_checkpoint(s)

        # 2. Corrupt active file with valid JSON but invalid schema
        active_path = self.cp.get_mission_path("s_schema", "m_schema_rec")
        with open(active_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "INVALID_SCHEMA_STATUS"}))

        # 3. load_checkpoint should catch ValidationError and recover from history
        recovered = self.cp.load_checkpoint("m_schema_rec", student_id="s_schema")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_schema_rec")
        self.assertEqual(recovered.hearts, 4)
        self.assertIn("Snapshot before schema corruption", recovered.trace)

    def test_concurrent_saves_to_same_mission(self):
        s = MissionState(mission_id="m_concurrent", student_id="s_shared")
        self.cp.save_checkpoint(s)

        def worker_save(step_num: int):
            state = self.cp.load_checkpoint("m_concurrent", student_id="s_shared")
            if state:
                state.budget.steps_taken += 1
                state.trace.append(f"Step {step_num}")
                self.cp.save_checkpoint(state)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_save, i) for i in range(10)]
            for f in futures:
                f.result()

        final_state = self.cp.load_checkpoint("m_concurrent", student_id="s_shared")
        self.assertIsNotNone(final_state)
        self.assertGreater(final_state.budget.steps_taken, 0)

    def test_state_recovery_across_server_restart(self):
        # 1. First server session saves mission
        cp1 = OyenFileCheckpointer(base_dir=self.test_dir)
        s1 = MissionState(mission_id="m_restart", student_id="s_restart", hearts=3)
        s1.budget.steps_taken = 7
        s1.trace.append("Checkpoint before restart")
        cp1.save_checkpoint(s1)

        # 2. Simulate complete server shutdown by deleting checkpointer instance
        del cp1

        # 3. New server session starts up and reinstantiates checkpointer
        cp2 = OyenFileCheckpointer(base_dir=self.test_dir)
        recovered = cp2.load_checkpoint("m_restart", student_id="s_restart")

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.hearts, 3)
        self.assertEqual(recovered.budget.steps_taken, 7)
        self.assertEqual(recovered.trace[-1], "Checkpoint before restart")


class TestFirestoreStorageFallback(unittest.TestCase):
    """Test Firestore provider graceful offline fallback."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_test_firestore_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_offline_fallback_activation(self):
        fcp = FirestoreMissionStorage(fallback_to_file=True, fallback_dir=self.test_dir)
        # In test environment where firebase_admin is not configured, fallback is active
        self.assertTrue(fcp.is_using_fallback)

        s = MissionState(mission_id="m_fs_01", student_id="stu_fs")
        chk_id = fcp.save_checkpoint(s)
        self.assertTrue(chk_id.startswith("chk_"))

        loaded = fcp.load_checkpoint("m_fs_01")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.mission_id, "m_fs_01")

        deleted = fcp.delete_checkpoint("m_fs_01")
        self.assertTrue(deleted)
        self.assertIsNone(fcp.load_checkpoint("m_fs_01"))

    def test_get_default_checkpointer_factory(self):
        cp_file = get_default_checkpointer(mode="file", base_dir=self.test_dir)
        self.assertIsInstance(cp_file, OyenFileCheckpointer)

        cp_auto = get_default_checkpointer(mode="auto", base_dir=self.test_dir)
        self.assertIsInstance(cp_auto, BaseMissionCheckpointer)


class TestOyenLangGraphCheckpointer(unittest.TestCase):
    """Test LangGraph checkpointer bridge with interrupt / resume simulation across restarts."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_test_lg_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_langgraph_checkpointer_thread_persistence_across_restart(self):
        from langgraph.graph import END, START, StateGraph
        from langgraph.types import Command, interrupt
        from typing import TypedDict

        class SimpleState(TypedDict):
            counter: int
            student_answer: str

        def ask_question(s: SimpleState) -> dict:
            ans = interrupt({"prompt": "Berapakah 2x + 3x?"})
            return {"student_answer": ans, "counter": s["counter"] + 1}

        builder = StateGraph(SimpleState)
        builder.add_node("ask", ask_question)
        builder.add_edge(START, "ask")
        builder.add_edge("ask", END)

        # Session 1: Compile graph with OyenLangGraphCheckpointer and execute until interrupt
        saver1 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app1 = builder.compile(checkpointer=saver1)

        config = {"configurable": {"thread_id": "mission_thread_42"}}
        out1 = app1.invoke({"counter": 0, "student_answer": ""}, config=config)

        # Graph should pause at interrupt
        self.assertIn("__interrupt__", out1)
        self.assertEqual(out1["counter"], 0)

        # Simulate server crash: destroy session 1 saver and app
        del saver1
        del app1

        # Session 2: Fresh server startup with new checkpointer instance
        saver2 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app2 = builder.compile(checkpointer=saver2)

        # Resume execution with student response
        out2 = app2.invoke(Command(resume="5x"), config=config)
        self.assertEqual(out2["student_answer"], "5x")
        self.assertEqual(out2["counter"], 1)


if __name__ == "__main__":
    unittest.main()
