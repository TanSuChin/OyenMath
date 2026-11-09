"""OyenMath Autonomous AI Learning Platform - Verification Engine Test Suite.

Milestone M2: Authoritative SymPy deterministic verification engine tests.

Test Coverage:
1. Differentiation verification across polynomial derivatives, product/quotient rule,
   and chain rule with SPM variables (t, r, h, theta).
2. Indefinite integration verification with and without '+ C', asserting forgot_c error tag.
3. Definite integrals and area calculations with proper constant_of_integration_valid handling.
4. Quadratic analysis verification (discriminants, roots as unordered sets, vertex as ordered pairs, axis of symmetry).
5. Comprehensive diagnostic error tagging: wrong_power (exp), sign_error (sign), arithmetic (coef/roots/coords), syntax_error.
6. Mastery protection: enforcing that mastery score updates are strictly rejected unless verified_by == 'sympy' and is_correct == True.
7. LLM confidence isolation: verifying that LLM confidence alone (even 1.0 / 100%) never increases mastery or overrides SymPy.
"""

from __future__ import annotations

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy as sp
from agents import math_tools as mt
from agents import verification as verif
from agents.state import VerificationResult


class TestDifferentiationVerification(unittest.TestCase):
    """Test verify_submission across polynomial, product, quotient, and chain rule derivatives."""

    def test_polynomial_derivative_basic(self):
        """Standard polynomial differentiation d/dx(3x^2 + 5x - 2) = 6x + 5."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="6x + 5",
            expected_answer="6x + 5",
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.is_valid_syntax)
        self.assertTrue(res.is_mathematically_equivalent)
        self.assertEqual(res.verified_by, "sympy")
        self.assertTrue(res.sympy_verified)
        self.assertEqual(res.symbolic_diff, "0")
        self.assertIsNone(res.error_tag)

    def test_polynomial_derivative_equivalent_commuted(self):
        """Commuted terms 5 + 6x must evaluate as equivalent to 6x + 5."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="5 + 6x",
            expected_answer="6x + 5",
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.is_mathematically_equivalent)
        self.assertEqual(res.symbolic_diff, "0")

    def test_polynomial_derivative_with_equation_prefix(self):
        """Prefixes like 'dy/dx = 6x + 5' or 'y = 6x + 5' must be normalized and accepted."""
        for prefix in ("dy/dx = 6x + 5", "y = 6x + 5", "f(x) = 6x + 5"):
            with self.subTest(prefix=prefix):
                res = verif.verify_submission(
                    topic="dif",
                    question_type="derivative",
                    student_answer=prefix,
                    expected_answer="6x + 5",
                )
                self.assertTrue(res.is_correct)
                self.assertEqual(res.symbolic_diff, "0")

    def test_product_rule_derivative(self):
        """Product rule: d/dx[(2x + 1)(x - 3)] = 2(x - 3) + (2x + 1)(1) = 4x - 5.
        Student submits unexpanded form: 2*(x - 3) + (2x + 1).
        """
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="2*(x - 3) + (2x + 1)",
            expected_answer="4x - 5",
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.is_mathematically_equivalent)
        self.assertEqual(res.symbolic_diff, "0")

    def test_quotient_rule_derivative(self):
        """Quotient rule: d/dx[x / (x + 1)] = ((x + 1) - x) / (x + 1)^2 = 1 / (x + 1)^2.
        Student submits unexpanded quotient rule form.
        """
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="((x + 1) - x) / ((x + 1)^2)",
            expected_answer="1 / ((x + 1)^2)",
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.is_mathematically_equivalent)
        self.assertEqual(res.symbolic_diff, "0")

    def test_chain_rule_kinematics_variable_t(self):
        """Kinematics variable t: s = (3t - 2)^4, ds/dt = 12(3t - 2)^3."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="12*(3t - 2)^3",
            expected_answer="12*(3t - 2)^3",
            context={"var": "t"},
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.is_mathematically_equivalent)
        self.assertEqual(res.symbolic_diff, "0")

    def test_chain_rule_kinematics_with_equation_prefix(self):
        """Kinematics: ds/dt = 10t + 2 or v = 10t + 2."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="ds/dt = 10t + 2",
            expected_answer="10t + 2",
            context={"var": "t"},
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")

    def test_chain_rule_geometry_variables_r_and_h(self):
        """Geometry variable r: Sphere volume V = (4/3)*pi*r^3, dV/dr = 4*pi*r^2."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="4 * pi * r^2",
            expected_answer="4*pi*r^2",
            context={"var": "r"},
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")

        # Geometry variable h: Cylinder volume rate dh with height h
        res_h = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="2 * pi * r * h",
            expected_answer="2*pi*r*h",
            context={"var": "h"},
        )
        self.assertTrue(res_h.is_correct)

    def test_chain_rule_angle_theta(self):
        """Angle variable theta: d/d(theta) [sin(theta)] = cos(theta).
        Accepts both 'theta' and Greek symbol 'θ'.
        """
        res_greek = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="cos(θ)",
            expected_answer="cos(theta)",
            context={"var": "theta"},
        )
        self.assertTrue(res_greek.is_correct)
        self.assertEqual(res_greek.symbolic_diff, "0")

        res_word = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="cos(theta)",
            expected_answer="cos(theta)",
            context={"var": "theta"},
        )
        self.assertTrue(res_word.is_correct)

    def test_chain_rule_radical_variable(self):
        """Differentiation with radical: y = sqrt(2x + 1), dy/dx = 1 / sqrt(2x + 1)."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="1 / √(2x + 1)",
            expected_answer="1 / sqrt(2x + 1)",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")


class TestIntegrationVerification(unittest.TestCase):
    """Test indefinite integration (+ C requirement and forgot_c tagging), definite integrals, and area."""

    def test_indefinite_integral_with_valid_c(self):
        """Indefinite integral with explicit '+ C' passes verification."""
        res = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="2x^3 + C",
            expected_answer="2x^3 + C",
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.is_mathematically_equivalent)
        self.assertTrue(res.constant_of_integration_valid)
        self.assertEqual(res.symbolic_diff, "0")
        self.assertIsNone(res.error_tag)

    def test_indefinite_integral_with_lowercase_c(self):
        """Indefinite integral with lowercase '+ c' is accepted."""
        res = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="2x^3 + c",
            expected_answer="2x^3 + C",
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.constant_of_integration_valid)

    def test_indefinite_integral_missing_c_tagged_forgot_c(self):
        """Student with correct algebra but missing '+ C' must receive forgot_c error tag."""
        res = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="2x^3",
            expected_answer="2x^3 + C",
        )
        self.assertFalse(res.is_correct)
        self.assertTrue(res.is_valid_syntax)
        self.assertFalse(res.is_mathematically_equivalent)
        self.assertFalse(res.constant_of_integration_valid)
        self.assertEqual(res.error_type, "forgot_c")
        self.assertEqual(res.error_tag, verif.TAG_FORGOT_C)
        self.assertIn("pemalar pengamiran + C", res.feedback)
        self.assertEqual(res.symbolic_diff, "-C")

    def test_indefinite_integral_context_require_constant(self):
        """context={'require_constant': True} enforces '+ C' even if expected omits it."""
        res = verif.verify_submission(
            topic="integ",
            question_type="integral",
            student_answer="x^4",
            expected_answer="x^4 + C",
            context={"require_constant": True},
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_FORGOT_C)
        self.assertFalse(res.constant_of_integration_valid)

    def test_indefinite_integral_algebra_error_not_masked_by_missing_c(self):
        """When algebra is also incorrect, don't just say forgot_c; diagnose algebraic error."""
        res = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="3x^2",  # Wrong power/coef vs 2x^3 + C
            expected_answer="2x^3 + C",
        )
        self.assertFalse(res.is_correct)
        self.assertNotEqual(res.error_tag, verif.TAG_FORGOT_C)
        self.assertIn(res.error_tag, (verif.TAG_WRONG_POWER, verif.TAG_ARITHMETIC))

    def test_definite_integral_correct_evaluation(self):
        """Definite integral: int_0^3 2x dx = 9. Must not demand + C."""
        res = verif.verify_submission(
            topic="integ",
            question_type="definite",
            student_answer="9",
            expected_answer="9",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")
        self.assertIsNone(res.constant_of_integration_valid)  # Definite has no constant of integration
        self.assertIsNone(res.error_tag)

    def test_definite_integral_fractional_result(self):
        """Definite integral with fractional bounds/result: int_0^1 x^2 dx = 1/3."""
        res = verif.verify_submission(
            topic="integ",
            question_type="definite",
            student_answer="1/3",
            expected_answer="1/3",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")

    def test_definite_integral_incorrect_arithmetic(self):
        """Definite integral with incorrect arithmetic value."""
        res = verif.verify_submission(
            topic="integ",
            question_type="definite",
            student_answer="8",
            expected_answer="9",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)
        self.assertIsNone(res.constant_of_integration_valid)

    def test_area_calculation_under_curve(self):
        """Area calculation under curve: question_type='area'."""
        res = verif.verify_submission(
            topic="integ",
            question_type="area",
            student_answer="16/3",
            expected_answer="16/3",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")
        self.assertIsNone(res.constant_of_integration_valid)

    def test_integration_with_spm_variable_t(self):
        """Indefinite integral with kinematics variable t: int (6t^2 + 4t) dt = 2t^3 + 2t^2 + C."""
        res = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="2t^3 + 2t^2 + C",
            expected_answer="2*t**3 + 2*t**2 + C",
            context={"var": "t"},
        )
        self.assertTrue(res.is_correct)
        self.assertTrue(res.constant_of_integration_valid)


class TestQuadraticVerification(unittest.TestCase):
    """Test quadratic analysis verification: discriminants, roots as sets, vertex as coordinates, axis of symmetry."""

    def test_quadratic_discriminant_correct(self):
        """Discriminant of 2x^2 - 4x - 6: b^2 - 4ac = (-4)^2 - 4(2)(-6) = 64."""
        res = verif.verify_submission(
            topic="quad",
            question_type="discriminant",
            student_answer="64",
            expected_answer="64",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")
        self.assertIsNone(res.error_tag)

    def test_quadratic_discriminant_arithmetic_error(self):
        """Incorrect discriminant value."""
        res = verif.verify_submission(
            topic="quad",
            question_type="discriminant",
            student_answer="60",
            expected_answer="64",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)

    def test_quadratic_roots_unordered_set_match(self):
        """Roots match regardless of order: 'x = -1, 3' == '3, -1'."""
        permutations = [
            ("x = -1, 3", "3, -1"),
            ("-1, 3", "3, -1"),
            ("[-1, 3]", "3, -1"),
            ("x = 3, x = -1", "-1, 3"),
        ]
        for s_ans, e_ans in permutations:
            with self.subTest(student=s_ans, expected=e_ans):
                res = verif.verify_submission(
                    topic="quad",
                    question_type="roots",
                    student_answer=s_ans,
                    expected_answer=e_ans,
                )
                self.assertTrue(res.is_correct)
                self.assertEqual(res.symbolic_diff, "0")

    def test_quadratic_roots_arithmetic_mismatch(self):
        """Roots with incorrect values are rejected with TAG_ARITHMETIC."""
        res = verif.verify_submission(
            topic="quad",
            question_type="roots",
            student_answer="x = -1, 4",
            expected_answer="-1, 3",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)
        self.assertEqual(res.error_type, "roots")

    def test_quadratic_roots_missing_one_root(self):
        """Only providing one root for a 2-root equation is rejected."""
        res = verif.verify_submission(
            topic="quad",
            question_type="roots",
            student_answer="x = -1",
            expected_answer="-1, 3",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)

    def test_quadratic_vertex_ordered_pair_match(self):
        """Vertex of 2x^2 - 4x - 6 is (1, -8). Matching ordered pair accepted."""
        for v_str in ("(1, -8)", "1, -8", "x = 1, y = -8"):
            with self.subTest(v_str=v_str):
                res = verif.verify_submission(
                    topic="quad",
                    question_type="vertex",
                    student_answer=v_str,
                    expected_answer="(1, -8)",
                )
                self.assertTrue(res.is_correct)
                self.assertEqual(res.symbolic_diff, "0")

    def test_quadratic_vertex_swapped_coordinates_rejected(self):
        """Vertex coordinates are ordered! (-8, 1) is NOT equivalent to (1, -8)."""
        res = verif.verify_submission(
            topic="quad",
            question_type="vertex",
            student_answer="(-8, 1)",
            expected_answer="(1, -8)",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)
        self.assertEqual(res.error_type, "coordinate")

    def test_quadratic_axis_of_symmetry(self):
        """Axis of symmetry x = 1 (or 1) matches expected 'x = 1'."""
        for ans in ("x = 1", "1"):
            with self.subTest(ans=ans):
                res = verif.verify_submission(
                    topic="quad",
                    question_type="axis_of_symmetry",
                    student_answer=ans,
                    expected_answer="x = 1",
                )
                self.assertTrue(res.is_correct)

        # Incorrect axis of symmetry
        res_bad = verif.verify_submission(
            topic="quad",
            question_type="axis_of_symmetry",
            student_answer="x = 2",
            expected_answer="x = 1",
        )
        self.assertFalse(res_bad.is_correct)


class TestDiagnosticErrorClassification(unittest.TestCase):
    """Test detailed error diagnostics: wrong_power, sign_error, arithmetic, syntax_error, empty."""

    def test_diagnostic_wrong_power(self):
        """Student differentiated incorrectly with wrong power: 6x^2 + 5 instead of 6x + 5."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="6x^2 + 5",
            expected_answer="6x + 5",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_WRONG_POWER)
        self.assertEqual(res.error_type, "exp")
        self.assertIn("kuasa pembolehubah", res.feedback)

    def test_diagnostic_wrong_power_kinematics(self):
        """Kinematics: wrong power in variable t."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="12t^3 - 4",
            expected_answer="12t^2 - 4",
            context={"var": "t"},
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_WRONG_POWER)

    def test_diagnostic_sign_error_total_inversion(self):
        """Total sign inversion (S + E == 0): -6x - 5 vs 6x + 5."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="-6x - 5",
            expected_answer="6x + 5",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_SIGN_ERROR)
        self.assertEqual(res.error_type, "sign")
        self.assertIn("tanda keseluruhan terbalik", res.feedback)

    def test_diagnostic_sign_error_partial(self):
        """Partial sign error: 6x - 5 vs 6x + 5 (constant term has wrong sign)."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="6x - 5",
            expected_answer="6x + 5",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_SIGN_ERROR)
        self.assertEqual(res.error_type, "sign")
        self.assertIn("kesilapan tanda", res.feedback)

    def test_diagnostic_sign_error_quadratic(self):
        """Partial sign error in quadratic: 3x^2 + 4x + 1 vs 3x^2 - 4x + 1."""
        res = verif.verify_submission(
            topic="quad",
            question_type="expression",
            student_answer="3x^2 + 4x + 1",
            expected_answer="3x^2 - 4x + 1",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_SIGN_ERROR)

    def test_diagnostic_arithmetic_coefficient(self):
        """Arithmetic error: 5x + 5 vs 6x + 5 (wrong coefficient, same power)."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="5x + 5",
            expected_answer="6x + 5",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)
        self.assertEqual(res.error_type, "coef")
        self.assertIn("pengiraan pekali", res.feedback)

    def test_diagnostic_arithmetic_constant_offset(self):
        """Arithmetic error: constant difference 6x + 7 vs 6x + 5."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="6x + 7",
            expected_answer="6x + 5",
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_ARITHMETIC)

    def test_diagnostic_syntax_error(self):
        """Syntax error: unparseable math string (unbalanced brackets, operator clash)."""
        bad_syntaxes = [
            "6x^^2 + 5",
            "((6x + 5",
            "6x + * 5",
            "6x + / 5",
        ]
        for bad in bad_syntaxes:
            with self.subTest(bad=bad):
                res = verif.verify_submission(
                    topic="dif",
                    question_type="derivative",
                    student_answer=bad,
                    expected_answer="6x + 5",
                )
                self.assertFalse(res.is_correct)
                self.assertFalse(res.is_valid_syntax)
                self.assertEqual(res.error_tag, verif.TAG_SYNTAX_ERROR)
                self.assertEqual(res.error_type, "syntax")
                self.assertIn("tidak sah", res.feedback)

    def test_diagnostic_empty_answer(self):
        """Empty student answer returns TAG_EMPTY."""
        for empty in ("", "   ", None):
            with self.subTest(empty=empty):
                res = verif.verify_submission(
                    topic="dif",
                    question_type="derivative",
                    student_answer=empty,
                    expected_answer="6x + 5",
                )
                self.assertFalse(res.is_correct)
                self.assertFalse(res.is_valid_syntax)
                self.assertEqual(res.error_tag, verif.TAG_EMPTY)
                self.assertEqual(res.error_type, "empty")


class TestMasteryProtection(unittest.TestCase):
    """Enforce Requirement R5: Only SymPy-verified results can increase mastery.
    LLM confidence alone must never determine mathematical correctness or increase mastery.
    """

    def test_can_update_mastery_true_only_for_sympy_and_correct(self):
        """Valid SymPy verification with is_correct=True allows mastery update."""
        valid_res = VerificationResult(
            verified_by="sympy",
            is_correct=True,
            is_valid_syntax=True,
            is_mathematically_equivalent=True,
            sympy_verified=True,
        )
        self.assertTrue(verif.can_update_mastery(valid_res))

    def test_can_update_mastery_rejects_llm_source(self):
        """LLM source is strictly rejected even if is_correct=True."""
        llm_res = {
            "verified_by": "llm",
            "is_correct": True,
            "sympy_verified": False,
            "confidence": 1.0,
        }
        self.assertFalse(verif.can_update_mastery(llm_res))

    def test_can_update_mastery_rejects_rule_based_or_mock(self):
        """Rule-based or mock verifications cannot update mastery."""
        for source in ("rule_based", "mock", "heuristic", "agent_grader"):
            with self.subTest(source=source):
                v_res = {
                    "verified_by": source,
                    "is_correct": True,
                    "sympy_verified": False,
                }
                self.assertFalse(verif.can_update_mastery(v_res))

    def test_can_update_mastery_rejects_incorrect_sympy(self):
        """SymPy verification that found student answer incorrect must not update mastery."""
        wrong_res = VerificationResult(
            verified_by="sympy",
            is_correct=False,
            is_valid_syntax=True,
            is_mathematically_equivalent=False,
            sympy_verified=True,
            error_tag=verif.TAG_WRONG_POWER,
        )
        self.assertFalse(verif.can_update_mastery(wrong_res))

    def test_can_update_mastery_rejects_unflagged_sympy(self):
        """verified_by='sympy' without sympy_verified flag is rejected."""
        tampered_res = {
            "verified_by": "sympy",
            "is_correct": True,
            "sympy_verified": False,
        }
        self.assertFalse(verif.can_update_mastery(tampered_res))

    def test_can_update_mastery_handles_invalid_types(self):
        """Invalid types return False safely."""
        for invalid in (None, 123, "string", [], ()):
            with self.subTest(invalid=invalid):
                self.assertFalse(verif.can_update_mastery(invalid))

    def test_assert_sympy_mastery_authority_raises_permission_error(self):
        """Attempting to update mastery without SymPy raises PermissionError."""
        bad_verification = {
            "verified_by": "llm",
            "is_correct": True,
            "sympy_verified": False,
        }
        with self.assertRaises(PermissionError) as ctx:
            verif.assert_sympy_mastery_authority(bad_verification)
        self.assertIn("Mastery update rejected", str(ctx.exception))
        self.assertIn("LLM confidence alone must never increase mastery", str(ctx.exception))

    def test_calculate_verified_mastery_updates_lawfully(self):
        """calculate_verified_mastery smoothly updates score using formula: cur + inc * (1 - cur)."""
        valid_res = VerificationResult(
            verified_by="sympy",
            is_correct=True,
            is_valid_syntax=True,
            is_mathematically_equivalent=True,
            sympy_verified=True,
        )
        # Starting at 0.50, increment 0.10: 0.50 + 0.10 * (1 - 0.50) = 0.55
        score_1 = verif.calculate_verified_mastery(0.50, valid_res, increment=0.10)
        self.assertEqual(score_1, 0.55)

        # Starting at 0.0, increment 0.20: 0.0 + 0.20 * 1.0 = 0.20
        score_2 = verif.calculate_verified_mastery(0.0, valid_res, increment=0.20)
        self.assertEqual(score_2, 0.20)

        # High mastery asymptotically approaches 1.0 (starting at 0.90, + 0.10 * (1 - 0.90) = 0.91)
        score_3 = verif.calculate_verified_mastery(0.90, valid_res, increment=0.10)
        self.assertEqual(score_3, 0.91)
        self.assertGreater(score_3, 0.90)
        self.assertLessEqual(score_3, 1.0)

    def test_calculate_verified_mastery_rejects_non_sympy(self):
        """calculate_verified_mastery raises PermissionError on non-SymPy inputs."""
        spoofed_llm = {
            "verified_by": "llm",
            "is_correct": True,
            "sympy_verified": False,
            "llm_confidence": 0.999,
        }
        with self.assertRaises(PermissionError):
            verif.calculate_verified_mastery(0.50, spoofed_llm)

    def test_llm_confidence_alone_never_overrides_sympy(self):
        """Comprehensive proof: Even if LLM has 100% confidence, SymPy's judgment is absolute."""
        # 1. Student entered wrong answer (e.g. 5x + 5 instead of 6x + 5)
        sympy_result = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="5x + 5",
            expected_answer="6x + 5",
        )
        self.assertFalse(sympy_result.is_correct)

        # 2. Suppose an LLM hallucinated that 5x + 5 is correct with 100% confidence
        llm_hallucination = {
            "verified_by": "llm",
            "is_correct": True,
            "confidence": 1.00,
            "reasoning": "The student answer looks very good and creative!",
        }

        # 3. Check that the system rejects the LLM claim
        self.assertFalse(verif.can_update_mastery(llm_hallucination))
        with self.assertRaises(PermissionError):
            verif.calculate_verified_mastery(0.50, llm_hallucination)

        # 4. Check that SymPy result cannot update mastery because it's incorrect
        self.assertFalse(verif.can_update_mastery(sympy_result))
        with self.assertRaises(PermissionError):
            verif.calculate_verified_mastery(0.50, sympy_result)


if __name__ == "__main__":
    unittest.main()
