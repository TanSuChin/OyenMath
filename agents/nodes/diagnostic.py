"""
OyenMath Autonomous AI Learning Platform - Diagnostic Node
Milestone M3: Evaluates prerequisite readiness and detects foundational knowledge gaps.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from ..state import MissionState


PREREQUISITE_MAP = {
    "dif": {"topic": "ind", "name": "Hukum Indeks / Index Laws", "min_mastery": 0.60},
    "integ": {"topic": "dif", "name": "Pembezaan Asas / Basic Differentiation", "min_mastery": 0.60},
    "quad": {"topic": "algebra", "name": "Pemfaktoran Asas / Basic Factoring", "min_mastery": 0.40},
}


def diagnostic_node(state: MissionState, llm: Optional[Any] = None) -> Dict[str, Any]:
    """
    Diagnostic Agent Node.
    Evaluates prerequisite readiness for the target topic.
    Flags foundational gaps that require targeted prerequisite intervention before advanced lessons.
    """
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    mastery = dict(getattr(state, "mastery", {}) or {})
    error_tags = dict(getattr(state, "error_tags", {}) or {})

    prereq_spec = PREREQUISITE_MAP.get(topic_id)
    prerequisite_gap = False
    prerequisite_topic = None
    prerequisite_name = ""
    misconception = None
    confidence = "rendah"
    explanation = "Prasyarat mencukupi untuk topik ini. / Prerequisite readiness verified."

    if prereq_spec:
        req_topic = prereq_spec["topic"]
        req_name = prereq_spec["name"]
        min_m = prereq_spec["min_mastery"]
        cur_prereq_m = mastery.get(req_topic, 1.0)

        # Check for prerequisite weakness: low mastery or persistent exponent/algebra errors
        has_error_pattern = False
        if topic_id in ("dif", "integ") and (error_tags.get("exp", 0) >= 2 or error_tags.get("wrong_power", 0) >= 2):
            has_error_pattern = True

        if cur_prereq_m < min_m or has_error_pattern:
            prerequisite_gap = True
            prerequisite_topic = req_topic
            prerequisite_name = req_name
            misconception = "index_laws_weakness" if req_topic == "ind" else "prerequisite_deficit"
            confidence = "tinggi" if has_error_pattern or cur_prereq_m < 0.40 else "sederhana"
            explanation = (
                f"Kelemahan asas pada {req_name} dikesan (penguasaan: {cur_prereq_m:.0%}). "
                f"Perlu pengukuhan prasyarat sebelum meneruskan {topic_id.upper()}."
            )

    diagnosis = {
        "prerequisite_gap": prerequisite_gap,
        "prerequisite_topic": prerequisite_topic,
        "prerequisite_name": prerequisite_name,
        "misconception": misconception,
        "confidence": confidence,
        "explanation": explanation,
    }

    trace_msg = (
        f"Diagnostic Agent: Evaluated prerequisite readiness for '{topic_id}'. "
        f"Gap detected: {prerequisite_gap} (Prereq topic: '{prerequisite_topic}', Confidence: {confidence})"
    )

    return {
        "diagnosis": diagnosis,
        "current_agent": "diagnostic",
        "trace": [trace_msg],
    }
