"""
OyenMath Autonomous AI Learning Platform - Profile Retrieval Node
Milestone M3: Retrieves student profile, baseline mastery, language preference, and prior misconceptions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..state import MissionState, MisconceptionDef


# Canonical default baseline masteries when a new student begins
DEFAULT_BASELINES = {
    "ind": 0.65,    # Prerequisite: Index laws
    "dif": 0.10,    # Target topic baseline
    "integ": 0.05,  # Target topic baseline
    "quad": 0.40,   # Quadratics baseline
}


def profile_retrieval_node(state: MissionState) -> Dict[str, Any]:
    """
    Profile Retrieval Agent Node.
    Loads or establishes the student's learning profile, prior verified mastery levels,
    language preference, and historical misconceptions.
    """
    student_id = getattr(state, "student_id", "dev-local") or "dev-local"
    topic_id = getattr(state, "topic_id", "dif") or "dif"

    # 1. Retrieve or initialize mastery dictionaries
    cur_mastery = dict(getattr(state, "mastery", {}) or {})
    cur_verified = dict(getattr(state, "verified_mastery", {}) or {})
    cur_initial = dict(getattr(state, "initial_mastery", {}) or {})

    # Ensure baseline score for active topic
    if topic_id not in cur_mastery:
        base_score = DEFAULT_BASELINES.get(topic_id, 0.10)
        cur_mastery[topic_id] = base_score
    if topic_id not in cur_verified:
        cur_verified[topic_id] = cur_mastery[topic_id]
    if topic_id not in cur_initial:
        cur_initial[topic_id] = cur_mastery[topic_id]

    # Ensure prerequisite topic baselines are present (e.g. index laws 'ind' for 'dif' or 'integ')
    if "ind" not in cur_mastery:
        cur_mastery["ind"] = DEFAULT_BASELINES.get("ind", 0.65)
        cur_verified["ind"] = cur_mastery["ind"]
        cur_initial["ind"] = cur_mastery["ind"]

    # 2. Preserve or normalize language preference
    lang = getattr(state, "language", "ms") or "ms"

    # 3. Retrieve prior misconceptions
    misconceptions = list(getattr(state, "identified_misconceptions", []) or [])

    baseline_val = cur_initial.get(topic_id, 0.0)

    return {
        "mastery": cur_mastery,
        "verified_mastery": cur_verified,
        "initial_mastery": cur_initial,
        "language": lang,
        "identified_misconceptions": misconceptions,
        "current_agent": "profile_retrieval",
        "trace": [
            f"Profile Retrieval: Loaded student '{student_id}'. "
            f"Baseline mastery for '{topic_id}': {baseline_val:.0%}, "
            f"Prerequisite 'ind' mastery: {cur_mastery.get('ind', 0.0):.0%}, "
            f"Language: {lang.upper()}, Prior misconceptions: {len(misconceptions)}"
        ],
    }
