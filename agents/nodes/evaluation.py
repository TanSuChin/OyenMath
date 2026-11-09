"""
OyenMath Autonomous AI Learning Platform - Evaluation Node
Milestone M3: Pedagogical error analysis, misconception diagnosis, and error tagging.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ..state import MissionState, MisconceptionDef, now_utc_iso


TAG_FORGOT_C = "forgot_c"
TAG_WRONG_POWER = "wrong_power"
TAG_SIGN_ERROR = "sign_error"
TAG_ARITHMETIC = "arithmetic"
TAG_SYNTAX_ERROR = "syntax_error"


def diagnose_pedagogical_error(
    student_answer: str,
    expected_answer: str,
    topic: str,
    lang: str = "ms",
) -> Dict[str, Any]:
    """Diagnose mathematical error patterns and formulate Oyen pedagogical guidance."""
    s_raw = str(student_answer or "").strip()
    e_raw = str(expected_answer or "").strip()

    s_clean = s_raw.lower().replace(" ", "")
    e_clean = e_raw.lower().replace(" ", "")

    error_tag = None
    feedback_ms = ""
    feedback_en = ""

    # 1. Missing constant of integration
    if ("+c" in e_clean or "+C" in expected_answer) and ("+c" not in s_clean and "+C" not in s_raw):
        error_tag = TAG_FORGOT_C
        feedback_ms = (
            "Hampir tepat! Tapi kamu tertinggal cawan kopi '+ c' Oyen! "
            "Dalam kamiran tak tentu, pemalar kamiran '+ c' adalah WAJIB. Jangan lupa ya! ☕🐾"
        )
        feedback_en = (
            "Almost correct! But you forgot Oyen's coffee cup '+ c'! "
            "In indefinite integrals, the constant of integration '+ c' is mandatory. Don't forget it! ☕🐾"
        )

    # 2. Sign error (opposite signs)
    elif ("-" in s_clean and "+" in e_clean) or ("+" in s_clean and "-" in e_clean):
        error_tag = TAG_SIGN_ERROR
        feedback_ms = (
            "Awas tanda positif/negatif! Oyen nampak tanda kamu terbalik sedikit. "
            "Periksa semula langkah pengembangan atau pembezaan anda. 🐾"
        )
        feedback_en = (
            "Watch out for signs! Oyen noticed a inverted sign. "
            "Double-check your negative/positive signs in each step. 🐾"
        )

    # 3. Wrong power / exponent
    elif "^" in e_clean and ("^" not in s_clean or re.findall(r"\^\d+", s_clean) != re.findall(r"\^\d+", e_clean)):
        error_tag = TAG_WRONG_POWER
        feedback_ms = (
            "Meow! Semak semula kuasa/eksponen x kamu. "
            "Untuk pembezaan bawa kuasa turun dan tolak 1; untuk kamiran tambah 1! 🐾"
        )
        feedback_en = (
            "Meow! Check your exponent/power of x. "
            "For derivatives multiply and subtract 1; for integrals add 1! 🐾"
        )

    # 4. Arithmetic / coefficient mismatch
    elif any(char.isdigit() for char in e_clean) and any(char.isdigit() for char in s_clean):
        error_tag = TAG_ARITHMETIC
        feedback_ms = (
            "Ada kesilapan kecil pada pengiraan nombor/pekali. "
            "Langkah konsep kamu dah baik, cuma perlu semak pendaraban/pembahagian semula! 🐾"
        )
        feedback_en = (
            "There's a minor calculation or coefficient error. "
            "Your conceptual steps are good, just re-check your multiplication/division! 🐾"
        )

    else:
        error_tag = TAG_ARITHMETIC
        feedback_ms = "Semak semula langkah penyelesaian kamu bersama Oyen. Jom cuba sekali lagi! 🐾"
        feedback_en = "Re-check your working steps with Oyen. Let's try again! 🐾"

    feedback = feedback_ms if lang == "ms" else feedback_en
    return {
        "error_tag": error_tag,
        "feedback": feedback,
    }


def evaluation_node(state: MissionState, llm: Optional[Any] = None) -> Dict[str, Any]:
    """
    Evaluation Agent Node.
    Analyzes student submissions from a pedagogical perspective, identifies error tags,
    updates historical error counters, and constructs constructive feedback in Oyen's persona.
    """
    student_resp = getattr(state, "student_response", None)
    student_ans = getattr(student_resp, "answer", "") if student_resp else ""
    current_activity = getattr(state, "current_activity", None)
    expected_ans = getattr(current_activity, "expected_answer", "") if current_activity else ""
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    lang = getattr(state, "language", "ms") or "ms"

    error_tags = dict(getattr(state, "error_tags", {}) or {})
    diag_res = diagnose_pedagogical_error(student_ans, expected_ans, topic_id, lang=lang)

    tag = diag_res.get("error_tag")
    feedback = diag_res.get("feedback")

    # Update state diagnosis
    diagnosis = dict(getattr(state, "diagnosis", {}) or {})
    diagnosis.update({
        "last_error_tag": tag,
        "pedagogical_feedback": feedback,
        "misconception": tag,
        "confidence": "tinggi" if tag else "rendah",
    })

    trace_msg = (
        f"Evaluation Agent: Analyzed student answer '{student_ans}'. "
        f"Diagnosed error pattern: '{tag or 'none'}'. Feedback: '{feedback[:60]}...'"
    )

    return {
        "diagnosis": diagnosis,
        "current_agent": "evaluation",
        "trace": [trace_msg],
    }
