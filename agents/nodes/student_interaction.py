"""
OyenMath Autonomous AI Learning Platform - Student Interaction Node
Milestone M3: Native LangGraph interrupt() gate for WAITING_FOR_STUDENT state & Command resume.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

from langgraph.types import interrupt

from ..state import MissionState, MissionStatus, StudentResponse, now_utc_iso

logger = logging.getLogger("oyen.nodes.student_interaction")


def _normalize_student_response(raw: Any) -> StudentResponse:
    """Normalize arbitrary resume input into a structured StudentResponse."""
    if isinstance(raw, StudentResponse):
        return raw
    if isinstance(raw, dict):
        ans = str(raw.get("answer") or raw.get("raw_answer") or "")
        return StudentResponse(
            answer=ans,
            raw_answer=str(raw.get("raw_answer") or ans),
            image_data=raw.get("image_data"),
            submitted_at=raw.get("submitted_at") or now_utc_iso(),
            ocr_result=raw.get("ocr_result"),
        )
    ans_str = str(raw or "").strip()
    return StudentResponse(
        answer=ans_str,
        raw_answer=ans_str,
        submitted_at=now_utc_iso(),
    )


def student_interaction_node(state: MissionState) -> Dict[str, Any]:
    """
    Student Interaction Agent Node.
    Transitions status to WAITING_FOR_STUDENT and pauses workflow via LangGraph interrupt().
    Upon resumption via Command(resume=...), transitions status back to RUNNING with student_response.
    """
    existing_resp = getattr(state, "student_response", None)
    if existing_resp is not None and getattr(existing_resp, "answer", None):
        # Already has an answer injected (e.g. testing or direct injection)
        trace_msg = f"Student Interaction: Processing existing response: '{existing_resp.answer}'"
        return {
            "status": MissionStatus.RUNNING,
            "current_agent": "student_interaction",
            "trace": [trace_msg],
        }

    curr_act = getattr(state, "current_activity", None)
    question_text = (
        (curr_act.question if curr_act else None)
        or "Sila masukkan jawapan anda. / Please enter your answer."
    )
    mission_id = getattr(state, "mission_id", "")
    student_id = getattr(state, "student_id", "")
    topic_id = getattr(state, "topic_id", "dif")

    interrupt_payload = {
        "mission_id": mission_id,
        "student_id": student_id,
        "activity_id": curr_act.activity_id if curr_act else None,
        "question": question_text,
        "topic": topic_id,
        "type": curr_act.type if curr_act else "challenge",
        "title": curr_act.title if curr_act else "Cabaran Pelajar",
        "timestamp": now_utc_iso(),
    }

    try:
        # Calls LangGraph native interrupt(). In a running StateGraph, this halts execution
        # until Command(resume=...) is supplied with the student answer.
        resumed_val = interrupt(interrupt_payload)
        student_resp = _normalize_student_response(resumed_val)

        trace_msg = (
            f"Student Interaction: Resumed from student input. "
            f"Answer: '{student_resp.answer}'. Transitioning status to RUNNING."
        )

        return {
            "status": MissionStatus.RUNNING,
            "student_response": student_resp,
            "waiting_interaction": None,
            "current_agent": "student_interaction",
            "trace": [trace_msg],
        }

    except RuntimeError:
        # Fallback when executed outside a LangGraph runnable context (e.g. isolated unit test)
        trace_msg = (
            f"Student Interaction: Standing by for student input (standalone context). "
            f"Question: '{question_text}'"
        )
        return {
            "status": MissionStatus.WAITING_FOR_STUDENT,
            "waiting_interaction": interrupt_payload,
            "current_agent": "student_interaction",
            "trace": [trace_msg],
        }
