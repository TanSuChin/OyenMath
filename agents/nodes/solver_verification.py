"""
OyenMath Autonomous AI Learning Platform - Solver Verification Node
Milestone M3: Deterministic verification gate using authoritative SymPy engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..state import MissionState, VerificationResult
from ..verification import verify_submission

logger = logging.getLogger("oyen.nodes.solver_verification")


def _determine_question_type(topic: str, expected_answer: str) -> str:
    """Infer the verification category for the SymPy verifier."""
    exp = str(expected_answer or "").strip()
    if topic == "integ":
        if "+c" in exp.lower().replace(" ", ""):
            return "indefinite_integral"
        return "definite"
    if topic == "dif":
        return "derivative"
    if topic == "quad":
        if "(" in exp and "," in exp:
            return "coordinates"
        if "," in exp:
            return "roots"
        return "expression"
    return "expression"


def solver_verification_node(state: MissionState) -> Dict[str, Any]:
    """
    Solver Verification Agent Node.
    Deterministic verification gate executing SymPy verification engine.
    Ensures LLM confidence alone never determines correctness or increases mastery.
    """
    student_resp = getattr(state, "student_response", None)
    student_ans = getattr(student_resp, "answer", "") if student_resp else ""
    current_activity = getattr(state, "current_activity", None)
    expected_ans = getattr(current_activity, "expected_answer", "") if current_activity else ""
    topic_id = getattr(state, "topic_id", "dif") or "dif"

    q_type = _determine_question_type(topic_id, expected_ans)

    # 1. Authoritative deterministic verification via SymPy
    v_result: VerificationResult = verify_submission(
        topic=topic_id,
        question_type=q_type,
        student_answer=student_ans,
        expected_answer=expected_ans,
    )

    # 2. Record tool execution in resource budget
    budget = getattr(state, "budget", None)
    if budget:
        budget.record_tool_call()

    trace_msg = (
        f"Solver Verification Gate (SymPy Authoritative): "
        f"is_correct={v_result.is_correct}, "
        f"verified_by='{v_result.verified_by}', "
        f"sympy_verified={v_result.sympy_verified}, "
        f"error_tag='{v_result.error_tag or 'none'}'"
    )

    return {
        "verification": v_result,
        "current_agent": "solver_verification",
        "trace": [trace_msg],
    }
