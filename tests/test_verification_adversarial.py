"""Adversarial Stress Test Suite for agents/verification.py.

Milestone M2 Challenger 2 Verification Harness.
Stress-tests mastery tampering, grading equivalence bypasses, constant of integration bypasses,
and coordinate ordering / multi-value edge cases.
"""

from __future__ import annotations

import math
import os
import sys
import unittest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import math_tools as mt
from agents import verification as verif
from agents.state import VerificationResult


class TestMasteryAuthorityAdversarial(unittest.TestCase):
    """Stress-test assert_sympy_mastery_authority and calculate_verified_mastery."""

    def setUp(self):
        self.valid_sympy_result = VerificationResult(
            verified_by="sympy",
            is_correct=True,
            is_valid_syntax=True,
            is_mathematically_equivalent=True,
            sympy_verified=True,
        )

    def test_llm_source_rejected_at_confidence_one(self):
        """LLM verification with 100% confidence must be strictly rejected."""
        llm_payload = {
            "verified_by": "llm",
            "is_correct": True,
            "confidence": 1.0,
            "sympy_verified": False,
        }
        self.assertFalse(verif.can_update_mastery(llm_payload))
        with self.assertRaises(PermissionError):
            verif.assert_sympy_mastery_authority(llm_payload)
        with self.assertRaises(PermissionError):
            verif.calculate_verified_mastery(0.50, llm_payload)

    def test_case_sensitivity_sympy(self):
        """Test case-sensitivity of verified_by field."""
        # 'SymPy' with sympy_verified=True
        sympy_caps = {
            "verified_by": "SymPy",
            "is_correct": True,
            "sympy_verified": True,
        }
        # can_update_mastery lowercases the string
        self.assertTrue(verif.can_update_mastery(sympy_caps))

        # 'SymPy' without sympy_verified flag must be rejected
        sympy_caps_no_flag = {
            "verified_by": "SymPy",
            "is_correct": True,
            "sympy_verified": False,
        }
        self.assertFalse(verif.can_update_mastery(sympy_caps_no_flag))
        with self.assertRaises(PermissionError):
            verif.assert_sympy_mastery_authority(sympy_caps_no_flag)

        # ' sympy ' with padding must be rejected
        sympy_padded = {
            "verified_by": " sympy ",
            "is_correct": True,
            "sympy_verified": True,
        }
        self.assertFalse(verif.can_update_mastery(sympy_padded))

    def test_verified_by_none_rejected(self):
        """verified_by = None must be strictly rejected."""
        none_payload = {
            "verified_by": None,
            "is_correct": True,
            "sympy_verified": True,
        }
        self.assertFalse(verif.can_update_mastery(none_payload))
        with self.assertRaises(PermissionError):
            verif.assert_sympy_mastery_authority(none_payload)
        with self.assertRaises(PermissionError):
            verif.calculate_verified_mastery(0.50, none_payload)

    def test_is_correct_false_high_confidence_rejected(self):
        """is_correct = False with high confidence must be strictly rejected."""
        false_payload = {
            "verified_by": "sympy",
            "is_correct": False,
            "sympy_verified": True,
            "confidence": 1.0,
        }
        self.assertFalse(verif.can_update_mastery(false_payload))
        with self.assertRaises(PermissionError):
            verif.assert_sympy_mastery_authority(false_payload)
        with self.assertRaises(PermissionError):
            verif.calculate_verified_mastery(0.50, false_payload)

    def test_mastery_nan_current_value(self):
        """REMEDIATED: calculate_verified_mastery defaults NaN current_mastery to 0.0."""
        score = verif.calculate_verified_mastery(float("nan"), self.valid_sympy_result)
        self.assertFalse(math.isnan(score))
        self.assertEqual(score, 0.10)

    def test_mastery_nan_increment(self):
        """REMEDIATED: calculate_verified_mastery defaults NaN increment to 0.10."""
        score = verif.calculate_verified_mastery(
            0.50, self.valid_sympy_result, increment=float("nan")
        )
        self.assertEqual(score, 0.55)

    def test_mastery_inf_and_negatives(self):
        """REMEDIATED: calculate_verified_mastery with infinity and negative floats."""
        # Infinity current mastery defaulted to 0.0, updated by 0.10 -> 0.10
        score_inf = verif.calculate_verified_mastery(float("inf"), self.valid_sympy_result)
        self.assertEqual(score_inf, 0.10)

        # Negative infinity current mastery clamped to 0.0, then updated
        score_neg_inf = verif.calculate_verified_mastery(
            float("-inf"), self.valid_sympy_result, increment=0.10
        )
        self.assertEqual(score_neg_inf, 0.10)

        # Negative current mastery clamped to 0.0, then updated
        score_neg = verif.calculate_verified_mastery(
            -0.50, self.valid_sympy_result, increment=0.10
        )
        self.assertEqual(score_neg, 0.10)

        # Negative increment clamped to 0.0, so score stays unchanged
        score_neg_inc = verif.calculate_verified_mastery(
            0.50, self.valid_sympy_result, increment=-0.50
        )
        self.assertEqual(score_neg_inc, 0.50)


class TestGradingEquivalenceAdversarial(unittest.TestCase):
    """Stress-test mathematical equivalence comparisons in verify_submission."""

    def test_equivalent_unexpanded_factors(self):
        """Equivalent algebraic expressions with unexpanded factors."""
        res1 = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="(x - 2)*(x + 3)",
            expected_answer="x^2 + x - 6",
        )
        self.assertTrue(res1.is_correct)
        self.assertEqual(res1.symbolic_diff, "0")

        res2 = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="(x - 2)(x + 3)",
            expected_answer="x^2 + x - 6",
        )
        self.assertTrue(res2.is_correct)
        self.assertEqual(res2.symbolic_diff, "0")

    def test_equivalent_fractions_and_latex(self):
        """Fractions written in various forms: slash, LaTeX frac, leading coefficients."""
        forms = [
            ("1/2 * x", "x/2"),
            ("x / 2", "x/2"),
            (r"\frac{1}{2}x", "x/2"),
            (r"\frac{x}{2}", "x/2"),
            ("0.5*x", "x/2"),
        ]
        for s, e in forms:
            with self.subTest(student=s, expected=e):
                res = verif.verify_submission("dif", "derivative", s, e)
                self.assertTrue(res.is_correct)
                self.assertEqual(res.symbolic_diff, "0")

    def test_equivalent_commuted_terms(self):
        """Commuted polynomial terms."""
        res = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="3 - 2x + x^2",
            expected_answer="x^2 - 2x + 3",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")

    def test_non_equivalent_similar_looking_expressions(self):
        """Similar-looking but mathematically distinct expressions must be rejected."""
        # x^2 + 1 vs x^2 - 1
        res1 = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="x^2 + 1",
            expected_answer="x^2 - 1",
        )
        self.assertFalse(res1.is_correct)
        self.assertEqual(res1.error_tag, verif.TAG_SIGN_ERROR)

        # 2x vs 2x + 0.0001
        res2 = verif.verify_submission(
            topic="dif",
            question_type="derivative",
            student_answer="2x",
            expected_answer="2x + 0.0001",
        )
        self.assertFalse(res2.is_correct)
        self.assertEqual(res2.error_tag, verif.TAG_ARITHMETIC)


class TestConstantOfIntegrationAdversarial(unittest.TestCase):
    """Stress-test integration constants (+ C vs + c vs + k, forgotten C)."""

    def test_constant_variants_c_and_k(self):
        """+ C and + c must be accepted; + k must be rejected."""
        # + C
        res_c = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="x^2 + C",
            expected_answer="x^2 + C",
        )
        self.assertTrue(res_c.is_correct)
        self.assertTrue(res_c.constant_of_integration_valid)

        # + c
        res_lower_c = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="x^2 + c",
            expected_answer="x^2 + C",
        )
        self.assertTrue(res_lower_c.is_correct)
        self.assertTrue(res_lower_c.constant_of_integration_valid)

        # + k is rejected
        res_k = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="x^2 + k",
            expected_answer="x^2 + C",
        )
        self.assertFalse(res_k.is_correct)
        self.assertFalse(res_k.constant_of_integration_valid)

    def test_forgotten_c_in_polynomial_trig_kinematics(self):
        """Forgotten constant + C across polynomial, trigonometric, and kinematics integrals."""
        # Polynomial
        res_poly = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="x^2",
            expected_answer="x^2 + C",
        )
        self.assertFalse(res_poly.is_correct)
        self.assertEqual(res_poly.error_tag, verif.TAG_FORGOT_C)
        self.assertFalse(res_poly.constant_of_integration_valid)

        # Trigonometric
        res_trig = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="-cos(x)",
            expected_answer="-cos(x) + C",
        )
        self.assertFalse(res_trig.is_correct)
        self.assertEqual(res_trig.error_tag, verif.TAG_FORGOT_C)
        self.assertFalse(res_trig.constant_of_integration_valid)

        # Kinematics with variable t
        res_kin = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="3*t^2",
            expected_answer="3*t^2 + C",
            context={"var": "t"},
        )
        self.assertFalse(res_kin.is_correct)
        self.assertEqual(res_kin.error_tag, verif.TAG_FORGOT_C)
        self.assertFalse(res_kin.constant_of_integration_valid)

    def test_indefinite_integral_bypass_when_expected_lacks_c(self):
        """REMEDIATED: Missing constant check is strictly enforced even when expected answer omits C."""
        res = verif.verify_submission(
            topic="integ",
            question_type="indefinite_integral",
            student_answer="x^2",
            expected_answer="x^2",
            context={"require_constant": True},
        )
        self.assertFalse(res.is_correct)
        self.assertEqual(res.error_tag, verif.TAG_FORGOT_C)
        self.assertFalse(res.constant_of_integration_valid)


class TestCoordinateOrderingAdversarial(unittest.TestCase):
    """Stress-test coordinate ordering vs unordered roots."""

    def test_vertex_coordinates_rejects_inverted_order(self):
        """When question_type is 'vertex', inverted coordinates (k, h) vs (h, k) are rejected."""
        res = verif.verify_submission(
            topic="quad",
            question_type="vertex",
            student_answer="(2, 1)",
            expected_answer="(1, 2)",
        )
        self.assertFalse(res.is_correct)
        self.assertIn("koordinat", res.feedback.lower())

    def test_coordinate_ordering_bypass_on_synonymous_question_types(self):
        """REMEDIATED: Synonymous question types enforce coordinate ordering; inverted coordinates are rejected."""
        bypassed_types = [
            "titik_pusingan",
            "stationary_point",
            "minimum_point",
            "maximum_point",
            "find_vertex",
            "quadratic",
        ]
        for q_type in bypassed_types:
            with self.subTest(question_type=q_type):
                res = verif.verify_submission(
                    topic="quad",
                    question_type=q_type,
                    student_answer="(2, 1)",
                    expected_answer="(1, 2)",
                )
                self.assertFalse(
                    res.is_correct,
                    f"Inverted coordinates (2, 1) for (1, 2) must be rejected for {q_type}",
                )
                self.assertIn("koordinat", res.feedback.lower())


class TestMultiValueLaTeXAdversarial(unittest.TestCase):
    """Stress-test multi-value (roots and coordinate) parsing with LaTeX."""

    def test_latex_fraction_in_roots_parser_bug(self):
        """REMEDIATED: _parse_multi_values preserves LaTeX fraction braces, matching equivalent roots."""
        res = verif.verify_submission(
            topic="quad",
            question_type="roots",
            student_answer=r"\frac{1}{2}, 3",
            expected_answer=r"\frac{1}{2}, 3",
        )
        self.assertTrue(res.is_correct)
        self.assertEqual(res.symbolic_diff, "0")


if __name__ == "__main__":
    unittest.main()
