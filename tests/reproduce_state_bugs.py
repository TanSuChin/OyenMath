"""
tests/reproduce_state_bugs.py - Minimal Deterministic Reproducer for State Model Bugs

Identified Failure Modes:
Bug 1 (Critical): float('nan') mastery is clamped to 1.0 (100% mastery) instead of 0.0 or error.
Bug 2 (High): create_initial_mission_state bypasses Pydantic validation via setattr, creating poison checkpoints that fail deserialization.
Bug 3 (Medium): is_budget_exhausted fails silently on naive ISO timestamp strings due to offset-naive vs offset-aware TypeError.
Bug 4 (Medium): can_transition, is_terminal_status, and is_active_status fail on lowercase strings.
Bug 5 (Low): create_initial_mission_state(topic_id=None) crashes with ValidationError instead of defaulting.
"""

import math
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents.state import (
    MissionState,
    MissionStatus,
    can_transition,
    create_initial_mission_state,
    is_active_status,
    is_budget_exhausted,
    is_terminal_status,
    mission_state_from_dict,
    mission_state_to_dict,
)


def repro_bug_1_nan_awards_full_mastery():
    print("=== Repro Bug 1: NaN Mastery Awards 100% (1.0) Full Mastery ===")
    s = MissionState(mastery={"dif": float("nan")})
    score = s.mastery["dif"]
    print(f"Input: mastery={{'dif': float('nan')}}")
    print(f"Resulting mastery['dif']: {score}")
    if score == 1.0:
        print("BUG CONFIRMED: NaN was converted to 1.0 (100% mastery)! Unverified/unanswered student gets full credit.")
        return True
    return False


def repro_bug_2_poison_checkpoint():
    print("\n=== Repro Bug 2: setattr Validation Bypass Creates Poison Checkpoint ===")
    # Client passes negative budget
    s = create_initial_mission_state(budget={"max_steps": -999})
    print(f"State created with max_steps: {s.budget.max_steps}")
    # Saved to disk via mission_state_to_dict
    saved_data = mission_state_to_dict(s)
    print(f"Serialized to dict: budget.max_steps = {saved_data['budget']['max_steps']}")
    # Server restarts and attempts to reload checkpoint
    try:
        reloaded = mission_state_from_dict(saved_data)
        print("Reloaded successfully")
        return False
    except Exception as e:
        print(f"BUG CONFIRMED: Checkpoint reload crashed with {type(e).__name__}: {e}")
        print("The mission checkpoint is permanently unrecoverable on disk!")
        return True


def repro_bug_3_naive_datetime_budget_bypass():
    print("\n=== Repro Bug 3: is_budget_exhausted Fails Silently on Naive ISO Datetime ===")
    budget_dict = {
        "max_duration_seconds": 30,
        "started_at": "2020-01-01T00:00:00",  # Over 6 years ago
    }
    exhausted, reason = is_budget_exhausted(budget_dict)
    print(f"Input budget: started_at='2020-01-01T00:00:00', max_duration_seconds=30")
    print(f"Result: is_budget_exhausted = {exhausted}, reason = {reason}")
    if not exhausted:
        print("BUG CONFIRMED: Duration exhaustion was completely bypassed due to swallowed TypeError!")
        return True
    return False


def repro_bug_4_lowercase_status_helpers():
    print("\n=== Repro Bug 4: can_transition/is_terminal_status Case Sensitivity ===")
    t1 = can_transition("running", "paused")
    t2 = is_terminal_status("completed")
    t3 = is_active_status("running")
    print(f"can_transition('running', 'paused') = {t1} (expected True)")
    print(f"is_terminal_status('completed') = {t2} (expected True)")
    print(f"is_active_status('running') = {t3} (expected True)")
    if not t1 or not t2 or not t3:
        print("BUG CONFIRMED: Status helper functions fail on lowercase strings.")
        return True
    return False


def repro_bug_5_topic_id_none_crash():
    print("\n=== Repro Bug 5: create_initial_mission_state(topic_id=None) Crash ===")
    try:
        s = create_initial_mission_state(topic_id=None)
        print(f"State created: topic_id = {s.topic_id}")
        return False
    except Exception as e:
        print(f"BUG CONFIRMED: Calling with topic_id=None crashed with {type(e).__name__}: {e}")
        return True


if __name__ == "__main__":
    results = [
        repro_bug_1_nan_awards_full_mastery(),
        repro_bug_2_poison_checkpoint(),
        repro_bug_3_naive_datetime_budget_bypass(),
        repro_bug_4_lowercase_status_helpers(),
        repro_bug_5_topic_id_none_crash(),
    ]
    total_bugs = sum(1 for r in results if r)
    print(f"\n==========================================")
    print(f"TOTAL CONFIRMED BUGS REPRODUCED: {total_bugs} / {len(results)}")
    print(f"==========================================")
