"""Empirical Adversarial Stress Harness for Milestone M2 Math Tools & Schemas.

Empirical Challenger 1 Test Suite testing:
1. SPM Variable Desynchronization (Greek theta θ in var, Greek pi π)
2. Differential Token Whitelist & Unconventional Casing (dt, uppercase X)
3. Injection / RCE Protection Verification
4. Pydantic Schema Bypass & Bounds Validation
5. Sandbox Timeout & Thread Pool Worker Saturation Behavior
"""

import math
import time
import unittest
from pydantic import ValidationError

from agents import math_tools as mt
from agents import schemas


class TestSPMVariableDesynchronization(unittest.TestCase):
    """Empirically test SPM variables: Greek theta, Greek pi, and unconventional tokens."""

    def test_unicode_theta_variable_in_calculus_diff(self):
        """REMEDIATED: Differentiating sin(θ) with var='θ' evaluates cleanly to cos(theta)."""
        res = mt.calculus("diff", "sin(θ)", var="θ")
        self.assertEqual(res.get("result"), "cos(theta)")

    def test_unicode_theta_variable_in_calculus_integrate(self):
        """REMEDIATED: Integrating θ with var='θ' evaluates cleanly to theta**2/2 + C."""
        res = mt.calculus("integrate", "θ", var="θ")
        self.assertEqual(res.get("result"), "theta**2/2 + C")

    def test_unicode_theta_variable_in_quadratic_analysis(self):
        """REMEDIATED: quadratic_analysis('θ^2 - 4*θ + 4', var='θ') analyzes quadratic in theta."""
        res = mt.quadratic_analysis("θ^2 - 4*θ + 4", var="θ")
        self.assertTrue(res.get("is_quadratic"))
        self.assertEqual(res.get("roots"), ["2"])
        self.assertEqual(res.get("discriminant"), "0")

    def test_unicode_theta_variable_in_stationary_points(self):
        """REMEDIATED: stationary_points with var='θ' yields 2 points and derivative 3*theta**2 - 3."""
        res = mt.stationary_points("θ^3 - 3*θ", var="θ")
        self.assertEqual(res.get("count"), 2)
        self.assertEqual(res.get("first_derivative"), "3*theta**2 - 3")

    def test_unicode_theta_variable_in_tangent(self):
        """REMEDIATED: tangent('θ^2', at_x=1, var='θ') evaluates to gradient 2, line equation."""
        res = mt.tangent("θ^2", at_x=1, var="θ")
        self.assertEqual(res.get("gradient"), "2")
        self.assertEqual(res.get("equation"), "y = 2*theta - 1")

    def test_greek_pi_acceptance_in_parse(self):
        """REMEDIATED: Greek pi 'π' is converted to 'pi' and parses safely."""
        expr = mt.parse("2*π*r")
        self.assertEqual(str(expr), "2*pi*r")

    def test_greek_pi_acceptance_in_check_equivalence(self):
        """REMEDIATED: check_equivalence accepts standard SPM expression '2*π*r'."""
        res = mt.check_equivalence("2*π*r", "2*pi*r")
        self.assertTrue(res.get("equivalent"))
        self.assertEqual(res.get("difference"), "0")

    def test_rates_of_change_dt_token_accepted(self):
        """REMEDIATED: 'dt', 'dh', 'dr', 'dA', 'dV', 'ds' are allowed differential tokens."""
        expr = mt.parse("dt")
        self.assertEqual(str(expr), "dt")
        for tok in ("dh", "dr", "dA", "dV", "ds"):
            p = mt.parse(tok)
            self.assertEqual(str(p), tok)

    def test_uppercase_variable_casing_accepted(self):
        """REMEDIATED: Uppercase variables 'X', 'Y', 'T' are safely normalized to lowercase."""
        expr_x = mt.parse("2*X + 1")
        self.assertEqual(str(expr_x), "2*x + 1")
        expr_y = mt.parse("Y^2 - 4")
        self.assertEqual(str(expr_y), "y**2 - 4")
        expr_t = mt.parse("T + 1")
        self.assertEqual(str(expr_t), "t + 1")


class TestInjectionAndRCEResilience(unittest.TestCase):
    """Empirically verify that injection, dunder access, and arbitrary code execution fail."""

    def test_dunder_import_rejected(self):
        with self.assertRaises(ValueError):
            mt.parse("__import__('os').system('calc')")

    def test_dunder_class_rejected(self):
        with self.assertRaises(ValueError):
            mt.parse("x.__class__")

    def test_eval_call_rejected(self):
        with self.assertRaises(ValueError):
            mt.parse("eval(x)")

    def test_exec_call_rejected(self):
        with self.assertRaises(ValueError):
            mt.parse("exec(x)")

    def test_system_call_in_definite_bounds_rejected(self):
        """Definite integral bounds reject code injection (RCE fix confirmed)."""
        res = mt.calculus("definite", "x", lower="__import__('os')", upper=1)
        self.assertEqual(res.get("error"), "ungkapan tidak sah")

    def test_deeply_nested_parentheses_bounded(self):
        """Deeply nested parentheses within 150 chars parse safely without recursion crash."""
        expr = "(" * 50 + "x" + ")" * 50
        res = mt.parse(expr)
        self.assertEqual(str(res), "x")

    def test_unbalanced_parentheses_gracefully_handled(self):
        res = mt.check_equivalence("(" * 40 + "x", "x")
        self.assertFalse(res.get("equivalent"))
        self.assertIn("error", res)

    def test_division_by_zero_in_check_equivalence(self):
        res = mt.check_equivalence("1/0", "1/0")
        self.assertFalse(res.get("equivalent"))
        self.assertEqual(res.get("difference"), "nan")

    def test_division_by_zero_in_tangent(self):
        res = mt.tangent("1/x", at_x=0)
        self.assertEqual(res.get("gradient"), "zoo")


class TestPydanticSchemaBypass(unittest.TestCase):
    """Empirically test Pydantic schema validation boundaries and edge cases."""

    def test_extra_unknown_fields_strictly_forbidden(self):
        is_valid, _, err = schemas.validate_tool_input(
            "check_equivalence",
            {"a": "x", "b": "x", "malicious_field": "__import__"},
        )
        self.assertFalse(is_valid)
        self.assertTrue("Extra inputs are not permitted" in err or "malicious_field" in err)

    def test_payload_exceeding_150_chars_rejected(self):
        long_expr = "x + " * 50 + "1"  # 201 chars
        is_valid, _, err = schemas.validate_tool_input(
            "check_equivalence",
            {"a": long_expr, "b": "x"},
        )
        self.assertFalse(is_valid)
        self.assertIn("String should have at most 150 characters", err)

    def test_empty_string_rejected(self):
        is_valid, _, err = schemas.validate_tool_input(
            "check_equivalence",
            {"a": "", "b": "x"},
        )
        self.assertFalse(is_valid)

    def test_nan_float_in_calculus_bounds_handled(self):
        res = schemas.run_validated_tool(
            "calculus",
            {"op": "definite", "expr": "x^2", "lower": float("nan"), "upper": 1.0},
        )
        self.assertTrue(res.get("validation_error"))
        self.assertIn("error", res)

    def test_nan_float_in_tangent_normal_produces_nan(self):
        """REMEDIATED: NaN float in at_x is rejected by schema validator."""
        res = schemas.run_validated_tool(
            "tangent_normal",
            {"expr": "x^2", "at_x": float("nan")},
        )
        self.assertTrue(res.get("validation_error"))
        self.assertIn("at_x", res.get("error", ""))

    def test_calculus_definite_missing_bounds_rejected(self):
        is_valid, _, err = schemas.validate_tool_input(
            "calculus",
            {"op": "definite", "expr": "x^2"},
        )
        self.assertFalse(is_valid)
        self.assertIn("Kedua-dua 'lower' dan 'upper' diperlukan", err)

    def test_calculus_tangent_missing_at_x_rejected(self):
        is_valid, _, err = schemas.validate_tool_input(
            "calculus",
            {"op": "tangent", "expr": "x^2"},
        )
        self.assertFalse(is_valid)
        self.assertIn("Nilai 'at_x' diperlukan", err)


class TestTimeoutSandboxBehavior(unittest.TestCase):
    """Empirically test execution timeout sandbox handling."""

    def test_clean_timeout_error_returned(self):
        """Confirm that operations exceeding timeout return a structured timeout error dict."""
        def slow_fn():
            time.sleep(1.0)
            return "done"

        with self.assertRaises(TimeoutError):
            mt.run_with_timeout(slow_fn, timeout=0.1)

    def test_check_equivalence_timeout_envelope(self):
        def slow_check(a, b, require_constant=False):
            time.sleep(1.0)
            return {"equivalent": True}

        # Monkey-patch internal function to simulate slow SymPy execution
        orig_fn = mt._check_equivalence_internal
        try:
            mt._check_equivalence_internal = slow_check
            res = mt.check_equivalence("x", "x", timeout=0.1)
            self.assertTrue(res.get("timeout"))
            self.assertFalse(res.get("equivalent"))
            self.assertIn("Operasi matematik melebihi had masa", res.get("error", ""))
        finally:
            mt._check_equivalence_internal = orig_fn


if __name__ == "__main__":
    unittest.main()
