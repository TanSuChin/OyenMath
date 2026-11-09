"""
OyenMath Autonomous AI Learning Platform - Goal Understanding Node
Milestone M3: Analyzes mission objective, extracts topic, target mastery, and constraints.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple, Union

from ..state import MissionGoal, MissionState


TOPIC_KEYWORDS = {
    "dif": [
        "differentiation", "pembezaan", "terbitan", "derivative", "dy/dx",
        "tangent", "tangen", "normal", "titik pegun", "stationary point", "dif"
    ],
    "integ": [
        "integration", "pengamiran", "kamiran", "integral", "antiderivative",
        "luas di bawah graf", "isipadu kisaran", "integ"
    ],
    "quad": [
        "quadratic", "kuadratik", "punca", "roots", "pemfaktoran",
        "penyempurnaan kuasa dua", "completing the square", "quad"
    ],
    "ind": [
        "indices", "indeks", "index laws", "hukum indeks", "surd",
        "logarithm", "logaritma", "ind"
    ],
}


def parse_goal_string(goal_str: str) -> Tuple[Optional[str], float, str, Optional[str]]:
    """
    Parse a natural language goal description into structured components:
    (topic_id, target_mastery, goal_type, detected_language)
    """
    if not goal_str:
        return None, 0.80, "mastery", None

    text = goal_str.lower()

    # 1. Detect target topic
    detected_topic = None
    for topic_code, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                detected_topic = topic_code
                break
        if detected_topic:
            break

    # 2. Detect target mastery
    target_mastery = 0.80
    pct_match = re.search(r"(\d{1,3})\s*%", text)
    if pct_match:
        val = float(pct_match.group(1)) / 100.0
        target_mastery = max(0.10, min(1.0, val))
    else:
        dec_match = re.search(r"\b0\.\d+\b", text)
        if dec_match:
            val = float(dec_match.group(0))
            target_mastery = max(0.10, min(1.0, val))

    # 3. Detect goal type
    goal_type = "mastery"
    if any(k in text for k in ("remediat", "kelemahan", "lemah", "ulang kaji", "prasyarat", "prerequisite")):
        goal_type = "remediation"
    elif any(k in text for k in ("exam", "spm", "drill", "kertas 1", "kertas 2", "percubaan")):
        goal_type = "exam_drill"
    elif any(k in text for k in ("asas", "basic", "foundation")):
        goal_type = "prerequisite_review"

    # 4. Detect language preference
    bm_count = sum(1 for w in ("kuasai", "pembezaan", "pengamiran", "kuadratik", "hukum", "ulang", "kaji", "kelemahan", "tahap") if w in text)
    en_count = sum(1 for w in ("master", "differentiation", "integration", "quadratic", "weakness", "review", "drill") if w in text)
    lang = "ms" if bm_count >= en_count else "en"

    return detected_topic, target_mastery, goal_type, lang


def goal_understanding_node(state: MissionState) -> Dict[str, Any]:
    """
    Goal Understanding Agent Node.
    Analyzes the initial goal specification, extracts target topic, target mastery threshold,
    and goal type, ensuring standard MissionGoal structure is set.
    """
    raw_goal = getattr(state, "goal", None) or (state.get("goal") if isinstance(state, dict) else None)
    current_topic = getattr(state, "topic_id", "dif") or "dif"

    # Extract goal description text
    desc = ""
    if isinstance(raw_goal, MissionGoal):
        desc = raw_goal.description or ""
    elif isinstance(raw_goal, dict):
        desc = raw_goal.get("description", "")
    elif isinstance(raw_goal, str):
        desc = raw_goal

    if not desc:
        payload = getattr(state, "payload", None) or (state.get("payload") if isinstance(state, dict) else None)
        if isinstance(payload, dict):
            desc = payload.get("goal", "") or payload.get("objective", "")

    parsed_topic, target_m, goal_type, detected_lang = parse_goal_string(desc)

    # Resolve final topic: parsed topic takes precedence if detected, else existing topic_id
    final_topic = parsed_topic or current_topic or "dif"

    # Preserve or update target_mastery: prioritize explicit target_mastery from raw_goal over parse_goal_string fallback
    raw_target_mastery = None
    if isinstance(raw_goal, MissionGoal) and raw_goal.target_mastery is not None:
        raw_target_mastery = raw_goal.target_mastery
    elif isinstance(raw_goal, dict) and "target_mastery" in raw_goal and raw_goal["target_mastery"] is not None:
        raw_target_mastery = float(raw_goal["target_mastery"])

    if raw_target_mastery is not None:
        target_m = raw_target_mastery

    # Build updated MissionGoal
    goal_obj = MissionGoal(
        topic_id=final_topic,
        topic=final_topic,
        target_mastery=target_m,
        goal_type=goal_type,
        type=goal_type,
        description=desc or f"Master SPM Additional Mathematics: {final_topic.upper()} to {target_m:.0%}",
    )

    update: Dict[str, Any] = {
        "goal": goal_obj,
        "topic_id": final_topic,
        "current_agent": "goal_understanding",
        "trace": [
            f"Goal Understanding: Analyzed objective '{desc or final_topic}'. "
            f"Target topic: '{final_topic}', target mastery: {target_m:.0%}, type: '{goal_type}'"
        ],
    }

    if detected_lang:
        update["language"] = detected_lang

    return update
