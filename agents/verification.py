"""OyenMath Autonomous AI Learning Platform - Deterministic Math Verification Engine.

Milestone M2: SymPy-backed Authoritative Verification Service for Student Submissions.

Mandatory Rules:
1. Pure SymPy deterministic verification (symbolic_diff == 0) is the sole arbiter of correctness.
2. LLM confidence alone must NEVER determine mathematical correctness or increase mastery.
3. Every student submission is verified deterministically with verified_by='sympy'.
4. Comprehensive diagnostic error tagging: forgot_c, wrong_power (exp), sign_error, arithmetic (coef), syntax_error.
5. Strict mastery authority enforcement: mastery score updates are rejected unless verified_by == 'sympy'.
"""

from __future__ import annotations

import math
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import sympy as sp

from . import math_tools as mt
from .state import VerificationResult


# =====================================================================
# Error Tagging Constants
# =====================================================================

TAG_FORGOT_C = "forgot_c"
TAG_WRONG_POWER = "wrong_power"  # also corresponds to 'exp'
TAG_SIGN_ERROR = "sign_error"
TAG_ARITHMETIC = "arithmetic"    # also corresponds to 'coef'
TAG_SYNTAX_ERROR = "syntax_error"
TAG_EMPTY = "empty_answer"
TAG_GENERAL = "general_error"


# =====================================================================
# Helper Diagnostics
# =====================================================================

def _extract_var_symbol(expr: sp.Expr) -> sp.Symbol:
    """Find the primary independent variable in a SymPy expression."""
    free = expr.free_symbols
    # Prefer x, then t, r, u, v, theta, y
    for preferred in (mt.x, mt.t, mt.r, mt.u, mt.v, mt.theta, mt.y):
        if preferred in free:
            return preferred
    for s in free:
        if s != mt.C:
            return s
    return mt.x


def _parse_multi_values(s: str) -> List[str]:
    """Parse comma-separated or bracketed values (e.g. roots 'x = -1, 3' or '[-1, 3]')."""
    clean = str(s).strip()
    # Strip only outer brackets [ ] and outer parentheses ( ), preserving internal LaTeX braces {}
    if (clean.startswith("(") and clean.endswith(")")) or (
        clean.startswith("[") and clean.endswith("]")
    ):
        clean = clean[1:-1].strip()
    clean = re.sub(r"\b[a-zA-Z]\s*=\s*", "", clean)
    parts = [p.strip() for p in clean.split(",") if p.strip()]
    return parts if parts else [s.strip()]


def _check_roots_match(student_ans: str, expected_ans: str) -> Tuple[bool, Optional[str]]:
    """Compare sets of roots for quadratic or polynomial equations."""
    s_roots = _parse_multi_values(student_ans)
    e_roots = _parse_multi_values(expected_ans)

    if not s_roots or not e_roots:
        return False, "tiada punca dikesan"

    if len(s_roots) != len(e_roots):
        return False, f"bilangan punca tidak sepadan ({len(s_roots)} vs {len(e_roots)})"

    matched_e: Set[int] = set()
    for s_item in s_roots:
        found_match = False
        for idx, e_item in enumerate(e_roots):
            if idx in matched_e:
                continue
            eq_res = mt.check_equivalence(s_item, e_item)
            if eq_res.get("equivalent"):
                matched_e.add(idx)
                found_match = True
                break
        if not found_match:
            return False, f"punca '{s_item}' tidak sepadan"

    return len(matched_e) == len(e_roots), None


def _check_coordinates_match(student_ans: str, expected_ans: str) -> Tuple[bool, Optional[str]]:
    """Compare ordered coordinates (e.g. vertex '(1, -8)' vs '(1, -8)')."""
    s_coords = _parse_multi_values(student_ans)
    e_coords = _parse_multi_values(expected_ans)

    if not s_coords or not e_coords:
        return False, "tiada koordinat dikesan"

    if len(s_coords) != len(e_coords):
        return False, f"bilangan koordinat tidak sepadan ({len(s_coords)} vs {len(e_coords)})"

    for idx, (s_item, e_item) in enumerate(zip(s_coords, e_coords)):
        eq_res = mt.check_equivalence(s_item, e_item)
        if not eq_res.get("equivalent"):
            return False, f"koordinat ke-{idx+1} '{s_item}' tidak sepadan (dijangka '{e_item}')"

    return True, None


def _diagnose_polynomial_error(
    parsed_student: sp.Expr,
    parsed_expected: sp.Expr,
    var: sp.Symbol,
) -> Tuple[str, str, str]:
    """Diagnose mathematical discrepancy between student and expected expression.

    Returns:
        (error_type, error_tag, feedback_message)
    """
    diff = sp.simplify(parsed_student - parsed_expected)

    # 1. Total sign inversion: S + E == 0
    if sp.simplify(parsed_student + parsed_expected) == 0:
        return (
            "sign",
            TAG_SIGN_ERROR,
            "Perhatikan tanda positif (+) dan negatif (-) dalam jawapan anda; tanda keseluruhan terbalik.",
        )

    # Try polynomial analysis if both are polynomials in var
    try:
        poly_s = sp.Poly(parsed_student, var)
        poly_e = sp.Poly(parsed_expected, var)

        # 2. Exponent / Power mismatch: degrees differ
        if poly_s.degree() != poly_e.degree():
            return (
                "exp",
                TAG_WRONG_POWER,
                f"Semak semula kuasa pembolehubah anda ({var}). Bagi pembezaan ax^n, kuasa berkurang satu menjadi n-1.",
            )

        # 3. Same degree, examine coefficients
        coeffs_s = poly_s.all_coeffs()
        coeffs_e = poly_e.all_coeffs()

        # Check for partial sign error: |c_s| == |c_e| for all coefficients
        if len(coeffs_s) == len(coeffs_e):
            signs_differ = False
            magnitudes_match = True
            for cs, ce in zip(coeffs_s, coeffs_e):
                if sp.simplify(abs(cs) - abs(ce)) != 0:
                    magnitudes_match = False
                    break
                if sp.simplify(cs + ce) == 0 and sp.simplify(cs) != 0:
                    signs_differ = True

            if magnitudes_match and signs_differ:
                return (
                    "sign",
                    TAG_SIGN_ERROR,
                    "Terdapat kesilapan tanda (+) atau (-) pada salah satu sebutan dalam jawapan anda.",
                )

        # 4. Arithmetic / Coefficient error
        return (
            "coef",
            TAG_ARITHMETIC,
            "Terdapat sedikit kesilapan dalam pengiraan pekali atau nombor pemalar.",
        )

    except Exception:
        pass

    # 5. Check if difference is a pure non-zero constant (arithmetic offset)
    if diff.is_number and diff != 0:
        return (
            "coef",
            TAG_ARITHMETIC,
            "Jawapan anda mempunyai kesilapan kira-kira nilai pemalar atau aritmetik.",
        )

    return (
        "general",
        TAG_GENERAL,
        "Jawapan belum tepat. Sila semak semula langkah pengiraan anda!",
    )


# =====================================================================
# Core Deterministic Verification Function
# =====================================================================

def verify_submission(
    topic: str,
    question_type: str,
    student_answer: str,
    expected_answer: str,
    context: Optional[Dict[str, Any]] = None,
) -> VerificationResult:
    """Authoritative deterministic mathematical verification via SymPy.

    Args:
        topic: Topic code ('dif', 'integ', 'quad', 'ind', etc.)
        question_type: Question category ('derivative', 'indefinite_integral', 'definite', 'roots', etc.)
        student_answer: Raw or LaTeX mathematical string from the student
        expected_answer: Ground truth reference solution
        context: Optional additional parameters (require_constant, var, etc.)

    Returns:
        VerificationResult model populated with deterministic grading output.
    """
    t0 = time.perf_counter()
    ctx = context or {}

    # 1. Empty answer guard
    if not student_answer or not str(student_answer).strip():
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return VerificationResult(
            verified_by="sympy",
            is_correct=False,
            is_valid_syntax=False,
            is_mathematically_equivalent=False,
            sympy_verified=True,
            error_type="empty",
            error_tag=TAG_EMPTY,
            feedback="Sila masukkan jawapan anda. / Please enter your answer.",
            execution_time_ms=duration_ms,
        )

    s_clean = str(student_answer).strip()
    e_clean = str(expected_answer).strip()

    # 2. Check for multi-value coordinates (ordered) or roots (unordered set)
    q_type_lower = str(question_type).lower()
    coord_keywords = (
        "vertex", "verteks", "point", "titik", "turning", "pusingan",
        "stationary", "pegun", "minimum", "maximum", "maksimum",
        "coordinate", "koordinat"
    )
    is_roots_type = (
        any(k in q_type_lower for k in ("roots", "punca", "quadratic_roots"))
        or "punca" in q_type_lower
        or "root" in q_type_lower
    )
    is_coord_type = (
        any(k in q_type_lower for k in coord_keywords)
        or (s_clean.startswith("(") and s_clean.endswith(")") and "," in s_clean)
        or (e_clean.startswith("(") and e_clean.endswith(")") and "," in e_clean)
    ) and not is_roots_type

    if is_coord_type:
        coords_match, coords_err = _check_coordinates_match(s_clean, e_clean)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        if coords_match:
            return VerificationResult(
                verified_by="sympy",
                is_correct=True,
                is_valid_syntax=True,
                is_mathematically_equivalent=True,
                algebraic_difference="0",
                symbolic_diff="0",
                sympy_verified=True,
                feedback="Tahniah! Titik koordinat / verteks adalah tepat. 🐱✨",
                execution_time_ms=duration_ms,
            )
        else:
            return VerificationResult(
                verified_by="sympy",
                is_correct=False,
                is_valid_syntax=True,
                is_mathematically_equivalent=False,
                sympy_verified=True,
                error_type="coordinate",
                error_tag=TAG_ARITHMETIC,
                feedback=f"Koordinat tidak tepat ({coords_err or 'semak semula nilai verteks'}).",
                execution_time_ms=duration_ms,
            )

    if is_roots_type or ("," in s_clean and "," in e_clean):
        roots_match, roots_err = _check_roots_match(s_clean, e_clean)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        if roots_match:
            return VerificationResult(
                verified_by="sympy",
                is_correct=True,
                is_valid_syntax=True,
                is_mathematically_equivalent=True,
                algebraic_difference="0",
                symbolic_diff="0",
                sympy_verified=True,
                feedback="Tahniah! Semua punca adalah tepat. 🐱✨",
                execution_time_ms=duration_ms,
            )
        else:
            return VerificationResult(
                verified_by="sympy",
                is_correct=False,
                is_valid_syntax=True,
                is_mathematically_equivalent=False,
                sympy_verified=True,
                error_type="roots",
                error_tag=TAG_ARITHMETIC,
                feedback=f"Punca tidak tepat ({roots_err or 'semak semula pemfaktoran'}).",
                execution_time_ms=duration_ms,
            )

    # 3. Parse student answer via safe parser
    try:
        parsed_student = mt.parse(s_clean)
    except Exception as ex:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return VerificationResult(
            verified_by="sympy",
            is_correct=False,
            is_valid_syntax=False,
            is_mathematically_equivalent=False,
            sympy_verified=True,
            error_type="syntax",
            error_tag=TAG_SYNTAX_ERROR,
            feedback="Ungkapan matematik tidak sah. Sila semak tanda kurung atau simbol (cth: 6x^2 + 5).",
            diagnostic_explanation=str(ex),
            execution_time_ms=duration_ms,
        )

    # 4. Parse expected answer
    try:
        parsed_expected = mt.parse(e_clean)
    except Exception as ex:
        # Fallback if expected contains unexpected notation
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return VerificationResult(
            verified_by="sympy",
            is_correct=False,
            is_valid_syntax=True,
            is_mathematically_equivalent=False,
            sympy_verified=True,
            error_type="reference_error",
            error_tag=TAG_GENERAL,
            feedback="Ralat rujukan soalan.",
            diagnostic_explanation=f"Expected answer could not be parsed: {ex}",
            execution_time_ms=duration_ms,
        )

    # 5. Indefinite integration: Constant of Integration (+ C) verification
    is_definite = q_type_lower in ("definite", "area", "kamiran_tentu", "luas", "volume", "isipadu", "isi_padu")
    is_indefinite_integral = (
        not is_definite
        and (
            q_type_lower in ("indefinite_integral", "integ", "integral", "kamiran_tak_tentu")
            or topic == "integ"
            or ctx.get("require_constant", False)
            or bool(re.search(r"\b[cC]\b", e_clean))
        )
    )

    if is_indefinite_integral:
        has_c_student = parsed_student.has(mt.C) or bool(re.search(r"\b[cC]\b", s_clean))
        has_c_expected = parsed_expected.has(mt.C) or bool(re.search(r"\b[cC]\b", e_clean))

        # If student forgot + C but the core integral is correct
        if not has_c_student and (has_c_expected or ctx.get("require_constant", False)):
            # Check if core algebraic parts are equivalent without C
            expected_core = parsed_expected - mt.C if has_c_expected else parsed_expected
            diff_no_c = sp.simplify(parsed_student - expected_core)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if diff_no_c == 0:
                return VerificationResult(
                    verified_by="sympy",
                    is_correct=False,
                    is_valid_syntax=True,
                    is_mathematically_equivalent=False,
                    constant_of_integration_valid=False,
                    symbolic_diff=str(-mt.C),
                    algebraic_difference=str(-mt.C),
                    sympy_verified=True,
                    error_type="forgot_c",
                    error_tag=TAG_FORGOT_C,
                    feedback="ALAMAK! Anda terlupa pemalar pengamiran + C! Dalam kamiran tak tentu, pemalar + C adalah wajib! 🐱",
                    diagnostic_explanation="Student omitted integration constant + C on indefinite integral.",
                    execution_time_ms=duration_ms,
                )

    # 6. Authoritative Symbolic Equivalence Check
    var_ctx = ctx.get("var")
    if var_ctx and var_ctx in mt._LOCAL_DICT:
        var_sym = mt._LOCAL_DICT[var_ctx]
    else:
        var_sym = _extract_var_symbol(parsed_expected)
    symbolic_difference = sp.simplify(parsed_student - parsed_expected)
    is_equivalent = bool(symbolic_difference == 0)

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    if is_equivalent:
        return VerificationResult(
            verified_by="sympy",
            is_correct=True,
            is_valid_syntax=True,
            is_mathematically_equivalent=True,
            algebraic_difference="0",
            symbolic_diff="0",
            constant_of_integration_valid=True if is_indefinite_integral else None,
            sympy_verified=True,
            feedback="Tahniah! Jawapan tepat dan sahih mengikut SymPy! 🐱✨",
            execution_time_ms=duration_ms,
        )

    # 7. Diagnose Discrepancy & Assign Error Tag
    err_type, err_tag, feedback_msg = _diagnose_polynomial_error(
        parsed_student, parsed_expected, var_sym
    )

    return VerificationResult(
        verified_by="sympy",
        is_correct=False,
        is_valid_syntax=True,
        is_mathematically_equivalent=False,
        algebraic_difference=str(symbolic_difference),
        symbolic_diff=str(symbolic_difference),
        constant_of_integration_valid=False if is_indefinite_integral and not parsed_student.has(mt.C) else None,
        sympy_verified=True,
        error_type=err_type,
        error_tag=err_tag,
        feedback=feedback_msg,
        diagnostic_explanation=f"SymPy symbolic diff: {symbolic_difference}",
        execution_time_ms=duration_ms,
    )


# =====================================================================
# Mastery Authority Enforcement
# =====================================================================

def can_update_mastery(verification: Union[VerificationResult, Dict[str, Any]]) -> bool:
    """Enforce Requirement R5: Only SymPy-verified results can increase mastery.

    Returns False if verification was produced by LLM, mock, rule-based, or non-SymPy sources.
    """
    if isinstance(verification, VerificationResult):
        v_dict = verification.model_dump()
    elif isinstance(verification, dict):
        v_dict = verification
    else:
        return False

    is_sympy = str(v_dict.get("verified_by", "")).lower() == "sympy"
    is_flagged = bool(v_dict.get("sympy_verified", False))
    is_correct = bool(v_dict.get("is_correct", False))

    return is_sympy and is_flagged and is_correct


def assert_sympy_mastery_authority(
    verification: Union[VerificationResult, Dict[str, Any]]
) -> None:
    """Raise PermissionError if mastery update is attempted without SymPy verification."""
    if not can_update_mastery(verification):
        if isinstance(verification, dict):
            v_by = verification.get("verified_by")
            is_corr = verification.get("is_correct")
        else:
            v_by = getattr(verification, "verified_by", None)
            is_corr = getattr(verification, "is_correct", None)
        raise PermissionError(
            f"Mastery update rejected: SymPy deterministic verification is the sole arbiter of correctness "
            f"(received verified_by='{v_by}', is_correct={is_corr}). LLM confidence alone must never increase mastery."
        )


def calculate_verified_mastery(
    current_mastery: float,
    verification: Union[VerificationResult, Dict[str, Any]],
    increment: float = 0.10,
) -> float:
    """Safely calculate updated mastery score, strictly enforcing SymPy verification.

    If verification was not verified by SymPy, raises PermissionError and refuses to change score.
    """
    assert_sympy_mastery_authority(verification)

    # Check if current_mastery is NaN or Inf; default to 0.0
    try:
        cur_f = float(current_mastery)
        if math.isnan(cur_f) or math.isinf(cur_f):
            cur = 0.0
        else:
            cur = max(0.0, min(1.0, cur_f))
    except (TypeError, ValueError):
        cur = 0.0

    # Check if increment is NaN or Inf; default to 0.10, clamp to [0.0, 1.0]
    try:
        inc_f = float(increment)
        if math.isnan(inc_f) or math.isinf(inc_f):
            inc = 0.10
        else:
            inc = max(0.0, min(1.0, inc_f))
    except (TypeError, ValueError):
        inc = 0.10

    new_mastery = cur + inc * (1.0 - cur)
    return round(max(0.0, min(1.0, new_mastery)), 2)
