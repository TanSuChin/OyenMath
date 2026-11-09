"""
OyenMath Autonomous AI Learning Platform - Challenge Generator Node
Milestone M3: Generates SPM-style challenge questions with verified mathematical ground truth.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..state import MissionState, MissionStatus


CHALLENGE_BANK = {
    "dif": {
        1: [
            {
                "question_ms": "Diberi y = 2x^3 - 5x^2 + 4x - 7, cari terbitan pertama dy/dx.",
                "question_en": "Given y = 2x^3 - 5x^2 + 4x - 7, find the first derivative dy/dx.",
                "expected": "6*x^2 - 10*x + 4",
                "solution_steps": [
                    "Beza 2x^3: 3 * 2 * x^(3-1) = 6x^2",
                    "Beza -5x^2: 2 * (-5) * x^(2-1) = -10x",
                    "Beza 4x: 4",
                    "Beza pemalar -7: 0",
                    "Hasil akhir: dy/dx = 6x^2 - 10x + 4",
                ],
            },
            {
                "question_ms": "Cari dy/dx bagi y = 3x^4 - 2x + 1.",
                "question_en": "Find dy/dx for y = 3x^4 - 2x + 1.",
                "expected": "12*x^3 - 2",
                "solution_steps": [
                    "Beza 3x^4: 12x^3",
                    "Beza -2x: -2",
                    "Hasil: dy/dx = 12x^3 - 2",
                ],
            },
        ],
        2: [
            {
                "question_ms": "Diberi y = (3x - 2)^4, cari dy/dx menggunakan petua rantai.",
                "question_en": "Given y = (3x - 2)^4, find dy/dx using the chain rule.",
                "expected": "12*(3*x - 2)^3",
                "solution_steps": [
                    "Biarkan u = 3x - 2, maka y = u^4",
                    "du/dx = 3 dan dy/du = 4u^3",
                    "dy/dx = dy/du * du/dx = 4(3x - 2)^3 * 3 = 12(3x - 2)^3",
                ],
            },
            {
                "question_ms": "Cari kecerunan lengkung y = x^2 - 4x + 1 pada titik x = 3.",
                "question_en": "Find the gradient of the curve y = x^2 - 4x + 1 at the point x = 3.",
                "expected": "2",
                "solution_steps": [
                    "dy/dx = 2x - 4",
                    "Gantikan x = 3: dy/dx = 2(3) - 4 = 2",
                ],
            },
        ],
        3: [
            {
                "question_ms": "Cari titik pegun bagi lengkung y = x^3 - 3x^2 + 2 pada x > 0.",
                "question_en": "Find the stationary point x-coordinate for the curve y = x^3 - 3x^2 + 2 where x > 0.",
                "expected": "2",
                "solution_steps": [
                    "dy/dx = 3x^2 - 6x = 0",
                    "3x(x - 2) = 0 => x = 0 atau x = 2",
                    "Syarat x > 0 memberikan x = 2",
                ],
            },
        ],
    },
    "integ": {
        1: [
            {
                "question_ms": "Cari kamiran tak tentu bagi ∫ (6x^2 - 4x + 3) dx.",
                "question_en": "Find the indefinite integral of ∫ (6x^2 - 4x + 3) dx.",
                "expected": "2*x^3 - 2*x^2 + 3*x + c",
                "solution_steps": [
                    "Kamir 6x^2: 6 * (x^3)/3 = 2x^3",
                    "Kamir -4x: -4 * (x^2)/2 = -2x^2",
                    "Kamir 3: 3x",
                    "Tambah pemalar kamiran: + c",
                    "Hasil: 2x^3 - 2x^2 + 3x + c",
                ],
            },
            {
                "question_ms": "Nilaikan kamiran tak tentu ∫ (4x^3 + 2x) dx.",
                "question_en": "Evaluate the indefinite integral ∫ (4x^3 + 2x) dx.",
                "expected": "x^4 + x^2 + c",
                "solution_steps": [
                    "Kamir 4x^3: x^4",
                    "Kamir 2x: x^2",
                    "Tambah pemalar: + c",
                ],
            },
        ],
        2: [
            {
                "question_ms": "Nilaikan kamiran tentu ∫ dari 0 hingga 2 bagi (3x^2 + 1) dx.",
                "question_en": "Evaluate the definite integral ∫ from 0 to 2 of (3x^2 + 1) dx.",
                "expected": "10",
                "solution_steps": [
                    "Antiterbitan: [x^3 + x]",
                    "Had atas x = 2: 2^3 + 2 = 10",
                    "Had bawah x = 0: 0 + 0 = 0",
                    "Nilai: 10 - 0 = 10",
                ],
            },
        ],
        3: [
            {
                "question_ms": "Diberi dy/dx = 4x - 3 dan lengkung melalui titik (1, 5). Cari persamaan lengkung y.",
                "question_en": "Given dy/dx = 4x - 3 and the curve passes through (1, 5). Find the equation of the curve y.",
                "expected": "2*x^2 - 3*x + 6",
                "solution_steps": [
                    "y = ∫ (4x - 3) dx = 2x^2 - 3x + c",
                    "Gantikan (1, 5): 5 = 2(1)^2 - 3(1) + c => 5 = -1 + c => c = 6",
                    "Persamaan lengkung: y = 2x^2 - 3x + 6",
                ],
            },
        ],
    },
    "quad": {
        1: [
            {
                "question_ms": "Selesaikan persamaan kuadratik x^2 - 5x + 6 = 0.",
                "question_en": "Solve the quadratic equation x^2 - 5x + 6 = 0.",
                "expected": "2, 3",
                "solution_steps": [
                    "Faktorkan: (x - 2)(x - 3) = 0",
                    "Punca: x = 2, 3",
                ],
            },
        ],
        2: [
            {
                "question_ms": "Cari koordinat titik pusingan bagi fungsi kuadratik f(x) = x^2 - 6x + 8.",
                "question_en": "Find the coordinates of the turning point of f(x) = x^2 - 6x + 8.",
                "expected": "(3, -1)",
                "solution_steps": [
                    "f'(x) = 2x - 6 = 0 => x = 3",
                    "f(3) = 3^2 - 6(3) + 8 = 9 - 18 + 8 = -1",
                    "Titik pusingan: (3, -1)",
                ],
            },
        ],
        3: [
            {
                "question_ms": "Persamaan kuadratik x^2 - kx + 9 = 0 mempunyai dua punca sama. Cari nilai positif k.",
                "question_en": "The quadratic equation x^2 - kx + 9 = 0 has two equal roots. Find the positive value of k.",
                "expected": "6",
                "solution_steps": [
                    "b^2 - 4ac = 0 => (-k)^2 - 4(1)(9) = 0",
                    "k^2 - 36 = 0 => k = 6 (kerana k positif)",
                ],
            },
        ],
    },
    "ind": {
        1: [
            {
                "question_ms": "Permudahkan: (x^3 * x^4) / x^2.",
                "question_en": "Simplify: (x^3 * x^4) / x^2.",
                "expected": "x^5",
                "solution_steps": [
                    "x^(3 + 4 - 2) = x^5",
                ],
            },
        ],
        2: [
            {
                "question_ms": "Selesaikan persamaan indeks: 2^(x + 3) = 32.",
                "question_en": "Solve the index equation: 2^(x + 3) = 32.",
                "expected": "2",
                "solution_steps": [
                    "32 = 2^5",
                    "x + 3 = 5 => x = 2",
                ],
            },
        ],
        3: [
            {
                "question_ms": "Selesaikan persamaan: 3^(2x) - 10(3^x) + 9 = 0 untuk x > 0.",
                "question_en": "Solve: 3^(2x) - 10(3^x) + 9 = 0 for x > 0.",
                "expected": "2",
                "solution_steps": [
                    "Biarkan u = 3^x: u^2 - 10u + 9 = 0 => (u - 1)(u - 9) = 0",
                    "u = 1 => 3^x = 1 => x = 0 (bukan x > 0)",
                    "u = 9 => 3^x = 9 => x = 2",
                ],
            },
        ],
    },
}


def challenge_node(state: MissionState, llm: Optional[Any] = None) -> Dict[str, Any]:
    """
    Challenge Agent Node.
    Generates authentic SPM-style challenge questions with verified mathematical ground truth.
    Selects level-appropriate challenge matching student's current mastery trajectory.
    """
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    lang = getattr(state, "language", "ms") or "ms"
    current_activity = getattr(state, "current_activity", None)

    # Determine difficulty level (1, 2, or 3)
    difficulty = 1
    if current_activity and current_activity.difficulty:
        difficulty = max(1, min(3, int(current_activity.difficulty)))
    elif current_activity and current_activity.level:
        difficulty = max(1, min(3, int(current_activity.level)))

    topic_challenges = CHALLENGE_BANK.get(topic_id, CHALLENGE_BANK["dif"])
    level_list = topic_challenges.get(difficulty, topic_challenges.get(1, []))

    if not level_list:
        level_list = topic_challenges.get(1, [])

    # Pick a question (index by step count to cycle if multiple)
    budget = getattr(state, "budget", None)
    step_idx = (budget.steps_taken if budget else 0) % len(level_list)
    item = level_list[step_idx]

    question_text = item["question_ms"] if lang == "ms" else item["question_en"]
    expected_ans = item["expected"]
    solution_steps = item.get("solution_steps", [])

    if current_activity:
        current_activity.question = question_text
        current_activity.expected_answer = expected_ans
        current_activity.correct_answer = expected_ans
        current_activity.difficulty = difficulty
        current_activity.level = difficulty
        current_activity.solution_steps = solution_steps
        if not current_activity.title:
            current_activity.title = f"Cabaran SPM Tahap {difficulty} ({topic_id.upper()})"

    trace_msg = (
        f"Challenge Agent: Generated SPM Level {difficulty} challenge on '{topic_id}': "
        f"'{question_text}'. Expected ground truth: '{expected_ans}'"
    )

    return {
        "status": MissionStatus.WAITING_FOR_STUDENT,
        "current_activity": current_activity,
        "current_agent": "challenge",
        "trace": [trace_msg],
    }
