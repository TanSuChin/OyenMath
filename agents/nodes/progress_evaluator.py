"""
OyenMath Autonomous AI Learning Platform - Progress Evaluator Node
Milestone M3: Compares verified mastery against target, enforces budget, routes autonomously.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..state import ActivityStatus, MissionState, MissionStatus, now_utc_iso

logger = logging.getLogger("oyen.nodes.progress_evaluator")


def evaluate_mission_progress(state: MissionState) -> Dict[str, Any]:
    """
    Evaluate whether mission is completed, budget exhausted, failed, needs replanning, or continues.
    Returns: dict of state updates and selected route decision.
    """
    budget = getattr(state, "budget", None)
    if budget:
        budget.record_step()

    topic_id = getattr(state, "topic_id", "dif") or "dif"
    verified_mastery = getattr(state, "verified_mastery", {}) or {}
    cur_m = verified_mastery.get(topic_id, 0.0)

    goal = getattr(state, "goal", None)
    target_m = getattr(goal, "target_mastery", 0.80) if goal else 0.80

    hearts = getattr(state, "hearts", 5)
    plan = getattr(state, "plan", None)

    # 1. Check budget exhaustion (highest priority constraint)
    if budget and budget.is_exhausted():
        reason = budget.exhaustion_reason() or "step_budget_exhausted"
        trace_msg = f"Progress Evaluator: Resource budget exhausted! ({reason}). Terminating mission."
        return {
            "status": MissionStatus.BUDGET_EXHAUSTED,
            "terminated_at": now_utc_iso(),
            "termination_reason": reason,
            "_route": "terminate",
            "trace_msg": trace_msg,
        }

    # 2. Check failure (hearts depleted)
    if hearts <= 0:
        trace_msg = "Progress Evaluator: Student hearts depleted (0/5). Terminating mission with FAILED status."
        return {
            "status": MissionStatus.FAILED,
            "terminated_at": now_utc_iso(),
            "termination_reason": "hearts_exhausted",
            "_route": "terminate",
            "trace_msg": trace_msg,
        }

    # 3. Check goal completion (verified mastery >= target mastery)
    if cur_m >= target_m:
        trace_msg = (
            f"Progress Evaluator: Target mastery achieved! "
            f"Verified mastery {cur_m:.0%} >= target {target_m:.0%}. Marking COMPLETED! 🎉"
        )
        return {
            "status": MissionStatus.COMPLETED,
            "terminated_at": now_utc_iso(),
            "termination_reason": "target_mastery_achieved",
            "_route": "complete",
            "trace_msg": trace_msg,
        }

    # 4. Check if all plan activities are finished but target mastery not yet reached -> REPLAN
    has_pending = False
    if plan and plan.activities:
        has_pending = any(act.status == ActivityStatus.PENDING.value for act in plan.activities)

    if not has_pending and cur_m < target_m:
        trace_msg = (
            f"Progress Evaluator: All roadmap steps completed but mastery {cur_m:.0%} < target {target_m:.0%}. "
            f"Triggering adaptive replan."
        )
        return {
            "status": MissionStatus.RUNNING,
            "_route": "replan",
            "trace_msg": trace_msg,
        }

    # 5. Check if repeated errors trigger adaptive replanning
    error_tags = getattr(state, "error_tags", {}) or {}
    total_errors = sum(error_tags.values()) if error_tags else 0
    if total_errors >= 3 and plan and plan.adaptive_replan_count < 2:
        trace_msg = (
            f"Progress Evaluator: {total_errors} accumulated errors detected. "
            f"Triggering adaptive replan for targeted remediation."
        )
        return {
            "status": MissionStatus.RUNNING,
            "_route": "replan",
            "trace_msg": trace_msg,
        }

    # 6. Otherwise continue to next activity in roadmap
    trace_msg = (
        f"Progress Evaluator: Current verified mastery {cur_m:.0%} (Target: {target_m:.0%}). "
        f"Continuing to next planned activity."
    )
    return {
        "status": MissionStatus.RUNNING,
        "_route": "continue",
        "trace_msg": trace_msg,
    }


def progress_evaluator_node(state: MissionState) -> Dict[str, Any]:
    """
    Autonomous Progress Evaluator Agent Node.
    Monitors learning progress, enforces budget state, and decides next step in autonomous lifecycle.
    """
    eval_result = evaluate_mission_progress(state)

    update: Dict[str, Any] = {
        "current_agent": "progress_evaluator",
        "trace": [eval_result["trace_msg"]],
        "_route": eval_result["_route"],
    }

    if "status" in eval_result:
        update["status"] = eval_result["status"]
    if "terminated_at" in eval_result:
        update["terminated_at"] = eval_result["terminated_at"]
    if "termination_reason" in eval_result:
        update["termination_reason"] = eval_result["termination_reason"]

    return update


def route_progress_evaluation(state: MissionState) -> str:
    """
    Conditional edge router for the Autonomous Progress Evaluator.
    Returns: 'replan' | 'continue' | 'wait' | 'complete' | 'terminate'
    """
    route = getattr(state, "_route", None)
    if not route and isinstance(state, dict):
        route = state.get("_route")

    if route in ("replan", "continue", "wait", "complete", "terminate"):
        return route

    # Fallback evaluation if _route not set
    eval_res = evaluate_mission_progress(state)
    return eval_res["_route"]
