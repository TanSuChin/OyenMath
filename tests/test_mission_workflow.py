"""
tests/test_mission_workflow.py - Comprehensive Unit & Integration Tests for Milestone M3
Covers:
- 12-Node Autonomous Execution Graph compilation & backwards compatibility
- Individual node execution & logic contracts
- Deterministic SymPy verification gate integration
- Native LangGraph interrupt() pausing and Command(resume=...) continuation
- Prerequisite detection and dynamic branching
- Adaptive replanning cycles
- Target mastery goal completion and resource budget exhaustion
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

# Ensure repository root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from langgraph.types import Command

from agents.checkpoint import OyenFileCheckpointer, OyenLangGraphCheckpointer
from agents.graph import build_autonomous_mission_graph, build_graph, run_agent
from agents.nodes import (
    PlanStep,
    adapt_existing_plan,
    challenge_node,
    create_initial_plan,
    diagnostic_node,
    evaluation_node,
    goal_understanding_node,
    learning_plan_node,
    orchestrator_node,
    parse_goal_string,
    prerequisite_node,
    profile_retrieval_node,
    progress_evaluator_node,
    route_orchestrator,
    route_progress_evaluation,
    solver_verification_node,
    state_updater_node,
    student_interaction_node,
    teaching_node,
)
from agents.state import (
    ActivityDef,
    ActivityStatus,
    BudgetState,
    MissionGoal,
    MissionState,
    MissionStatus,
    StudentResponse,
    create_initial_mission_state,
)


class TestMissionWorkflowNodes(unittest.TestCase):
    """Unit tests for individual autonomous agent nodes."""

    def test_goal_understanding_parses_topic_and_mastery(self):
        """Node 1: Goal understanding extracts topic, target percentage, and type."""
        state = create_initial_mission_state(
            goal={"description": "Kuasai topik pembezaan sekurang-kurangnya 85% untuk SPM", "target_mastery": 0.85},
            topic_id="dif",
        )
        res = goal_understanding_node(state)
        self.assertEqual(res["topic_id"], "dif")
        self.assertAlmostEqual(res["goal"].target_mastery, 0.85)
        self.assertEqual(res["goal"].topic_id, "dif")
        self.assertEqual(res["current_agent"], "goal_understanding")
        self.assertTrue(len(res["trace"]) > 0)

        # Test English integration goal parsing
        parsed_topic, target_m, g_type, lang = parse_goal_string("Remediate integration weaknesses to 90%")
        self.assertEqual(parsed_topic, "integ")
        self.assertAlmostEqual(target_m, 0.90)
        self.assertEqual(g_type, "remediation")
        self.assertEqual(lang, "en")

    def test_profile_retrieval_initializes_baselines(self):
        """Node 2: Profile retrieval sets baseline mastery for target and prerequisite."""
        state = create_initial_mission_state(topic_id="dif", student_id="student_101")
        res = profile_retrieval_node(state)
        self.assertIn("dif", res["mastery"])
        self.assertIn("ind", res["mastery"])
        self.assertIn("dif", res["verified_mastery"])
        self.assertEqual(res["current_agent"], "profile_retrieval")

    def test_diagnostic_evaluates_prerequisite_readiness(self):
        """Node 3: Diagnostic detects prerequisite gap when index laws mastery is below threshold."""
        # Gap case: ind mastery 0.30 < 0.60
        state_gap = create_initial_mission_state(topic_id="dif")
        state_gap.mastery = {"dif": 0.10, "ind": 0.30}
        res_gap = diagnostic_node(state_gap)
        self.assertTrue(res_gap["diagnosis"]["prerequisite_gap"])
        self.assertEqual(res_gap["diagnosis"]["prerequisite_topic"], "ind")

        # Ready case: ind mastery 0.85 >= 0.60
        state_ok = create_initial_mission_state(topic_id="dif")
        state_ok.mastery = {"dif": 0.10, "ind": 0.85}
        res_ok = diagnostic_node(state_ok)
        self.assertFalse(res_ok["diagnosis"]["prerequisite_gap"])

    def test_learning_plan_generates_prerequisite_step_when_gap_exists(self):
        """Node 4: Learning plan generator prepends prerequisite step when gap flagged."""
        state = create_initial_mission_state(topic_id="dif")
        state.diagnosis = {"prerequisite_gap": True, "prerequisite_topic": "ind"}
        res = learning_plan_node(state)
        plan = res["plan"]
        self.assertTrue(len(plan.activities) >= 4)
        first_step = plan.activities[0]
        self.assertTrue(first_step.is_prerequisite)
        self.assertEqual(first_step.topic, "ind")

    def test_learning_plan_generates_standard_sequence(self):
        """Node 4: Learning plan generates teaching and challenge sequence without gap."""
        state = create_initial_mission_state(topic_id="dif")
        state.diagnosis = {"prerequisite_gap": False}
        res = learning_plan_node(state)
        plan = res["plan"]
        types = [act.type for act in plan.activities]
        self.assertIn("teaching", types)
        self.assertIn("challenge", types)
        self.assertFalse(plan.activities[0].is_prerequisite)

    def test_learning_plan_adaptive_replan(self):
        """Node 4: Adaptive replan preserves completed steps and appends targeted drill."""
        plan = create_initial_plan("dif")
        plan.activities[0].status = ActivityStatus.COMPLETED.value
        state = create_initial_mission_state(topic_id="dif")
        state.plan = plan
        state.error_tags = {"forgot_c": 2}
        res = learning_plan_node(state)
        updated_plan = res["plan"]
        self.assertEqual(updated_plan.adaptive_replan_count, 1)
        self.assertEqual(updated_plan.activities[0].status, ActivityStatus.COMPLETED.value)
        self.assertIn("Pemalar Kamiran", updated_plan.activities[-1].title)

    def test_orchestrator_selects_and_routes(self):
        """Node 5: Orchestrator selects next pending activity and routes correctly."""
        state = create_initial_mission_state(topic_id="dif")
        state.plan = create_initial_plan("dif")

        # First activity is teaching
        res = orchestrator_node(state)
        self.assertEqual(res["action"], "teach")
        self.assertEqual(res["current_activity"].status, ActivityStatus.IN_PROGRESS.value)
        state.action = res["action"]
        self.assertEqual(route_orchestrator(state), "teaching")

        # When activity is challenge
        state.plan.activities[0].status = ActivityStatus.COMPLETED.value
        state.plan.activities[1].status = ActivityStatus.COMPLETED.value
        res2 = orchestrator_node(state)
        self.assertEqual(res2["action"], "challenge")
        state.action = res2["action"]
        self.assertEqual(route_orchestrator(state), "challenge")

    def test_teaching_node_content_and_question(self):
        """Node 6: Teaching agent provides Oyen mascot persona lesson and comprehension challenge."""
        state = create_initial_mission_state(topic_id="dif")
        state.language = "ms"
        state.current_activity = ActivityDef(type="teaching", topic="dif")
        res = teaching_node(state)
        act = res["current_activity"]
        self.assertTrue("Oyen" in act.content)
        self.assertTrue("dy/dx" in act.question or "bezakan" in act.question.lower())
        self.assertEqual(act.expected_answer, "6*x")

    def test_challenge_node_generates_ground_truth(self):
        """Node 7: Challenge agent generates questions with verified ground truth."""
        for level in (1, 2, 3):
            state = create_initial_mission_state(topic_id="dif")
            state.current_activity = ActivityDef(type="challenge", topic="dif", difficulty=level)
            res = challenge_node(state)
            act = res["current_activity"]
            self.assertTrue(len(act.question) > 0)
            self.assertTrue(len(act.expected_answer) > 0)

    def test_prerequisite_node_remedial_question(self):
        """Node 8: Prerequisite agent prepares remedial index law lesson and question."""
        state = create_initial_mission_state(topic_id="dif")
        state.diagnosis = {"prerequisite_topic": "ind"}
        state.current_activity = ActivityDef(type="prerequisite", topic="ind")
        res = prerequisite_node(state)
        act = res["current_activity"]
        self.assertTrue(act.is_prerequisite)
        self.assertEqual(act.expected_answer, "x^(-3)")

    def test_student_interaction_node_standalone(self):
        """Node 9: In standalone mode outside runnable graph, transitions to WAITING_FOR_STUDENT."""
        state = create_initial_mission_state(topic_id="dif")
        state.current_activity = ActivityDef(question="What is 2+2?", expected_answer="4")
        res = student_interaction_node(state)
        self.assertEqual(res["status"], MissionStatus.WAITING_FOR_STUDENT)
        self.assertIsNotNone(res["waiting_interaction"])

    def test_evaluation_node_diagnoses_errors(self):
        """Node 10: Evaluation agent detects forgot_c, wrong_power, sign_error."""
        state = create_initial_mission_state(topic_id="integ")
        state.current_activity = ActivityDef(expected_answer="x^3 + c")
        state.student_response = StudentResponse(answer="x^3")
        res = evaluation_node(state)
        self.assertEqual(res["diagnosis"]["last_error_tag"], "forgot_c")
        self.assertIn("+ c", res["diagnosis"]["pedagogical_feedback"])

    def test_solver_verification_authoritative_gate(self):
        """Node 11: SymPy engine authoritatively validates mathematically equivalent submissions."""
        state = create_initial_mission_state(topic_id="dif")
        state.current_activity = ActivityDef(expected_answer="6*x - 5")
        state.student_response = StudentResponse(answer="-5 + 6*x")  # Commutative algebraic equivalence
        res = solver_verification_node(state)
        v = res["verification"]
        self.assertTrue(v.is_correct)
        self.assertEqual(v.verified_by, "sympy")
        self.assertTrue(v.sympy_verified)

    def test_state_updater_awards_and_updates_mastery(self):
        """Node 12: State updater awards XP, fish coins, streak, and updates verified mastery."""
        state = create_initial_mission_state(topic_id="dif")
        state.current_activity = ActivityDef(expected_answer="6*x")
        state.student_response = StudentResponse(answer="6*x")

        # Run solver verification first to obtain authoritative SymPy result
        v_res = solver_verification_node(state)
        state.verification = v_res["verification"]

        update = state_updater_node(state)
        self.assertGreater(update["verified_mastery"]["dif"], 0.0)
        self.assertEqual(update["xp_points"], 50)
        self.assertEqual(update["fish_coins"], 10)
        self.assertEqual(update["streak"], 1)
        self.assertEqual(update["current_activity"].status, ActivityStatus.COMPLETED.value)
        self.assertIsNone(update["student_response"])  # Cleared for next step

    def test_state_updater_penalizes_incorrect(self):
        """Node 12: Decrements hearts and breaks streak on incorrect answer."""
        state = create_initial_mission_state(topic_id="dif")
        state.current_activity = ActivityDef(expected_answer="6*x")
        state.student_response = StudentResponse(answer="999")
        state.hearts = 5
        state.streak = 3

        v_res = solver_verification_node(state)
        state.verification = v_res["verification"]

        update = state_updater_node(state)
        self.assertEqual(update["hearts"], 4)
        self.assertEqual(update["streak"], 0)

    def test_progress_evaluator_routing(self):
        """Node 13: Progress evaluator evaluates completion, continuation, and budget exhaustion."""
        # Completion when verified mastery reaches target
        state_done = create_initial_mission_state(topic_id="dif")
        state_done.goal.target_mastery = 0.80
        state_done.verified_mastery = {"dif": 0.85}
        res_done = progress_evaluator_node(state_done)
        self.assertEqual(res_done["status"], MissionStatus.COMPLETED)
        self.assertEqual(res_done["_route"], "complete")
        for k, v in res_done.items():
            state_done[k] = v
        self.assertEqual(route_progress_evaluation(state_done), "complete")

        # Budget exhaustion
        state_budget = create_initial_mission_state(topic_id="dif")
        state_budget.budget = BudgetState(max_steps=5, steps_taken=5)
        res_budget = progress_evaluator_node(state_budget)
        self.assertEqual(res_budget["status"], MissionStatus.BUDGET_EXHAUSTED)
        self.assertEqual(res_budget["_route"], "terminate")


class TestAutonomousWorkflowIntegration(unittest.TestCase):
    """Integration tests running compiled LangGraph workflows with native interrupt and resume."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_chk = OyenFileCheckpointer(self.temp_dir.name)
        self.lg_chk = self.file_chk.get_langgraph_checkpointer()
        self.graph = build_autonomous_mission_graph(checkpointer=self.lg_chk)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_backward_compatibility_with_legacy_pipeline(self):
        """Confirm legacy build_graph() and run_agent() operate unchanged."""
        legacy_g = build_graph()
        self.assertIsNotNone(legacy_g)
        res = run_agent({"topic": "dif", "level": 1, "question": "Beza 3x^2", "student_answer": "6x"})
        self.assertIn("action", res)
        self.assertIn("message", res)

    def test_execution_pauses_at_interrupt_and_resumes(self):
        """Verify graph halts at student_interaction interrupt and resumes with Command(resume=...)."""
        mission = create_initial_mission_state(
            goal={"topic": "dif", "description": "Master differentiation to 80%", "target_mastery": 0.80},
            topic_id="dif",
        )
        config = {"configurable": {"thread_id": mission.mission_id}}

        # First run: preparation nodes execute, halts at student_interaction
        out1 = self.graph.invoke(mission, config)
        interrupts = out1.get("__interrupt__", [])
        self.assertEqual(len(interrupts), 1)
        int_payload = interrupts[0].value
        self.assertEqual(int_payload["mission_id"], mission.mission_id)
        self.assertEqual(out1.get("status"), MissionStatus.WAITING_FOR_STUDENT)

        # Resume with correct answer: "6*x"
        out2 = self.graph.invoke(Command(resume="6*x"), config)
        # Should have evaluated, verified with SymPy, updated verified mastery
        verified_m = out2.get("verified_mastery", {})
        self.assertGreater(verified_m.get("dif", 0.0), 0.0)
        self.assertGreater(out2.get("xp_points", 0), 0)

    def test_prerequisite_branching_on_knowledge_gap(self):
        """Verify student with low prerequisite index mastery is branched into prerequisite review."""
        mission = create_initial_mission_state(
            goal={"topic": "dif", "description": "Master differentiation"},
            topic_id="dif",
            initial_mastery={"dif": 0.05, "ind": 0.20},  # Low prerequisite mastery triggers gap
        )
        config = {"configurable": {"thread_id": mission.mission_id}}

        out = self.graph.invoke(mission, config)
        plan = out.get("plan")
        self.assertIsNotNone(plan)
        # Prerequisite step should have been generated and selected
        first_act = plan.activities[0]
        self.assertTrue(first_act.is_prerequisite)
        self.assertEqual(first_act.topic, "ind")

    def test_budget_exhaustion_terminates_workflow(self):
        """Verify strict budget limiter terminates runaway loops cleanly."""
        mission = create_initial_mission_state(
            goal={"topic": "dif", "description": "Master differentiation", "target_mastery": 0.80},
            topic_id="dif",
            budget={"max_steps": 1},  # Strict 1-step budget limit
        )
        config = {"configurable": {"thread_id": mission.mission_id}}

        # First invoke halts at question
        out1 = self.graph.invoke(mission, config)
        # Resume step records step taken -> exhausts budget -> terminates
        out2 = self.graph.invoke(Command(resume="6*x"), config)
        self.assertEqual(out2.get("status"), MissionStatus.BUDGET_EXHAUSTED)


if __name__ == "__main__":
    unittest.main()
