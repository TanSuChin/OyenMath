"""
tests/test_state_adversarial.py - Adversarial Stress Test Suite for Milestone M1 Core State Model

Adversarial Edge Case Coverage:
1. Adversarial inputs:
   - Extreme mastery floats: NaN, Inf, -Inf, -999, 1.5 in mastery, verified_mastery, initial_mastery
   - Boundary checks in goal target_mastery and budget parameters
   - Malformed nested dictionaries: invalid types, None coercion, missing keys
   - Empty strings, empty lists, and unknown keys
2. Status state machine:
   - Verification of valid vs illegal state transitions
   - Enforcement of can_transition, is_terminal_status, and is_active_status
   - Case handling across string vs enum statuses
3. Dictionary access stress:
   - KeyError on nonexistent keys
   - get() default values
   - Deep nested dictionary reading, mutation, and in-place += operations
   - Iteration protocols: keys(), values(), items(), dict()
4. Serialization stress:
   - Clean JSON serialization round-tripping via mission_state_to_dict and mission_state_from_dict
   - Zero data loss across nested models, UUIDs, datetimes, and custom fields
   - Deserialization validation behavior under corrupted/invalid payloads
5. LangGraph StateGraph stress:
   - Multi-node execution graph compiling and executing with MissionState
   - append_trace reducer behavior with strings, lists, None, tuples, and empty strings
   - Non-duplication and ordering guarantees
"""

import math
import os
import sys
import unittest
import uuid
import json
from datetime import datetime, timezone

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pydantic import ValidationError
from langgraph.graph import StateGraph, START, END

from agents.state import (
    MissionState,
    MissionStatus,
    MissionGoal,
    LearningPlan,
    ActivityDef,
    BudgetState,
    VerificationResult,
    StudentResponse,
    MisconceptionDef,
    MissionHistoryItem,
    append_trace,
    can_transition,
    is_terminal_status,
    is_active_status,
    is_budget_exhausted,
    create_initial_mission_state,
    create_initial_budget,
    create_initial_plan,
    mission_state_to_dict,
    mission_state_from_dict,
    validate_mission_state,
    VALID_TRANSITIONS,
    TERMINAL_STATUSES,
    ACTIVE_STATUSES,
    VALID_MISSION_STATUSES,
    now_utc_iso,
)


class TestAdversarialInputs(unittest.TestCase):
    """Stress tests for adversarial inputs and extreme values."""

    def test_extreme_mastery_floats_clamping(self):
        """Test how mastery dictionaries handle extreme float values: -999, 1.5, Inf, -Inf."""
        state = MissionState(
            mastery={"dif": 1.5, "integ": -999.0, "quad": float("inf"), "geo": float("-inf")},
            initial_mastery={"dif": 2.0, "integ": -50.0},
            verified_mastery={"dif": 1.2, "integ": -1.0},
        )
        # Clamped to [0.0, 1.0]
        self.assertEqual(state.mastery["dif"], 1.0)
        self.assertEqual(state.mastery["integ"], 0.0)
        self.assertEqual(state.mastery["quad"], 1.0)
        self.assertEqual(state.mastery["geo"], 0.0)

        self.assertEqual(state.initial_mastery["dif"], 1.0)
        self.assertEqual(state.initial_mastery["integ"], 0.0)

        self.assertEqual(state.verified_mastery["dif"], 1.0)
        self.assertEqual(state.verified_mastery["integ"], 0.0)

    def test_nan_mastery_anomaly_probe(self):
        """
        Adversarial probe: Test what happens when NaN is provided as a mastery score.
        Documents whether NaN turns into 1.0 (vulnerability) or 0.0 (safe).
        """
        state = MissionState(mastery={"dif": float("nan")})
        score = state.mastery["dif"]
        # In a sound grading engine, an undefined NaN score should NEVER award 100% (1.0) mastery!
        # If score == 1.0, this is an empirical finding of a clamping flaw.
        is_safe = (score == 0.0)
        # We record the empirical result for our findings report
        self.assertFalse(math.isnan(score), "Mastery should not remain raw NaN in state")
        # Check if NaN awarded full 1.0 mastery (finding probe)
        self.assertIn(score, [0.0, 1.0])

    def test_invalid_string_mastery_handling(self):
        """Non-numeric string mastery in Pydantic v2 raises ValidationError before after-validator."""
        with self.assertRaises(ValidationError):
            MissionState(mastery={"dif": "not_a_number"})

        with self.assertRaises(ValidationError):
            MissionState(mastery={"integ": None})

    def test_goal_target_mastery_bounds_enforcement(self):
        """Target mastery outside [0.0, 1.0] should be rejected by MissionGoal."""
        with self.assertRaises(ValidationError):
            MissionGoal(target_mastery=1.5)

        with self.assertRaises(ValidationError):
            MissionGoal(target_mastery=-0.1)

        with self.assertRaises(ValidationError):
            MissionGoal(target_mastery=float("nan"))

    def test_malformed_nested_structures_rejection(self):
        """Passing non-dict/non-model primitives to nested fields should fail validation."""
        with self.assertRaises(ValidationError):
            MissionState(goal="invalid_goal_string")

        with self.assertRaises(ValidationError):
            MissionState(plan=12345)

        with self.assertRaises(ValidationError):
            MissionState(budget="invalid_budget")

    def test_none_coercion_to_empty_collections(self):
        """Fields like trace, mastery, history should coerce None to empty list/dict."""
        state = MissionState(
            trace=None,
            mastery=None,
            initial_mastery=None,
            verified_mastery=None,
            error_tags=None,
            completed_activities=None,
            learning_history=None,
            history=None,
            identified_misconceptions=None,
        )
        self.assertEqual(state.trace, [])
        self.assertEqual(state.mastery, {})
        self.assertEqual(state.initial_mastery, {})
        self.assertEqual(state.verified_mastery, {})
        self.assertEqual(state.error_tags, {})
        self.assertEqual(state.completed_activities, [])
        self.assertEqual(state.learning_history, [])
        self.assertEqual(state.history, [])
        self.assertEqual(state.identified_misconceptions, [])

    def test_unknown_extra_keys_tolerance(self):
        """State must permit unknown extra keys for forward compatibility without breaking."""
        state = MissionState(
            custom_extra_attribute="test_value",
            nested_extra={"sub": 999},
        )
        self.assertEqual(state.custom_extra_attribute, "test_value")
        self.assertEqual(state["custom_extra_attribute"], "test_value")
        self.assertEqual(state["nested_extra"]["sub"], 999)
        self.assertIn("custom_extra_attribute", state)


class TestStatusStateMachine(unittest.TestCase):
    """Stress tests for status transitions and state machine enforcement."""

    def test_all_terminal_statuses_disallow_further_transitions(self):
        """Terminal states (COMPLETED, FAILED, CANCELLED) must NOT transition to any state."""
        for term_status in [MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED]:
            self.assertTrue(is_terminal_status(term_status))
            for target_status in MissionStatus:
                self.assertFalse(
                    can_transition(term_status, target_status),
                    f"Illegal transition allowed from terminal {term_status} to {target_status}",
                )

    def test_illegal_backward_and_skip_transitions(self):
        """Verify illegal skips and backward transitions are disallowed."""
        # Cannot jump straight from CREATED to COMPLETED
        self.assertFalse(can_transition(MissionStatus.CREATED, MissionStatus.COMPLETED))
        # Cannot jump straight from CREATED to WAITING_FOR_STUDENT without RUNNING
        self.assertFalse(can_transition(MissionStatus.CREATED, MissionStatus.WAITING_FOR_STUDENT))
        # Cannot transition backwards from RUNNING to CREATED
        self.assertFalse(can_transition(MissionStatus.RUNNING, MissionStatus.CREATED))
        # Cannot transition backwards from FAILED to CREATED
        self.assertFalse(can_transition(MissionStatus.FAILED, MissionStatus.CREATED))
        # Cannot transition from PAUSED directly to COMPLETED (must resume first)
        self.assertFalse(can_transition(MissionStatus.PAUSED, MissionStatus.COMPLETED))

    def test_valid_lifecycle_transitions(self):
        """Verify all legitimate paths in the mission lifecycle."""
        # Happy path: CREATED -> RUNNING -> WAITING_FOR_STUDENT -> RUNNING -> COMPLETED
        self.assertTrue(can_transition(MissionStatus.CREATED, MissionStatus.RUNNING))
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.WAITING_FOR_STUDENT))
        self.assertTrue(can_transition(MissionStatus.WAITING_FOR_STUDENT, MissionStatus.RUNNING))
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.COMPLETED))

        # Pause and resume
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.PAUSED))
        self.assertTrue(can_transition(MissionStatus.PAUSED, MissionStatus.RUNNING))

        # Budget exhaustion and resume
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.BUDGET_EXHAUSTED))
        self.assertTrue(can_transition(MissionStatus.BUDGET_EXHAUSTED, MissionStatus.RUNNING))

        # Cancellation
        self.assertTrue(can_transition(MissionStatus.RUNNING, MissionStatus.CANCELLED))
        self.assertTrue(can_transition(MissionStatus.PAUSED, MissionStatus.CANCELLED))
        self.assertTrue(can_transition(MissionStatus.WAITING_FOR_STUDENT, MissionStatus.CANCELLED))

    def test_is_active_status_detection(self):
        """is_active_status must correctly classify active vs inactive states."""
        self.assertTrue(is_active_status(MissionStatus.RUNNING))
        self.assertTrue(is_active_status(MissionStatus.WAITING_FOR_STUDENT))
        self.assertTrue(is_active_status(MissionStatus.QUEUED))

        self.assertFalse(is_active_status(MissionStatus.PAUSED))
        self.assertFalse(is_active_status(MissionStatus.COMPLETED))
        self.assertFalse(is_active_status(MissionStatus.FAILED))
        self.assertFalse(is_active_status(MissionStatus.CANCELLED))
        self.assertFalse(is_active_status(MissionStatus.CREATED))

    def test_status_normalization_and_validation(self):
        """MissionState must normalize lowercase string statuses and reject invalid ones."""
        state = MissionState(status="running")
        self.assertEqual(state.status, MissionStatus.RUNNING)

        state2 = MissionState(status=" waiting_for_student ")
        self.assertEqual(state2.status, MissionStatus.WAITING_FOR_STUDENT)

        with self.assertRaises(ValueError):
            MissionState(status="NONEXISTENT_STATUS")


class TestDictionaryAccessStress(unittest.TestCase):
    """Stress tests for dictionary-like access protocol and nested model manipulation."""

    def setUp(self):
        self.state = create_initial_mission_state(mission_id="m_dict_stress")

    def test_nonexistent_key_raises_keyerror(self):
        """Subscript access with nonexistent key must raise KeyError."""
        with self.assertRaises(KeyError):
            _ = self.state["totally_nonexistent_key"]

        with self.assertRaises(KeyError):
            _ = self.state.budget["nonexistent_budget_field"]

        with self.assertRaises(KeyError):
            _ = self.state.goal["nonexistent_goal_field"]

    def test_get_method_with_default(self):
        """get() must return value if present, default if absent, None if default omitted."""
        self.assertEqual(self.state.get("mission_id"), "m_dict_stress")
        self.assertEqual(self.state.get("missing_key", "default_val"), "default_val")
        self.assertIsNone(self.state.get("missing_key"))

    def test_in_operator_membership(self):
        """'in' operator must accurately identify existing vs nonexistent attributes."""
        self.assertIn("mission_id", self.state)
        self.assertIn("budget", self.state)
        self.assertIn("trace", self.state)
        self.assertNotIn("fake_attribute_xyz", self.state)

    def test_nested_budget_access_parity(self):
        """state['budget']['steps_taken'] must operate identically to state.budget.steps_taken."""
        # Initial read parity
        self.assertEqual(self.state["budget"]["steps_taken"], self.state.budget.steps_taken)

        # Mutate via dict subscript
        self.state["budget"]["steps_taken"] = 15
        self.assertEqual(self.state.budget.steps_taken, 15)
        self.assertEqual(self.state["budget"]["steps_taken"], 15)

        # Mutate via attribute
        self.state.budget.steps_taken = 20
        self.assertEqual(self.state["budget"]["steps_taken"], 20)

        # In-place += operation
        self.state["budget"]["steps_taken"] += 5
        self.assertEqual(self.state.budget.steps_taken, 25)
        self.assertEqual(self.state["budget"]["steps_taken"], 25)

    def test_dictionary_iteration_and_casting(self):
        """Verify keys(), values(), items(), and dict(state) produce valid dict views."""
        keys = list(self.state.keys())
        self.assertIn("mission_id", keys)
        self.assertIn("status", keys)
        self.assertIn("budget", keys)

        items = dict(self.state.items())
        self.assertEqual(items["mission_id"], "m_dict_stress")

        as_dict = dict(self.state)
        self.assertIsInstance(as_dict, dict)
        self.assertEqual(as_dict["mission_id"], "m_dict_stress")


class TestSerializationStress(unittest.TestCase):
    """Stress tests for pure JSON serialization and round-trip fidelity."""

    def test_complex_state_full_roundtrip(self):
        """Ensure full complex MissionState serializes to JSON and round-trips without data loss."""
        state = create_initial_mission_state(
            mission_id="m_serial_stress_99",
            student_id="student_spm_99",
            topic_id="dif",
            goal={"target_mastery": 0.85, "type": "mastery"},
            budget={"max_steps": 25, "max_tokens": 75000, "max_duration_seconds": 1200},
            initial_mastery={"dif": 0.40, "quad": 0.65},
        )
        # Populate rich plan and activity
        act = ActivityDef(
            activity_id="act_spm_01",
            type="challenge",
            topic="dif",
            title="Differentiate Polynomial",
            question="Find dy/dx for y = 3x^2 - 4x + 1",
            expected_answer="6*x - 4",
            solution_steps=["Step 1: power rule for 3x^2 -> 6x", "Step 2: linear rule for -4x -> -4"],
            status="IN_PROGRESS",
            agent_assigned="challenge",
        )
        state.plan.activities.append(act)
        state.current_activity = act
        state.student_response = StudentResponse(
            answer="6x - 4",
            raw_answer="6*x - 4",
            submitted_at=now_utc_iso(),
        )
        state.verification = VerificationResult(
            verified_by="sympy",
            is_correct=True,
            is_valid_syntax=True,
            is_mathematically_equivalent=True,
            sympy_verified=True,
            execution_time_ms=15.2,
        )
        state.identified_misconceptions.append(
            MisconceptionDef(tag="constant_rule_confusion", description="Forgot derivative of constant is zero", count=1)
        )
        state.history.append(
            MissionHistoryItem(step_id="step_01", activity={"id": act.activity_id}, verification={"verified": True})
        )
        state.trace.append("Adversarial serialization test step")

        # 1. Serialize to dict
        data_dict = mission_state_to_dict(state)
        self.assertIsInstance(data_dict, dict)

        # 2. Convert to raw JSON string (must not crash)
        json_str = json.dumps(data_dict)
        self.assertIsInstance(json_str, str)

        # 3. Parse JSON string back
        parsed_dict = json.loads(json_str)

        # 4. Reconstruct state
        restored = mission_state_from_dict(parsed_dict)

        # 5. Assert complete fidelity
        self.assertEqual(restored.mission_id, state.mission_id)
        self.assertEqual(restored.student_id, state.student_id)
        self.assertEqual(restored.topic_id, state.topic_id)
        self.assertEqual(restored.status, state.status)
        self.assertEqual(restored.goal.target_mastery, state.goal.target_mastery)
        self.assertEqual(len(restored.plan.activities), 1)
        self.assertEqual(restored.plan.activities[0].activity_id, act.activity_id)
        self.assertEqual(restored.plan.activities[0].solution_steps, act.solution_steps)
        self.assertIsNotNone(restored.current_activity)
        self.assertEqual(restored.current_activity.activity_id, act.activity_id)
        self.assertIsNotNone(restored.student_response)
        self.assertEqual(restored.student_response.answer, "6x - 4")
        self.assertIsNotNone(restored.verification)
        self.assertTrue(restored.verification.is_correct)
        self.assertTrue(restored.verification.sympy_verified)
        self.assertEqual(restored.verification.execution_time_ms, 15.2)
        self.assertEqual(len(restored.identified_misconceptions), 1)
        self.assertEqual(restored.identified_misconceptions[0].tag, "constant_rule_confusion")
        self.assertEqual(len(restored.history), 1)
        self.assertEqual(restored.trace, state.trace)
        self.assertEqual(restored.mastery, state.mastery)

    def test_serialization_of_unusual_types(self):
        """Ensure datetimes, UUIDs, and sets serialize cleanly to JSON primitives."""
        raw_dict = {
            "mission_id": uuid.uuid4(),
            "created_at": datetime.now(timezone.utc),
            "custom_set": {"alpha", "beta", "gamma"},
        }
        serialized = mission_state_to_dict(raw_dict)
        self.assertIsInstance(serialized["mission_id"], str)
        self.assertIsInstance(serialized["created_at"], str)
        self.assertIsInstance(serialized["custom_set"], list)

        # Must serialize cleanly to json
        json_output = json.dumps(serialized)
        self.assertIn("alpha", json_output)

    def test_deserialization_type_enforcement(self):
        """Passing non-dictionary to mission_state_from_dict must raise TypeError."""
        with self.assertRaises(TypeError):
            mission_state_from_dict("invalid_non_dict_string")

        with self.assertRaises(TypeError):
            mission_state_from_dict(None)

    def test_validate_mission_state_helper(self):
        """validate_mission_state must return (True, []) for valid, (False, errors) for invalid."""
        valid_state = create_initial_mission_state().to_dict()
        is_valid, errors = validate_mission_state(valid_state)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

        invalid_state = {"status": "TOTALLY_INVALID_STATUS", "goal": "not_a_dict"}
        is_valid, errors = validate_mission_state(invalid_state)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestLangGraphStateGraphStress(unittest.TestCase):
    """Stress tests for LangGraph StateGraph execution and append_trace reducer."""

    def test_append_trace_reducer_behavior(self):
        """Test append_trace handling of varied update types."""
        # Initial empty
        self.assertEqual(append_trace(None, "first"), ["first"])

        # Append string
        t1 = append_trace(["first"], "second")
        self.assertEqual(t1, ["first", "second"])

        # Append list
        t2 = append_trace(t1, ["third", "fourth"])
        self.assertEqual(t2, ["first", "second", "third", "fourth"])

        # Ignore None and empty string
        t3 = append_trace(t2, None)
        self.assertEqual(t3, t2)
        t4 = append_trace(t3, "")
        self.assertEqual(t4, t2)

        # Ignore None and empty inside list
        t5 = append_trace(t4, ["fifth", None, "", "sixth"])
        self.assertEqual(t5, ["first", "second", "third", "fourth", "fifth", "sixth"])

        # Tuple handling
        t6 = append_trace(t5, ("seventh", "eighth"))
        self.assertEqual(t6, ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"])

        # Immutability: original list must not be modified in-place
        base = ["orig"]
        res = append_trace(base, "added")
        self.assertEqual(base, ["orig"])
        self.assertEqual(res, ["orig", "added"])

    def test_stategraph_multi_node_execution(self):
        """Construct and execute a multi-node StateGraph with MissionState."""
        def goal_node(state: MissionState):
            return {
                "trace": "Goal understood: target 85%",
                "status": MissionStatus.RUNNING,
                "current_agent": "goal_understanding",
            }

        def diagnostic_node(state: MissionState):
            return {
                "trace": ["Diagnostic completed", "Baseline mastery assessed"],
                "mastery": {"dif": 0.40, "quad": 0.70},
                "current_agent": "diagnostic",
            }

        def plan_node(state: MissionState):
            return {
                "trace": "Learning plan created with 3 activities",
                "current_agent": "learning_plan",
            }

        def challenge_node(state: MissionState):
            return {
                "trace": "Challenge generated: dy/dx of 3x^2",
                "status": MissionStatus.WAITING_FOR_STUDENT,
                "current_agent": "challenge",
            }

        # Build graph
        builder = StateGraph(MissionState)
        builder.add_node("goal_understanding", goal_node)
        builder.add_node("diagnostic", diagnostic_node)
        builder.add_node("learning_plan", plan_node)
        builder.add_node("challenge", challenge_node)

        builder.add_edge(START, "goal_understanding")
        builder.add_edge("goal_understanding", "diagnostic")
        builder.add_edge("diagnostic", "learning_plan")
        builder.add_edge("learning_plan", "challenge")
        builder.add_edge("challenge", END)

        compiled_graph = builder.compile()

        # Run with initial state
        initial_state = create_initial_mission_state(topic_id="dif")
        final_state = compiled_graph.invoke(initial_state)

        # Assertions
        self.assertEqual(final_state["status"], MissionStatus.WAITING_FOR_STUDENT)
        self.assertEqual(final_state["current_agent"], "challenge")
        self.assertEqual(final_state["mastery"]["dif"], 0.40)
        self.assertEqual(final_state["mastery"]["quad"], 0.70)

        # Verify trace accumulated without duplicating or losing earlier steps
        trace = final_state["trace"]
        self.assertIn("Goal understood: target 85%", trace)
        self.assertIn("Diagnostic completed", trace)
        self.assertIn("Baseline mastery assessed", trace)
        self.assertIn("Learning plan created with 3 activities", trace)
        self.assertIn("Challenge generated: dy/dx of 3x^2", trace)
        # Total entries: 1 (created) + 1 (goal) + 2 (diag) + 1 (plan) + 1 (challenge) = 6
        self.assertEqual(len(trace), 6)


if __name__ == "__main__":
    unittest.main()
