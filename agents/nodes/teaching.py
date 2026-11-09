"""
OyenMath Autonomous AI Learning Platform - Teaching Node
Milestone M3: Generates worked examples and analogies in Oyen cat mascot persona (bilingual BM/EN).
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..state import MissionState, MissionStatus


TEACHING_LESSONS = {
    "dif": {
        "ms": {
            "title": "Petua Kuasa Pembezaan (Power Rule)",
            "content": (
                "Meow! Oyen nak kongsi petua paling senang ingat untuk pembezaan! 🐾\n\n"
                "Formula Asas: d/dx [a * x^n] = a * n * x^(n - 1)\n\n"
                "🐱 **Analogi Ikan Oyen:**\n"
                "Bayangkan nombor kuasa 'n' tu seekor ikan atas bumbung. Bila kita bezakan, "
                "ikan tu melompat turun ke depan untuk mendarab dengan nombor depan 'a'. "
                "Lepas tu, kuasanya berkurang satu (n - 1) sebab Oyen dah makan satu ekor ikan! Nyam nyam!\n\n"
                "**Contoh Kerja:**\n"
                "Beza y = 4x^3:\n"
                "1. Bawa 3 ke depan: 4 * 3 = 12\n"
                "2. Kurangkan kuasa: 3 - 1 = 2\n"
                "3. Jawapan: dy/dx = 12x^2"
            ),
            "question": "Cuba soalan ini: Cari dy/dx bagi y = 3x^2.",
            "expected_answer": "6*x",
        },
        "en": {
            "title": "The Power Rule of Differentiation",
            "content": (
                "Meow! Oyen is here to show you the easiest way to master differentiation! 🐾\n\n"
                "Core Formula: d/dx [a * x^n] = a * n * x^(n - 1)\n\n"
                "🐱 **Oyen's Fish Analogy:**\n"
                "Imagine the power 'n' is a fish on a roof. When taking the derivative, "
                "the fish jumps down to the front and multiplies the coefficient 'a'. "
                "Then the exponent decreases by 1 (n - 1) because Oyen ate one fish! Meow!\n\n"
                "**Worked Example:**\n"
                "Differentiate y = 4x^3:\n"
                "1. Bring down 3: 4 * 3 = 12\n"
                "2. Subtract 1 from power: 3 - 1 = 2\n"
                "3. Result: dy/dx = 12x^2"
            ),
            "question": "Your turn: Find dy/dx for y = 3x^2.",
            "expected_answer": "6*x",
        },
    },
    "integ": {
        "ms": {
            "title": "Petua Kuasa Kamiran & Cawan Kopi C",
            "content": (
                "Meow! Kamiran ialah proses terbalik bagi pembezaan! ☕🐾\n\n"
                "Formula Asas: ∫ (a * x^n) dx = [a * x^(n + 1)] / (n + 1) + c  (untuk n ≠ -1)\n\n"
                "🐱 **Petua Oyen:**\n"
                "1. Kuasa bertambah satu: (n + 1)\n"
                "2. Bahagi dengan kuasa baru tersebut!\n"
                "3. WAJIB tambah '+ c'! Bayangkan 'c' ialah cawan kopi kegemaran Oyen. Jangan tertinggal ya!\n\n"
                "**Contoh Kerja:**\n"
                "Kira ∫ 6x^2 dx:\n"
                "1. Tambah kuasa: 2 + 1 = 3\n"
                "2. Bahagi kuasa baru: (6x^3) / 3 = 2x^3\n"
                "3. Tambah cawan kopi Oyen: 2x^3 + c"
            ),
            "question": "Cuba soalan ini: Cari kamiran tak tentu bagi ∫ 3x^2 dx.",
            "expected_answer": "x^3 + c",
        },
        "en": {
            "title": "The Power Rule of Integration & Constant C",
            "content": (
                "Meow! Integration is the reverse process of differentiation! ☕🐾\n\n"
                "Core Formula: ∫ (a * x^n) dx = [a * x^(n + 1)] / (n + 1) + c  (for n ≠ -1)\n\n"
                "🐱 **Oyen's Rule:**\n"
                "1. Add 1 to the power: (n + 1)\n"
                "2. Divide by the new power!\n"
                "3. NEVER forget '+ c'! 'c' is Oyen's Coffee cup. Keep it warm!\n\n"
                "**Worked Example:**\n"
                "Evaluate ∫ 6x^2 dx:\n"
                "1. Increase power: 2 + 1 = 3\n"
                "2. Divide: (6x^3) / 3 = 2x^3\n"
                "3. Add + c: 2x^3 + c"
            ),
            "question": "Your turn: Find the indefinite integral of ∫ 3x^2 dx.",
            "expected_answer": "x^3 + c",
        },
    },
    "quad": {
        "ms": {
            "title": "Punca Persamaan Kuadratik",
            "content": (
                "Meow! Bentuk am persamaan kuadratik ialah ax^2 + bx + c = 0. 🐾\n\n"
                "Punca-punca kuadratik ialah nilai-nilai x yang memuaskan persamaan tersebut. "
                "Kita boleh menyelesaikannya dengan pemfaktoran atau formula kuadratik:\n"
                "x = [-b ± √(b^2 - 4ac)] / (2a)\n\n"
                "**Contoh Kerja:**\n"
                "Selesaikan x^2 - 4x + 3 = 0:\n"
                "Faktorkan: (x - 1)(x - 3) = 0\n"
                "Maka punca: x = 1 atau x = 3"
            ),
            "question": "Cari punca-punca bagi persamaan kuadratik x^2 - 4x + 3 = 0 (tulis dalam bentuk '1, 3').",
            "expected_answer": "1, 3",
        },
        "en": {
            "title": "Roots of Quadratic Equations",
            "content": (
                "Meow! The standard form of a quadratic equation is ax^2 + bx + c = 0. 🐾\n\n"
                "The roots are values of x that satisfy the equation. "
                "Solve by factoring or using the quadratic formula:\n"
                "x = [-b ± √(b^2 - 4ac)] / (2a)\n\n"
                "**Worked Example:**\n"
                "Solve x^2 - 4x + 3 = 0:\n"
                "Factor: (x - 1)(x - 3) = 0\n"
                "Roots: x = 1 or x = 3"
            ),
            "question": "Find the roots of x^2 - 4x + 3 = 0 (write in format '1, 3').",
            "expected_answer": "1, 3",
        },
    },
    "ind": {
        "ms": {
            "title": "Hukum Indeks Asas",
            "content": (
                "Meow! Hukum indeks ialah asas kepada pembezaan dan kamiran! 🐾\n\n"
                "1. x^a * x^b = x^(a + b)\n"
                "2. x^a / x^b = x^(a - b)\n"
                "3. (x^a)^b = x^(a * b)\n"
                "4. 1 / x^n = x^(-n)\n"
                "5. √x = x^(1/2)"
            ),
            "question": "Permudahkan: x^2 * x^3 (tulis dalam sebutan x^n).",
            "expected_answer": "x^5",
        },
        "en": {
            "title": "Fundamental Laws of Indices",
            "content": (
                "Meow! Laws of indices are the foundation for calculus! 🐾\n\n"
                "1. x^a * x^b = x^(a + b)\n"
                "2. x^a / x^b = x^(a - b)\n"
                "3. (x^a)^b = x^(a * b)\n"
                "4. 1 / x^n = x^(-n)\n"
                "5. √x = x^(1/2)"
            ),
            "question": "Simplify: x^2 * x^3 (write in terms of x^n).",
            "expected_answer": "x^5",
        },
    },
}


def teaching_node(state: MissionState, llm: Optional[Any] = None) -> Dict[str, Any]:
    """
    Teaching Agent Node.
    Generates worked examples and mascot analogies in Oyen cat persona (bilingual BM/EN).
    Prepares a verification question for the student to confirm understanding.
    """
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    lang = getattr(state, "language", "ms") or "ms"
    current_activity = getattr(state, "current_activity", None)

    topic_lessons = TEACHING_LESSONS.get(topic_id, TEACHING_LESSONS["dif"])
    lesson_data = topic_lessons.get(lang, topic_lessons.get("ms", list(topic_lessons.values())[0]))

    title = lesson_data["title"]
    content = lesson_data["content"]
    question = lesson_data["question"]
    expected_answer = lesson_data["expected_answer"]

    if current_activity:
        current_activity.content = content
        current_activity.question = question
        current_activity.expected_answer = expected_answer
        current_activity.correct_answer = expected_answer
        if not current_activity.title:
            current_activity.title = title

    trace_msg = (
        f"Teaching Agent (Oyen Mascot): Delivered lesson '{title}' in {lang.upper()}. "
        f"Comprehension challenge prepared: '{question}'"
    )

    return {
        "status": MissionStatus.WAITING_FOR_STUDENT,
        "current_activity": current_activity,
        "current_agent": "teaching",
        "trace": [trace_msg],
    }
