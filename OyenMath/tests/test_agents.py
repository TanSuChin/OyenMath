"""Run: python3 -m unittest discover -s tests -p 'test_*.py' (from project root)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import math_tools as mt
from agents.graph import build_graph, run_agent


class FakeLLM:
    def __init__(self, reply): self.reply, self.calls = reply, []
    def run(self, system, user, tools=None, max_steps=4):
        self.calls.append(bool(tools)); return self.reply(user, tools)


class MathTools(unittest.TestCase):
    def test_equivalence(self):
        self.assertTrue(mt.check_equivalence("6x+5", "5+6x")["equivalent"])
        self.assertFalse(mt.check_equivalence("6x^2+5", "6x+5")["equivalent"])
        self.assertTrue(mt.check_equivalence("3x²+5x", "x(3x+5)")["equivalent"])
    def test_calculus(self):
        self.assertEqual(mt.calculus("diff", "3x^2+5x-2")["result"].replace(" ", ""), "6*x+5")
        self.assertIn("+ C", mt.calculus("integrate", "6x^2")["result"])
        self.assertEqual(mt.calculus("definite", "2x", "0", "3")["result"], "9")
    def test_rejects_unsafe_input(self):
        for bad in ["__import__('os')", "open('f')", "x; y", "a" * 200, "exit"]:
            self.assertIn("error", mt.check_equivalence(bad, "x"), bad)


class Graph(unittest.TestCase):
    base = {"topic": "dif", "question": "f(x)=3x^2+5x-2", "student_answer": "6x^2+5", "correct_answer": "6x+5", "level": 2,
            "error_tags": {"exp": 2}, "recent": [{"ok": False}] * 3, "mastery": {"ind": 0.2}, "result_msg": "indeks tidak dikurangkan"}
    def test_rules_only_prerequisite(self):
        out = run_agent(dict(self.base), llm=None)
        self.assertEqual(out["action"], "prerequisite"); self.assertEqual(out["next_topic"], "ind"); self.assertFalse(out["llm"])
    def test_low_confidence_does_not_redirect(self):
        p = dict(self.base, error_tags={"exp": 1}); out = run_agent(p, llm=None)
        self.assertNotEqual(out["action"], "prerequisite")
    def test_advance_when_accurate(self):
        p = dict(self.base, error_tags={}, recent=[{"ok": True}] * 4); self.assertEqual(run_agent(p, llm=None)["action"], "advance")
    def test_practice_message_is_not_praise(self):
        out = run_agent(dict(self.base, error_tags={"x": 1}, recent=[{"ok": False}]), llm=None)
        self.assertEqual(out["action"], "practice"); self.assertNotIn("semakin laju", out["message"])
    def test_llm_nodes_used_and_tools_offered(self):
        llm = FakeLLM(lambda u, t: '{"misconception":"exp","confidence":"tinggi","prerequisite_gap":true,"explanation":"x"}' if t else "Meow, jom!")
        out = run_agent(dict(self.base), llm=llm)
        self.assertTrue(out["llm"]); self.assertEqual(out["message"], "Meow, jom!"); self.assertEqual(llm.calls, [True, False])
        self.assertTrue(any("LLM" in t for t in out["trace"]))
    def test_llm_failure_falls_back(self):
        def boom(u, t): raise RuntimeError("down")
        out = run_agent(dict(self.base), llm=FakeLLM(boom)); self.assertTrue(out["message"]); self.assertIn("action", out)


if __name__ == "__main__":
    unittest.main()
