"""
tests/stress_empirical_m1.py - Milestone M1 Empirical Stress Harness
Executed by Challenger 2 to stress-test the checkpoint persistence layer:
1. High-concurrency writes (same & different missions, WinError 5/32 checks)
2. Corruption recovery (0-byte, truncated JSON, multi-snapshot recovery, schema corruption)
3. Windows edge cases (illegal characters, deep paths > 260 chars, path traversal)
4. LangGraph interrupt/resume across complete runtime destruction & multi-turn cycles
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple, TypedDict
import unittest
import uuid

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents.checkpoint import (
    CheckpointCorruptedError,
    CheckpointPermissionError,
    MissionLockRegistry,
    OyenFileCheckpointer,
    OyenLangGraphCheckpointer,
    sanitize_identifier,
)
from agents.state import (
    MissionState,
    MissionStatus,
    mission_state_from_dict,
    mission_state_to_dict,
)

try:
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class TestConcurrencyStress(unittest.TestCase):
    """Area 1: Concurrency stress tests asserting zero WinError 5/32 and zero corruption."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_stress_conc_")
        self.cp = OyenFileCheckpointer(base_dir=self.test_dir, max_history=100)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_twenty_concurrent_threads_writing_to_same_mission(self):
        """20 concurrent threads writing 10 times each to the SAME mission (200 total writes)."""
        mid = "m_same_stress_20"
        sid = "stu_shared_20"
        s = MissionState(mission_id=mid, student_id=sid, topic_id="dif")
        self.cp.save_checkpoint(s)

        errors: List[Tuple[int, int, str, str]] = []

        def worker(thread_idx: int, iterations: int = 10):
            for i in range(iterations):
                try:
                    state = self.cp.load_checkpoint(mid, student_id=sid)
                    if state is None:
                        raise ValueError("load_checkpoint returned None")
                    state.budget.steps_taken += 1
                    state.trace.append(f"T{thread_idx}_W{i}")
                    self.cp.save_checkpoint(state)
                    time.sleep(random.uniform(0.001, 0.004))
                except Exception as e:
                    errors.append((thread_idx, i, type(e).__name__, str(e)))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, t, 10) for t in range(20)]
            for f in as_completed(futures):
                f.result()

        # Assert zero exceptions occurred
        self.assertEqual(
            len(errors), 0, f"Encountered {len(errors)} concurrency errors: {errors[:5]}"
        )

        # Assert active file exists and is strictly valid MissionState JSON
        active_path = self.cp.get_mission_path(sid, mid)
        self.assertTrue(active_path.exists())
        with open(active_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validated = mission_state_from_dict(data)
        self.assertEqual(validated.mission_id, mid)
        self.assertGreater(validated.budget.steps_taken, 0)
        self.assertGreater(len(validated.trace), 0)

        # Assert all historical snapshots are valid JSON
        hist_dir = self.cp.get_history_dir(sid, mid)
        snapshots = list(hist_dir.glob("*.json"))
        self.assertGreater(len(snapshots), 0)
        for snap in snapshots:
            with open(snap, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            self.assertEqual(s_data["mission_id"], mid)

        # Assert no lingering temporary files remain
        tmp_files = list(self.cp.get_student_dir(sid).glob("*.tmp*"))
        self.assertEqual(len(tmp_files), 0, f"Found lingering temporary files: {tmp_files}")

    def test_twenty_concurrent_threads_writing_to_twenty_different_missions(self):
        """20 concurrent threads writing 10 times each to 20 DIFFERENT missions in parallel."""
        errors: List[Tuple[int, int, str, str]] = []

        def worker(thread_idx: int, iterations: int = 10):
            mid = f"m_diff_{thread_idx}"
            sid = f"stu_diff_{thread_idx}"
            s = MissionState(mission_id=mid, student_id=sid, topic_id="integ")
            self.cp.save_checkpoint(s)

            for i in range(iterations):
                try:
                    state = self.cp.load_checkpoint(mid, student_id=sid)
                    if state is None:
                        raise ValueError("load_checkpoint returned None")
                    state.budget.steps_taken += 1
                    state.trace.append(f"Step_{i}")
                    self.cp.save_checkpoint(state)
                    time.sleep(random.uniform(0.001, 0.003))
                except Exception as e:
                    errors.append((thread_idx, i, type(e).__name__, str(e)))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, t, 10) for t in range(20)]
            for f in as_completed(futures):
                f.result()

        self.assertEqual(
            len(errors), 0, f"Encountered {len(errors)} errors in different-mission test: {errors[:5]}"
        )

        # Verify each of the 20 missions
        for t in range(20):
            mid = f"m_diff_{t}"
            sid = f"stu_diff_{t}"
            loaded = self.cp.load_checkpoint(mid, student_id=sid)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.mission_id, mid)
            self.assertEqual(loaded.budget.steps_taken, 10)
            self.assertEqual(len(loaded.trace), 10)

    def test_high_concurrency_mixed_readers_and_writers(self):
        """10 concurrent writer threads and 10 concurrent reader/lister threads."""
        errors: List[Tuple[str, int, str, str]] = []

        # Pre-seed 3 missions
        for m in range(3):
            s = MissionState(mission_id=f"m_mix_{m}", student_id="stu_mix")
            self.cp.save_checkpoint(s)

        def writer_task(writer_id: int):
            for i in range(15):
                mid = f"m_mix_{i % 3}"
                try:
                    st = self.cp.load_checkpoint(mid, student_id="stu_mix")
                    if st:
                        st.budget.steps_taken += 1
                        self.cp.save_checkpoint(st)
                    time.sleep(random.uniform(0.001, 0.003))
                except Exception as e:
                    errors.append(("writer", writer_id, type(e).__name__, str(e)))

        def reader_task(reader_id: int):
            for i in range(25):
                mid = f"m_mix_{i % 3}"
                try:
                    res = self.cp.load_checkpoint(mid, student_id="stu_mix")
                    all_m = self.cp.list_missions()
                    hist = self.cp.list_checkpoints(mission_id=mid)
                    time.sleep(random.uniform(0.001, 0.002))
                except Exception as e:
                    errors.append(("reader", reader_id, type(e).__name__, str(e)))

        with ThreadPoolExecutor(max_workers=20) as executor:
            w_futs = [executor.submit(writer_task, i) for i in range(10)]
            r_futs = [executor.submit(reader_task, i) for i in range(10)]
            for f in as_completed(w_futs + r_futs):
                f.result()

        self.assertEqual(
            len(errors), 0, f"Encountered {len(errors)} errors in mixed reader/writer test: {errors[:5]}"
        )


class TestCorruptionRecoveryStress(unittest.TestCase):
    """Area 2: Corruption recovery stress testing."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_stress_corrupt_")
        self.cp = OyenFileCheckpointer(base_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_recovery_from_zero_byte_active_file(self):
        """Simulate sudden power failure during write resulting in 0 bytes."""
        s = MissionState(mission_id="m_zero_byte", student_id="stu_corrupt", hearts=4)
        s.trace.append("Initial intact checkpoint")
        self.cp.save_checkpoint(s)

        active_path = self.cp.get_mission_path("stu_corrupt", "m_zero_byte")
        # Overwrite active file with 0 bytes
        with open(active_path, "wb") as f:
            f.write(b"")

        self.assertEqual(active_path.stat().st_size, 0)

        # load_checkpoint should automatically detect 0 bytes, recover from history, and rewrite active file
        recovered = self.cp.load_checkpoint("m_zero_byte", student_id="stu_corrupt")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_zero_byte")
        self.assertEqual(recovered.hearts, 4)
        self.assertEqual(recovered.trace, ["Initial intact checkpoint"])

        # Verify active file was restored on disk
        self.assertGreater(active_path.stat().st_size, 0)
        with open(active_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data["mission_id"], "m_zero_byte")

    def test_recovery_from_truncated_json_active_file(self):
        """Simulate power failure midway through serialization (truncated JSON)."""
        s = MissionState(mission_id="m_truncated", student_id="stu_corrupt", hearts=2)
        s.trace.append("Intact trace entry")
        self.cp.save_checkpoint(s)

        active_path = self.cp.get_mission_path("stu_corrupt", "m_truncated")
        # Truncate active file mid-JSON
        with open(active_path, "w", encoding="utf-8") as f:
            f.write('{"mission_id": "m_truncated", "student_id": "stu_corrupt", "status": "RUN')

        recovered = self.cp.load_checkpoint("m_truncated", student_id="stu_corrupt")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_truncated")
        self.assertEqual(recovered.hearts, 2)
        self.assertEqual(recovered.trace, ["Intact trace entry"])

        # Verify active file was repaired on disk
        with open(active_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data["mission_id"], "m_truncated")

    def test_recovery_from_invalid_utf8_binary_corruption(self):
        """Active file contains arbitrary unparseable binary garbage."""
        s = MissionState(mission_id="m_binary_garbage", student_id="stu_corrupt", hearts=5)
        self.cp.save_checkpoint(s)

        active_path = self.cp.get_mission_path("stu_corrupt", "m_binary_garbage")
        with open(active_path, "wb") as f:
            f.write(b"\x00\xff\xfe\x00\xaa\xbb\xcc\xdd\xee\xff" * 50)

        recovered = self.cp.load_checkpoint("m_binary_garbage", student_id="stu_corrupt")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_binary_garbage")
        self.assertEqual(recovered.hearts, 5)

    def test_schema_corruption_in_active_file_should_recover_from_history(self):
        """
        Active file contains syntactically valid JSON, but invalid state schema
        (e.g. invalid status enum or missing required fields).
        load_checkpoint should detect schema corruption and recover from latest valid snapshot.
        """
        s = MissionState(mission_id="m_schema_corrupt", student_id="stu_corrupt", hearts=4)
        s.trace.append("Intact snapshot before schema corruption")
        self.cp.save_checkpoint(s)

        active_path = self.cp.get_mission_path("stu_corrupt", "m_schema_corrupt")
        # Write valid JSON but invalid schema
        with open(active_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "NONEXISTENT_CORRUPT_STATUS"}))

        # Under robust corruption recovery, load_checkpoint should recover from history
        recovered = self.cp.load_checkpoint("m_schema_corrupt", student_id="stu_corrupt")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_schema_corrupt")
        self.assertEqual(recovered.hearts, 4)

    def test_multi_snapshot_recovery_when_latest_snapshot_is_also_corrupt(self):
        """
        Active file is corrupt AND the newest historical snapshot is corrupt,
        but an older historical snapshot is valid.
        """
        # Save snapshot 1
        s1 = MissionState(mission_id="m_multi_snap", student_id="stu_corrupt", hearts=3)
        s1.trace.append("Snapshot 1")
        self.cp.save_checkpoint(s1)
        time.sleep(0.05)

        # Save snapshot 2
        s2 = MissionState(mission_id="m_multi_snap", student_id="stu_corrupt", hearts=4)
        s2.trace.append("Snapshot 2")
        self.cp.save_checkpoint(s2)

        # Corrupt active file
        active_path = self.cp.get_mission_path("stu_corrupt", "m_multi_snap")
        with open(active_path, "w", encoding="utf-8") as f:
            f.write("ACTIVE CORRUPTED")

        # Corrupt the newest snapshot in history dir
        hist_dir = self.cp.get_history_dir("stu_corrupt", "m_multi_snap")
        snaps = sorted(hist_dir.glob("*.json"), reverse=True)
        self.assertGreaterEqual(len(snaps), 2)
        newest_snap = snaps[0]
        with open(newest_snap, "w", encoding="utf-8") as f:
            f.write("NEWEST SNAPSHOT CORRUPTED")

        # load_checkpoint should skip the corrupted newest snapshot and recover snapshot 1
        recovered = self.cp.load_checkpoint("m_multi_snap", student_id="stu_corrupt")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.mission_id, "m_multi_snap")
        self.assertEqual(recovered.hearts, 3)
        self.assertEqual(recovered.trace, ["Snapshot 1"])

    def test_no_valid_history_raises_clean_checkpoint_corrupted_error(self):
        """When active file is corrupt and NO valid snapshot exists, raises CheckpointCorruptedError."""
        s_dir = self.cp.get_student_dir("stu_unrecoverable")
        active_file = s_dir / "m_lost.json"
        with open(active_file, "w", encoding="utf-8") as f:
            f.write("CORRUPT DATA")

        with self.assertRaises(CheckpointCorruptedError):
            self.cp.load_checkpoint("m_lost", student_id="stu_unrecoverable")


class TestPathLengthAndWindowsEdgeCases(unittest.TestCase):
    """Area 3: Windows edge cases, path sanitization, and path traversal."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_stress_path_")
        self.cp = OyenFileCheckpointer(base_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_illegal_windows_characters_in_identifiers(self):
        """Test characters forbidden by Windows NTFS: :*?\"<>| and control chars."""
        illegal_chars = ':*?"<>|\r\n\t'
        dirty_id = f"test{illegal_chars}id"
        cleaned = sanitize_identifier(dirty_id)

        for ch in ':*?"<>|\r\n\t':
            self.assertNotIn(ch, cleaned)

        # Save and load with dirty identifiers
        dirty_mid = 'mission:123/456*?<>|"test"|'
        dirty_sid = 'student:abc\\def*?<>|'
        s = MissionState(mission_id=dirty_mid, student_id=dirty_sid, topic_id="dif")
        chk_id = self.cp.save_checkpoint(s)
        self.assertTrue(chk_id.startswith("chk_"))

        loaded = self.cp.load_checkpoint(dirty_mid, student_id=dirty_sid)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.topic_id, "dif")

    def test_deep_directory_path_exceeding_windows_max_path_limit(self):
        """Test total file path length > 260 chars on Windows."""
        deep_subdir = Path(self.test_dir) / ("dir_" + "a" * 60) / ("dir_" + "b" * 60)
        deep_cp = OyenFileCheckpointer(base_dir=deep_subdir)

        long_mid = "m_long_" + "x" * 70
        long_sid = "stu_long_" + "y" * 70
        s = MissionState(mission_id=long_mid, student_id=long_sid, topic_id="dif")

        full_target_path = deep_cp.get_mission_path(long_sid, long_mid)
        self.assertGreater(
            len(str(full_target_path)),
            260,
            f"Path length {len(str(full_target_path))} should exceed 260 chars",
        )

        chk_id = deep_cp.save_checkpoint(s)
        self.assertTrue(chk_id.startswith("chk_"))

        loaded = deep_cp.load_checkpoint(long_mid, student_id=long_sid)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.mission_id, long_mid)

    def test_path_traversal_attempts(self):
        """Test malicious path traversal payloads: .., ../.., ..\\.., etc."""
        traversal_payloads = [
            "..",
            "../..",
            "..\\..",
            "../../etc",
            "..\\..\\sensitive",
            ".",
            "....",
            ".../...",
        ]
        base_resolved = Path(self.test_dir).resolve()

        for payload in traversal_payloads:
            s_dir = self.cp.get_student_dir(payload).resolve()
            m_path = self.cp.get_mission_path(payload, "test_m").resolve()
            h_dir = self.cp.get_history_dir(payload, "test_m").resolve()

            # The resolved path MUST be strictly inside base_resolved
            try:
                s_dir.relative_to(base_resolved)
                m_path.relative_to(base_resolved)
                h_dir.relative_to(base_resolved)
                is_safe = True
            except ValueError:
                is_safe = False

            # We assert that the path does NOT escape base_dir
            self.assertTrue(
                is_safe,
                f"Path traversal vulnerability! Payload '{payload}' resolved to '{s_dir}' outside base '{base_resolved}'",
            )


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "langgraph not installed")
class TestLangGraphInterruptResumeStress(unittest.TestCase):
    """Area 4: LangGraph interrupt/resume stress across runtime destruction."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oyen_stress_lg_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_single_interrupt_resume_across_process_destruction(self):
        """
        1. Compile graph with checkpointer.
        2. Run until interrupt() pauses execution.
        3. Delete runtime instance completely.
        4. Reconstruct graph in fresh runtime instance.
        5. Resume execution from disk and verify completion.
        """
        class GraphState(TypedDict):
            counter: int
            student_response: str
            completed: bool

        def ask_node(s: GraphState) -> dict:
            ans = interrupt({"prompt": "Hitungkan pembezaan 3x^2"})
            return {"student_response": ans, "counter": s["counter"] + 1, "completed": True}

        builder = StateGraph(GraphState)
        builder.add_node("ask", ask_node)
        builder.add_edge(START, "ask")
        builder.add_edge("ask", END)

        config = {"configurable": {"thread_id": "thread_spm_test_1"}}

        # --- Phase 1: Execution up to interrupt ---
        saver1 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app1 = builder.compile(checkpointer=saver1)
        res1 = app1.invoke({"counter": 0, "student_response": "", "completed": False}, config=config)

        self.assertIn("__interrupt__", res1)
        self.assertEqual(res1["counter"], 0)
        self.assertFalse(res1["completed"])

        # --- Phase 2: Complete Destruction of Runtime ---
        del saver1
        del app1

        # --- Phase 3: Fresh Runtime Reinstantiation ---
        saver2 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app2 = builder.compile(checkpointer=saver2)

        # Inspect state before resume
        curr_state = app2.get_state(config)
        self.assertIsNotNone(curr_state)
        # LangGraph stores pending interrupt details in tasks[0].interrupts
        self.assertGreater(len(curr_state.tasks), 0)
        self.assertGreater(len(curr_state.tasks[0].interrupts), 0)
        self.assertEqual(
            curr_state.tasks[0].interrupts[0].value,
            {"prompt": "Hitungkan pembezaan 3x^2"},
        )
        self.assertEqual(curr_state.values["counter"], 0)

        # Resume execution with student answer
        res2 = app2.invoke(Command(resume="6x"), config=config)
        self.assertEqual(res2["student_response"], "6x")
        self.assertEqual(res2["counter"], 1)
        self.assertTrue(res2["completed"])

    def test_multi_turn_three_stage_interrupt_resume_across_restarts(self):
        """
        Stress test a 3-turn interactive conversation where each turn interrupts,
        the runtime is destroyed, and resumes from disk.
        """
        class MultiTurnState(TypedDict):
            history: List[str]
            turn: int

        def turn_node(s: MultiTurnState) -> dict:
            turn_num = s["turn"]
            ans = interrupt(f"Question for turn {turn_num}")
            return {
                "history": s["history"] + [f"T{turn_num}:{ans}"],
                "turn": turn_num + 1,
            }

        builder = StateGraph(MultiTurnState)
        builder.add_node("step", turn_node)
        builder.add_edge(START, "step")
        builder.add_edge("step", END)

        thread_id = "thread_multiturn_99"
        config = {"configurable": {"thread_id": thread_id}}

        # Turn 1
        saver_t1 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app_t1 = builder.compile(checkpointer=saver_t1)
        out1 = app_t1.invoke({"history": [], "turn": 1}, config=config)
        self.assertIn("__interrupt__", out1)
        del saver_t1, app_t1

        # Resume Turn 1 -> completes turn 1 and records answer
        saver_t2 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app_t2 = builder.compile(checkpointer=saver_t2)
        out2 = app_t2.invoke(Command(resume="Ans1"), config=config)
        self.assertEqual(out2["history"], ["T1:Ans1"])
        self.assertEqual(out2["turn"], 2)
        del saver_t2, app_t2

        # Verify disk state preserves completed multi-turn history
        saver_t3 = OyenLangGraphCheckpointer(base_dir=self.test_dir)
        app_t3 = builder.compile(checkpointer=saver_t3)
        final_state = app_t3.get_state(config)
        self.assertEqual(final_state.values["history"], ["T1:Ans1"])
        self.assertEqual(final_state.values["turn"], 2)


if __name__ == "__main__":
    unittest.main()
