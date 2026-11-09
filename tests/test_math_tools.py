"""OyenMath Autonomous AI Learning Platform - Math Tools Test Suite.

Milestone M2: Verification tests for:
1. Security RCE prevention (sp.sympify elimination, malicious input rejection)
2. SPM variable whitelist (t, u, v, r, h, k, m, n, theta, radicals √)
3. Constant of integration (+ C) enforcement and forgot_c tagging
4. Expanded operations (second_derivative, tangent, normal, stationary_points, quadratic_analysis)
5. 5-second timeout execution sandbox via concurrent.futures.ThreadPoolExecutor
6. Strict Pydantic v2 schemas, input validation, and structured invocation logging
7. 100% backward compatibility with legacy callers (run_tool, TOOL_SPECS, get_syllabus)
"""

from __future__ import annotations

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import math_tools as mt
from agents import schemas as sc


class TestSecurityRCEPrevention(unittest.TestCase):
    """Verify that remote code execution vulnerabilities are strictly eliminated."""

    def test_definite_integral_rce_in_lower_bound_rejected(self):
        """Proof-of-exploit test: lower bound with __import__('os') must not execute."""
        exploit = "__import__('os').system('echo VULNERABLE_TEST')"
        res = mt.calculus("definite", "x", lower=exploit, upper="1")
        self.assertIn("error", res)
        self.assertNotIn("result", res)

    def test_definite_integral_rce_in_upper_bound_rejected(self):
        """Proof-of-exploit test: upper bound with malicious payload must not execute."""
        exploit = "__import__('subprocess').call(['calc.exe'])"
        res = mt.calculus("definite", "x", lower="0", upper=exploit)
        self.assertIn("error", res)
        self.assertNotIn("result", res)

    def test_malicious_expressions_rejected(self):
        """All common Python execution escape vectors must fail safely."""
        malicious_inputs = [
            "__import__('os')",
            "open('/etc/passwd')",
            "open('test.txt', 'w')",
            "eval('2+2')",
            "exec('import sys')",
            "__builtins__",
            "x; os.system('dir')",
            "exit()",
            "quit()",
            "getattr(sp, 'core')",
            "__class__.__bases__",
        ]
        for bad in malicious_inputs:
            with self.subTest(bad=bad):
                # Test in parse()
                with self.assertRaises(ValueError):
                    mt.parse(bad)
                # Test in check_equivalence()
                res = mt.check_equivalence(bad, "x")
                self.assertIn("error", res, f"Expected error for {bad}")
                self.assertFalse(res.get("equivalent", False))

    def test_oversized_string_rejected(self):
        """Expressions exceeding 150 characters must be rejected to prevent ReDoS/DoS."""
        long_expr = "x" + "+x" * 100  # > 150 characters
        with self.assertRaises(ValueError):
            mt.parse(long_expr)
        res = mt.check_equivalence(long_expr, "x")
        self.assertIn("error", res)

    def test_unauthorized_token_names_rejected(self):
        """Tokens outside _ALLOWED_NAMES and single-letter set must be rejected."""
        for invalid in ["foo", "func", "system", "lambda", "def", "import", "class", "bad"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    mt.parse(f"{invalid}(x)")


class TestSPMVariableWhitelist(unittest.TestCase):
    """Verify that all standard SPM Additional Mathematics variables and notations parse correctly."""

    def test_kinematics_variable_t(self):
        """Test kinematics variable t (time) in expressions and differentiation."""
        p = mt.parse("3t^2 + 5t - 2")
        self.assertEqual(str(p), "3*t**2 + 5*t - 2")
        diff_res = mt.calculus("diff", "3t^2 + 5t - 2", var="t")
        self.assertEqual(diff_res.get("result", "").replace(" ", ""), "6*t+5")

    def test_geometry_variables_r_and_h(self):
        """Test cylinder volume / geometry variables r (radius) and h (height)."""
        p = mt.parse("pi * r^2 * h")
        self.assertIn("pi*h*r**2", str(p).replace(" ", ""))

    def test_chain_rule_variables_u_and_v(self):
        """Test product/quotient/chain rule variables u and v."""
        p = mt.parse("2uv")
        self.assertEqual(str(p), "2*u*v")
        eq = mt.check_equivalence("u * v + v * u", "2uv")
        self.assertTrue(eq.get("equivalent"))

    def test_angle_theta(self):
        """Test angle notation θ and theta."""
        p1 = mt.parse("sin(θ)")
        p2 = mt.parse("sin(theta)")
        self.assertEqual(str(p1), str(p2))
        eq = mt.check_equivalence("sin(θ)^2 + cos(θ)^2", "1")
        self.assertTrue(eq.get("equivalent"))

    def test_radical_notation(self):
        """Test radical symbol √ normalisation to sqrt."""
        p_unicode = mt.parse("2√x")
        p_standard = mt.parse("2*sqrt(x)")
        self.assertEqual(str(p_unicode), str(p_standard))

        p_grouped = mt.parse("√(x + 1)")
        self.assertEqual(str(p_grouped), "sqrt(x + 1)")

        p_latex = mt.parse(r"\sqrt{x + 4}")
        self.assertEqual(str(p_latex), "sqrt(x + 4)")

        eq = mt.check_equivalence("√x * √x", "x")
        self.assertTrue(eq.get("equivalent"))

    def test_constants_k_m_n_a_b(self):
        """Test algebraic constants k, m, n, a, b."""
        for c in ("k", "m", "n", "a", "b"):
            with self.subTest(c=c):
                p = mt.parse(f"{c} * x^2")
                self.assertIn(c, str(p))


class TestConstantOfIntegration(unittest.TestCase):
    """Verify explicit constant of integration (+ C) checking and forgot_c tagging."""

    def test_indefinite_integral_includes_c(self):
        """Integration tool must output '+ C'."""
        res = mt.calculus("integrate", "6x^2")
        self.assertIn("+ C", res.get("result", ""))

    def test_missing_c_tagged_forgot_c_by_default(self):
        """When expected answer has + C and student omitted it, return tag='forgot_c'."""
        res = mt.check_equivalence("3x", "3x + C")
        self.assertFalse(res.get("equivalent"))
        self.assertEqual(res.get("tag"), "forgot_c")
        self.assertEqual(res.get("difference"), "-C")

    def test_require_constant_true_enforces_c(self):
        """require_constant=True must flag missing C even if core algebra is identical."""
        res = mt.check_equivalence("2x^3", "2x^3 + C", require_constant=True)
        self.assertFalse(res.get("equivalent"))
        self.assertEqual(res.get("tag"), "forgot_c")

    def test_both_including_c_is_equivalent(self):
        """Both student and expected having + C must evaluate as equivalent."""
        res = mt.check_equivalence("2x^3 + C", "C + 2x^3", require_constant=True)
        self.assertTrue(res.get("equivalent"))
        self.assertEqual(res.get("difference"), "0")

    def test_lowercase_c_accepted(self):
        """Lowercase + c is normalized to + C."""
        res = mt.check_equivalence("2x^3 + c", "2x^3 + C", require_constant=True)
        self.assertTrue(res.get("equivalent"))


class TestExpandedCalculusOperations(unittest.TestCase):
    """Verify tangent, normal, stationary_points, second_derivative, and quadratic_analysis."""

    def test_second_derivative(self):
        """Test f''(x) calculation."""
        res = mt.second_derivative("3x^3 - 5x^2 + 4x - 1")
        self.assertIn(res.get("result", "").replace(" ", ""), ("18*x-10", "2*(9*x-5)"))
        self.assertIn("first_derivative", res)

    def test_tangent_line(self):
        """Tangent line to y = 3x^2 + 5x - 2 at x = 1: y = 11x - 5."""
        res = mt.tangent("3x^2 + 5x - 2", at_x=1)
        self.assertEqual(res.get("gradient"), "11")
        self.assertEqual(res.get("point"), "(1, 6)")
        self.assertIn("11*x - 5", res.get("equation", ""))

    def test_normal_line(self):
        """Normal line to y = 3x^2 + 5x - 2 at x = 1: gradient = -1/11."""
        res = mt.normal("3x^2 + 5x - 2", at_x=1)
        self.assertEqual(res.get("gradient"), "-1/11")
        self.assertEqual(res.get("tangent_gradient"), "11")

    def test_normal_line_horizontal_tangent(self):
        """Normal to y = x^2 at x = 0 (horizontal tangent) is vertical line x = 0."""
        res = mt.normal("x^2", at_x=0)
        self.assertEqual(res.get("gradient"), "undefined")
        self.assertEqual(res.get("equation"), "x = 0")

    def test_stationary_points(self):
        """Find turning points of y = 2x^3 - 3x^2 - 12x + 5: (-1, 12) max, (2, -15) min."""
        res = mt.stationary_points("2x^3 - 3x^2 - 12x + 5")
        self.assertEqual(res.get("count"), 2)
        pts = {p["x"]: p for p in res.get("points", [])}
        self.assertIn("-1", pts)
        self.assertIn("2", pts)
        self.assertEqual(pts["-1"]["nature"], "maximum")
        self.assertEqual(pts["-1"]["y"], "12")
        self.assertEqual(pts["2"]["nature"], "minimum")
        self.assertEqual(pts["2"]["y"], "-15")

    def test_quadratic_analysis_two_real_roots(self):
        """Quadratic 2x^2 - 4x - 6: disc = 64, roots = [-1, 3], vertex = (1, -8)."""
        res = mt.quadratic_analysis("2x^2 - 4x - 6")
        self.assertTrue(res.get("is_quadratic"))
        self.assertEqual(res.get("discriminant"), "64")
        self.assertEqual(set(res.get("roots", [])), {"-1", "3"})
        self.assertEqual(res.get("nature_of_roots"), "two_real_distinct")
        self.assertEqual(res.get("vertex"), "(1, -8)")
        self.assertEqual(res.get("axis_of_symmetry"), "x = 1")
        self.assertEqual(res.get("optimum_type"), "minimum")

    def test_quadratic_analysis_equal_roots(self):
        """Quadratic x^2 - 6x + 9: disc = 0, nature = two_equal_roots."""
        res = mt.quadratic_analysis("x^2 - 6x + 9")
        self.assertEqual(res.get("discriminant"), "0")
        self.assertEqual(res.get("nature_of_roots"), "two_equal_roots")
        self.assertEqual(res.get("roots"), ["3"])

    def test_quadratic_analysis_no_real_roots(self):
        """Quadratic x^2 + 2x + 5: disc = -16, nature = no_real_roots."""
        res = mt.quadratic_analysis("x^2 + 2x + 5")
        self.assertEqual(res.get("discriminant"), "-16")
        self.assertEqual(res.get("nature_of_roots"), "no_real_roots")

    def test_quadratic_analysis_non_quadratic_rejected(self):
        """Expression with degree != 2 must return error."""
        res = mt.quadratic_analysis("x^3 - 2x + 1")
        self.assertIn("error", res)
        self.assertFalse(res.get("is_quadratic", True))


class TestExecutionTimeoutSandbox(unittest.TestCase):
    """Verify that 5-second timeout execution sandbox protects against hangs."""

    def test_run_with_timeout_normal_execution(self):
        """Normal mathematical functions execute within timeout limit."""
        res = mt.run_with_timeout(lambda a, b: a + b, 10, 20, timeout=1.0)
        self.assertEqual(res, 30)

    def test_run_with_timeout_aborts_on_exceeded_time(self):
        """Slow or pathological execution is cleanly aborted with TimeoutError."""
        def slow_func():
            time.sleep(0.3)
            return "done"

        with self.assertRaises(TimeoutError):
            mt.run_with_timeout(slow_func, timeout=0.05)

    def test_check_equivalence_handles_timeout_gracefully(self):
        """check_equivalence returns structured timeout error dictionary on timeout."""
        res = mt.check_equivalence("x^2", "x^2", timeout=0.00001)
        # On ultra-short timeout, it should either return result or clean timeout error
        if "error" in res:
            self.assertTrue(res.get("timeout"))
            self.assertFalse(res.get("equivalent"))


class TestSchemasAndValidation(unittest.TestCase):
    """Verify Pydantic v2 schemas, input validation, and structured logging."""

    def setUp(self):
        sc.clear_tool_logs()

    def test_check_equivalence_schema_valid(self):
        is_valid, model, err = sc.validate_tool_input("check_equivalence", {"a": "6x+5", "b": "5+6x"})
        self.assertTrue(is_valid)
        self.assertIsNotNone(model)
        self.assertIsNone(err)

    def test_check_equivalence_schema_missing_fields_rejected(self):
        is_valid, model, err = sc.validate_tool_input("check_equivalence", {"a": "6x+5"})
        self.assertFalse(is_valid)
        self.assertIn("Pengesahan parameter gagal", err)

    def test_calculus_schema_definite_missing_bounds_rejected(self):
        is_valid, model, err = sc.validate_tool_input("calculus", {"op": "definite", "expr": "2x"})
        self.assertFalse(is_valid)
        self.assertIn("Kedua-dua 'lower' dan 'upper' diperlukan", err)

    def test_calculus_schema_tangent_missing_at_x_rejected(self):
        is_valid, model, err = sc.validate_tool_input("calculus", {"op": "tangent", "expr": "x^2"})
        self.assertFalse(is_valid)
        self.assertIn("Nilai 'at_x' diperlukan", err)

    def test_extra_forbidden_fields_rejected(self):
        """Prevent parameter injection by rejecting unexpected arguments."""
        is_valid, model, err = sc.validate_tool_input(
            "check_equivalence", {"a": "x", "b": "x", "malicious_injected_param": True}
        )
        self.assertFalse(is_valid)

    def test_run_validated_tool_and_logging(self):
        """Verify validated tool execution, latency measurement, and audit log."""
        res = sc.run_validated_tool(
            "check_equivalence",
            {"a": "3x²+5x", "b": "x(3x+5)"},
            caller="unit_test_worker",
        )
        self.assertTrue(res.get("equivalent"))

        logs = sc.get_tool_invocation_logs()
        self.assertGreaterEqual(len(logs), 1)
        last_log = logs[-1]
        self.assertEqual(last_log["tool_name"], "check_equivalence")
        self.assertEqual(last_log["caller"], "unit_test_worker")
        self.assertTrue(last_log["success"])
        self.assertGreater(last_log["duration_ms"], 0.0)
        self.assertIn("timestamp", last_log)


class TestBackwardCompatibility(unittest.TestCase):
    """Verify 100% backward compatibility for all legacy callers and specifications."""

    def test_legacy_math_tools_suite(self):
        """Preserve exact test cases from test_agents.py:MathTools."""
        self.assertTrue(mt.check_equivalence("6x+5", "5+6x")["equivalent"])
        self.assertFalse(mt.check_equivalence("6x^2+5", "6x+5")["equivalent"])
        self.assertTrue(mt.check_equivalence("3x²+5x", "x(3x+5)")["equivalent"])
        self.assertEqual(mt.calculus("diff", "3x^2+5x-2")["result"].replace(" ", ""), "6*x+5")
        self.assertIn("+ C", mt.calculus("integrate", "6x^2")["result"])
        self.assertEqual(mt.calculus("definite", "2x", "0", "3")["result"], "9")
        for bad in ["__import__('os')", "open('f')", "x; y", "a" * 200, "exit"]:
            self.assertIn("error", mt.check_equivalence(bad, "x"), bad)

    def test_get_syllabus_all_topics(self):
        for topic in ("ind", "quad", "dif", "integ"):
            res = mt.get_syllabus(topic)
            self.assertIn("notes", res)
            self.assertNotEqual(res["notes"], "tiada nota")

    def test_run_tool_dispatcher_compatibility(self):
        res1 = mt.run_tool("check_equivalence", {"a": "2x", "b": "2*x"})
        self.assertTrue(res1.get("equivalent"))
        res2 = mt.run_tool("calculus", {"op": "diff", "expr": "x^3"})
        self.assertIn("3*x**2", res2.get("result", ""))
        res3 = mt.run_tool("get_syllabus", {"topic": "dif"})
        self.assertIn("Petua kuasa", res3.get("notes", ""))
        res4 = mt.run_tool("non_existent_tool", {})
        self.assertIn("error", res4)

    def test_tool_specs_structure(self):
        names = {t["name"] for t in mt.TOOL_SPECS}
        self.assertIn("check_equivalence", names)
        self.assertIn("calculus", names)
        self.assertIn("get_syllabus", names)
        for spec in mt.TOOL_SPECS:
            self.assertIn("name", spec)
            self.assertIn("description", spec)
            self.assertIn("input_schema", spec)
            self.assertEqual(spec["input_schema"]["type"], "object")


if __name__ == "__main__":
    unittest.main()
