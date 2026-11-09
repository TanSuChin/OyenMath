"""
OyenMath Autonomous AI Learning Platform - Learning Plan Generator Node
Milestone M3: Generates or adapts a structured sequence of PlanSteps (ActivityDefs).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from ..state import ActivityDef, ActivityStatus, LearningPlan, MissionState, now_utc_iso


# Alias PlanStep to ActivityDef for specification compliance
PlanStep = ActivityDef

TOPIC_TITLES = {
    "dif": "Pembezaan / Differentiation",
    "integ": "Pengamiran / Integration",
    "quad": "Persamaan Kuadratik / Quadratic Equations",
    "ind": "Hukum Indeks & Logaritma / Indices & Logarithms",
}


def create_initial_plan(
    topic_id: str,
    target_mastery: float = 0.80,
    has_prerequisite_gap: bool = False,
    prereq_topic: Optional[str] = None,
) -> LearningPlan:
    """Generate a fresh structured pedagogical roadmap for a topic."""
    activities: List[ActivityDef] = []
    topic_title = TOPIC_TITLES.get(topic_id, topic_id.upper())

    # 1. Prerequisite Remediation Step (if diagnostic gap detected)
    if has_prerequisite_gap:
        prereq_code = prereq_topic or "ind"
        prereq_title = TOPIC_TITLES.get(prereq_code, prereq_code.upper())
        activities.append(
            ActivityDef(
                activity_id=f"step_{uuid.uuid4().hex[:6]}",
                type="prerequisite",
                topic=prereq_code,
                level=1,
                difficulty=1,
                title=f"Langkah Prasyarat: Ulang Kaji {prereq_title}",
                description="Kukuhkan konsep asas prasyarat sebelum meneruskan topik utama.",
                agent_assigned="prerequisite",
                is_prerequisite=True,
                status=ActivityStatus.PENDING.value,
            )
        )

    # 2. Teaching Step: Core Concept & Mascot Analogy
    activities.append(
        ActivityDef(
            activity_id=f"step_{uuid.uuid4().hex[:6]}",
            type="teaching",
            topic=topic_id,
            level=1,
            difficulty=1,
            title=f"Pengenalan Konsep & Petua Oyen: {topic_title}",
            description="Penerangan konsep asas bersama Oyen menggunakan analogi mesra pelajar.",
            agent_assigned="teaching",
            is_prerequisite=False,
            status=ActivityStatus.PENDING.value,
        )
    )

    # 3. Teaching Step: Worked Example
    activities.append(
        ActivityDef(
            activity_id=f"step_{uuid.uuid4().hex[:6]}",
            type="teaching",
            topic=topic_id,
            level=1,
            difficulty=1,
            title=f"Contoh Kerja Terperinci Oyen: {topic_title}",
            description="Langkah demi langkah menyelesaikan soalan tipikal SPM.",
            agent_assigned="teaching",
            is_prerequisite=False,
            status=ActivityStatus.PENDING.value,
        )
    )

    # 4. Challenge Step: Guided Practice (Difficulty 1)
    activities.append(
        ActivityDef(
            activity_id=f"step_{uuid.uuid4().hex[:6]}",
            type="challenge",
            topic=topic_id,
            level=1,
            difficulty=1,
            title=f"Latihan Berpandu SPM Tahap 1: {topic_title}",
            description="Uji kefahaman asas dengan soalan format SPM Kertas 1.",
            agent_assigned="challenge",
            is_prerequisite=False,
            status=ActivityStatus.PENDING.value,
        )
    )

    # 5. Challenge Step: Standard SPM Challenge (Difficulty 2)
    activities.append(
        ActivityDef(
            activity_id=f"step_{uuid.uuid4().hex[:6]}",
            type="challenge",
            topic=topic_id,
            level=2,
            difficulty=2,
            title=f"Cabaran Penguasaan SPM Tahap 2: {topic_title}",
            description="Soalan standard SPM dengan aplikasi petua rantai / kamiran tentu.",
            agent_assigned="challenge",
            is_prerequisite=False,
            status=ActivityStatus.PENDING.value,
        )
    )

    # 6. Challenge Step: Mastery Challenge (Difficulty 3)
    activities.append(
        ActivityDef(
            activity_id=f"step_{uuid.uuid4().hex[:6]}",
            type="challenge",
            topic=topic_id,
            level=3,
            difficulty=3,
            title=f"Cabaran Penguasaan Skor A Tahap 3: {topic_title}",
            description="Soalan KBAT SPM aras tinggi untuk mencapai sasaran penguasaan.",
            agent_assigned="challenge",
            is_prerequisite=False,
            status=ActivityStatus.PENDING.value,
        )
    )

    return LearningPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        topic=topic_id,
        target_topic=topic_id,
        target_mastery=target_mastery,
        current_step_index=0,
        activities=activities,
        estimated_steps=len(activities),
        adaptive_replan_count=0,
        created_at=now_utc_iso(),
        updated_at=now_utc_iso(),
    )


def adapt_existing_plan(
    existing_plan: LearningPlan,
    state: MissionState,
) -> LearningPlan:
    """Adaptively adjust remaining plan activities based on observed performance and error patterns."""
    activities = list(existing_plan.activities)
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    diagnosis = getattr(state, "diagnosis", {}) or {}
    error_tags = getattr(state, "error_tags", {}) or {}

    # Identify misconceptions to target
    remedial_title = None
    if error_tags.get("forgot_c", 0) >= 1 or diagnosis.get("misconception") == "forgot_c":
        remedial_title = "Latihan Pengukuhan: Pemalar Kamiran (+ C)"
    elif error_tags.get("wrong_power", 0) >= 1 or error_tags.get("exp", 0) >= 1:
        remedial_title = "Latihan Pengukuhan: Petua Kuasa & Indeks"
    elif error_tags.get("sign_error", 0) >= 1:
        remedial_title = "Latihan Pengukuhan: Pengurusan Tanda & Kurungan"
    else:
        remedial_title = "Latihan Pengukuhan Tambahan SPM"

    # Append an adaptive remedial challenge step
    new_step = ActivityDef(
        activity_id=f"step_remedial_{uuid.uuid4().hex[:6]}",
        type="challenge",
        topic=topic_id,
        level=2,
        difficulty=2,
        title=remedial_title,
        description="Langkah penyesuaian untuk mengatasi salah faham yang dikesan.",
        agent_assigned="challenge",
        is_prerequisite=False,
        status=ActivityStatus.PENDING.value,
    )
    activities.append(new_step)

    existing_plan.activities = activities
    existing_plan.adaptive_replan_count += 1
    existing_plan.updated_at = now_utc_iso()
    existing_plan.estimated_steps = len(activities)
    return existing_plan


def learning_plan_node(state: MissionState) -> Dict[str, Any]:
    """
    Learning Plan Generator Agent Node.
    Constructs an initial structured sequence of PlanSteps or dynamically adapts the
    existing roadmap when triggered by the Autonomous Progress Evaluator.
    """
    topic_id = getattr(state, "topic_id", "dif") or "dif"
    goal = getattr(state, "goal", None)
    target_m = getattr(goal, "target_mastery", 0.80) if goal else 0.80

    diagnosis = getattr(state, "diagnosis", {}) or {}
    has_prereq_gap = bool(diagnosis.get("prerequisite_gap"))
    prereq_topic = diagnosis.get("prerequisite_topic")

    existing_plan = getattr(state, "plan", None)

    # Check if this is an adaptive replanning cycle
    if existing_plan and existing_plan.activities and len(existing_plan.activities) > 0:
        # Check if replanning is requested
        replan = adapt_existing_plan(existing_plan, state)
        trace_msg = (
            f"Learning Plan: Adapted roadmap (Replan #{replan.adaptive_replan_count}). "
            f"Total steps now: {len(replan.activities)}"
        )
        return {
            "plan": replan,
            "current_agent": "learning_plan",
            "trace": [trace_msg],
        }

    # Otherwise generate a fresh roadmap
    new_plan = create_initial_plan(
        topic_id=topic_id,
        target_mastery=target_m,
        has_prerequisite_gap=has_prereq_gap,
        prereq_topic=prereq_topic,
    )

    trace_msg = (
        f"Learning Plan: Generated initial structured roadmap with {len(new_plan.activities)} steps "
        f"for topic '{topic_id}' (Target: {target_m:.0%}, Prereq step: {has_prereq_gap})"
    )

    return {
        "plan": new_plan,
        "current_agent": "learning_plan",
        "trace": [trace_msg],
    }
