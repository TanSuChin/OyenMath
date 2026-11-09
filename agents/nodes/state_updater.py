"""
OyenMath Autonomous AI Learning Platform - State Updater Node
Milestone M3: Updates verified mastery using calculate_verified_mastery(), awards gamification, updates activity status.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..state import (
    ActivityStatus,
    MissionHistoryItem,
    MissionState,
    MisconceptionDef,
    VerificationResult,
    now_utc_iso,
)
from ..verification import calculate_verified_mastery

logger = logging.getLogger("oyen.nodes.state_updater")


def state_updater_node(state: MissionState) -> Dict[str, Any]:
    """
    Learning State Updater Agent Node.
    Authoritatively updates verified mastery scores (strictly gated by SymPy),
    awards XP and fish coins, tracks streaks, decrements hearts upon errors,
    records mission history, and advances the learning plan.
    """
    v_result: Optional[VerificationResult] = getattr(state, "verification", None)
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    student_resp = getattr(state, "student_response", None)
    student_ans = getattr(student_resp, "answer", "") if student_resp else ""
    current_activity = getattr(state, "current_activity", None)

    mastery = dict(getattr(state, "mastery", {}) or {})
    verified_mastery = dict(getattr(state, "verified_mastery", {}) or {})
    cur_m = verified_mastery.get(topic_id, mastery.get(topic_id, 0.0))

    hearts = getattr(state, "hearts", 5)
    xp_points = getattr(state, "xp_points", 0)
    fish_coins = getattr(state, "fish_coins", 0)
    streak = getattr(state, "streak", 0)
    error_tags = dict(getattr(state, "error_tags", {}) or {})
    misconceptions = list(getattr(state, "identified_misconceptions", []) or [])
    completed_activities = list(getattr(state, "completed_activities", []) or [])
    learning_history = list(getattr(state, "learning_history", []) or [])
    history = list(getattr(state, "history", []) or [])
    plan = getattr(state, "plan", None)

    is_correct = bool(v_result and v_result.is_correct)

    if is_correct:
        # Calculate verified mastery update strictly through SymPy authority
        new_m = calculate_verified_mastery(cur_m, v_result, increment=0.15)
        verified_mastery[topic_id] = new_m
        mastery[topic_id] = new_m

        # Gamification reward
        xp_points += 50
        fish_coins += 10
        streak += 1

        # Mark activity completed
        if current_activity:
            current_activity.status = ActivityStatus.COMPLETED.value
            current_activity.student_answer = student_ans

        trace_msg = (
            f"State Updater: Verified correct answer! Mastery for '{topic_id}' "
            f"increased from {cur_m:.0%} to {new_m:.0%}. "
            f"+50 XP, +10 Fish Coins, Streak: {streak} 🔥"
        )
    else:
        # Penalties and error diagnosis logging
        streak = 0
        hearts = max(0, hearts - 1)

        err_tag = getattr(v_result, "error_tag", None) if v_result else None
        if not err_tag:
            diag = getattr(state, "diagnosis", {}) or {}
            err_tag = diag.get("last_error_tag") or "arithmetic"

        if err_tag:
            error_tags[err_tag] = error_tags.get(err_tag, 0) + 1

            # Update or create MisconceptionDef
            found = False
            for m in misconceptions:
                if m.tag == err_tag:
                    m.count += 1
                    m.last_observed_at = now_utc_iso()
                    found = True
                    break
            if not found:
                misconceptions.append(
                    MisconceptionDef(
                        tag=err_tag,
                        description=f"Ralat {err_tag} dikesan pada topik {topic_id}",
                        confidence="sederhana",
                        count=1,
                    )
                )

        trace_msg = (
            f"State Updater: Incorrect answer. Hearts remaining: {hearts}/5. "
            f"Error tag '{err_tag}' recorded. Streak reset."
        )

    # Sync status in plan activities
    if plan and plan.activities and current_activity:
        for act in plan.activities:
            if act.activity_id == current_activity.activity_id:
                act.status = current_activity.status
                act.student_answer = current_activity.student_answer
                break
        plan.current_step_index = min(len(plan.activities), plan.current_step_index + 1)

    def _to_dump(obj: Any) -> Optional[Dict[str, Any]]:
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, dict):
            return dict(obj)
        return None

    # Record archival history item
    hist_item = MissionHistoryItem(
        activity=_to_dump(current_activity),
        student_response=_to_dump(student_resp),
        verification=_to_dump(v_result),
        evaluation=getattr(state, "diagnosis", None),
        timestamp=now_utc_iso(),
    )
    history.append(hist_item)
    dumped_hist = _to_dump(hist_item)
    if dumped_hist:
        learning_history.append(dumped_hist)

    if current_activity and current_activity.status == ActivityStatus.COMPLETED.value:
        dumped_act = _to_dump(current_activity)
        if dumped_act:
            completed_activities.append(dumped_act)

    return {
        "plan": plan,
        "mastery": mastery,
        "verified_mastery": verified_mastery,
        "hearts": hearts,
        "xp_points": xp_points,
        "fish_coins": fish_coins,
        "streak": streak,
        "error_tags": error_tags,
        "identified_misconceptions": misconceptions,
        "completed_activities": completed_activities,
        "learning_history": learning_history,
        "history": history,
        "current_activity": current_activity,
        "student_response": None,  # Reset student_response for subsequent activity
        "current_agent": "state_updater",
        "trace": [trace_msg],
    }
