"""
OyenMath Autonomous AI Learning Platform - Prerequisite Intervention Node
Milestone M3: Injects targeted remedial steps when diagnostic gaps or repeated errors occur.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..state import MissionState, MissionStatus


PREREQUISITE_REMEDIAL = {
    "ind": {
        "ms": {
            "title": "Intervensi Prasyarat: Pengukuhan Hukum Indeks",
            "content": (
                "Meow! Oyen perasan kesilapan ini berpunca daripada asas hukum indeks! 🐾\n"
                "Untuk bezakan atau kamirkan dengan tepat, kita perlu tahu tukar bentuk:\n"
                "1. 1 / (x^n) = x^(-n)\n"
                "2. √(x) = x^(1/2) dan n√(x^m) = x^(m/n)\n\n"
                "Jom kita kukuhkan asas ini dahulu sebelum kita teruskan! 🐱"
            ),
            "question": "Tuliskan 1 / (x^3) dalam bentuk x^n (contoh: x^(-3)).",
            "expected_answer": "x^(-3)",
        },
        "en": {
            "title": "Prerequisite Intervention: Index Laws Mastery",
            "content": (
                "Meow! Oyen noticed this error stems from foundational index laws! 🐾\n"
                "To differentiate or integrate accurately, we must convert fractions to negative powers:\n"
                "1. 1 / (x^n) = x^(-n)\n"
                "2. √(x) = x^(1/2) and n√(x^m) = x^(m/n)\n\n"
                "Let's master this foundation first before continuing! 🐱"
            ),
            "question": "Express 1 / (x^3) in the form x^n (example: x^(-3)).",
            "expected_answer": "x^(-3)",
        },
    },
    "dif": {
        "ms": {
            "title": "Intervensi Prasyarat: Pembezaan Asas untuk Kamiran",
            "content": (
                "Meow! Kamiran memerlukan kefahaman mantap tentang pembezaan! 🐾\n"
                "Ingat, d/dx [x^n] = n * x^(n - 1). Mari semak satu soalan asas.",
            ),
            "question": "Cari dy/dx bagi y = 4x^3.",
            "expected_answer": "12*x^2",
        },
        "en": {
            "title": "Prerequisite Intervention: Basic Differentiation for Integration",
            "content": (
                "Meow! Integration requires solid differentiation intuition! 🐾\n"
                "Remember, d/dx [x^n] = n * x^(n - 1). Let's review a basic derivative.",
            ),
            "question": "Find dy/dx for y = 4x^3.",
            "expected_answer": "12*x^2",
        },
    },
}


def prerequisite_node(state: MissionState, llm: Optional[Any] = None) -> Dict[str, Any]:
    """
    Prerequisite Intervention Agent Node.
    Injects targeted remedial instruction and practice when diagnostic gaps
    or persistent foundational misconceptions are detected.
    """
    diagnosis = getattr(state, "diagnosis", {}) or {}
    prereq_topic = diagnosis.get("prerequisite_topic") or "ind"
    lang = getattr(state, "language", "ms") or "ms"
    current_activity = getattr(state, "current_activity", None)

    remedial_data = PREREQUISITE_REMEDIAL.get(prereq_topic, PREREQUISITE_REMEDIAL["ind"])
    lesson = remedial_data.get(lang, remedial_data.get("ms", list(remedial_data.values())[0]))

    title = lesson["title"]
    content = lesson["content"]
    question = lesson["question"]
    expected_ans = lesson["expected_answer"]

    if current_activity:
        current_activity.title = title
        current_activity.content = content
        current_activity.question = question
        current_activity.expected_answer = expected_ans
        current_activity.correct_answer = expected_ans
        current_activity.is_prerequisite = True

    trace_msg = (
        f"Prerequisite Agent: Activated remedial intervention on '{prereq_topic}': '{title}'. "
        f"Target question: '{question}'"
    )

    return {
        "status": MissionStatus.WAITING_FOR_STUDENT,
        "current_activity": current_activity,
        "current_agent": "prerequisite",
        "trace": [trace_msg],
    }
