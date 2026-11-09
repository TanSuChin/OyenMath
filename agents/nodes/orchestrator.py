"""
OyenMath Autonomous AI Learning Platform - Orchestrator Node
Milestone M3: Autonomously decides next action and selects active step and topic.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from ..state import ActivityDef, ActivityStatus, MissionState


def select_next_activity(state: MissionState) -> ActivityDef:
    """Find the next pending activity or active in-progress step in the plan."""
    plan = getattr(state, "plan", None)
    if not plan or not plan.activities:
        # Fallback if no plan exists
        topic_id = getattr(state, "topic_id", "dif") or "dif"
        return ActivityDef(
            activity_id=f"act_fallback_{uuid.uuid4().hex[:6]}",
            type="challenge",
            topic=topic_id,
            level=1,
            title="Latihan Matematik SPM",
            status=ActivityStatus.IN_PROGRESS.value,
            agent_assigned="challenge",
        )

    # 1. Check if current_activity is still IN_PROGRESS (e.g. repeated attempt)
    cur_act = getattr(state, "current_activity", None)
    if cur_act and cur_act.status == ActivityStatus.IN_PROGRESS.value:
        return cur_act

    # 2. Find first PENDING activity
    for act in plan.activities:
        if act.status == ActivityStatus.PENDING.value:
            act.status = ActivityStatus.IN_PROGRESS.value
            return act

    # 3. If all activities are completed, create an additional mastery drill
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    extra_act = ActivityDef(
        activity_id=f"step_mastery_{uuid.uuid4().hex[:6]}",
        type="challenge",
        topic=topic_id,
        level=2,
        difficulty=2,
        title="Latihan Penguasaan Lanjutan Oyen",
        description="Latihan pengukuhan tambahan untuk memastikan sasaran penguasaan tercapai.",
        agent_assigned="challenge",
        status=ActivityStatus.IN_PROGRESS.value,
    )
    plan.activities.append(extra_act)
    return extra_act


def orchestrator_node(state: MissionState) -> Dict[str, Any]:
    """
    Orchestrator Agent Node.
    Autonomously selects the next educational activity, determines whether
    teaching, challenge, or prerequisite intervention is needed, and directs graph routing.
    """
    plan = getattr(state, "plan", None)
    active_activity = select_next_activity(state)
    topic_id = active_activity.topic or getattr(state, "topic_id", "dif")

    # Determine action based on activity type and flags
    if active_activity.is_prerequisite or active_activity.type == "prerequisite":
        action = "prerequisite_intervention"
        agent_name = "prerequisite"
    elif active_activity.type == "teaching":
        action = "teach"
        agent_name = "teaching"
    else:
        action = "challenge"
        agent_name = "challenge"

    active_activity.agent_assigned = agent_name

    trace_msg = (
        f"Orchestrator: Selected '{active_activity.title}' (type: {active_activity.type}). "
        f"Autonomous decision -> action '{action}' directed to '{agent_name}'."
    )

    return {
        "plan": plan,
        "current_activity": active_activity,
        "action": action,
        "current_agent": "orchestrator",
        "trace": [trace_msg],
    }


def route_orchestrator(state: MissionState) -> str:
    """Conditional router for the Orchestrator node."""
    action = getattr(state, "action", "challenge") or "challenge"
    if action in ("prerequisite", "prerequisite_intervention"):
        return "prerequisite"
    if action in ("teach", "teaching"):
        return "teaching"
    return "challenge"
