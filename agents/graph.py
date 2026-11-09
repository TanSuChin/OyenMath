"""
Oyen Math - real LangGraph multi-agent pipeline.
START -> diagnostic (LLM + SymPy tool-calling) -> orchestrator (policy) -> {prerequisite | teaching | challenge} -> END
Without ANTHROPIC_API_KEY every node falls back to deterministic rules, so the graph always runs.
"""
import json
import os
from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .math_tools import TOOL_SPECS, run_tool

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
PERSONA = ("Kamu Oyen, kucing oren gemuk yang comel, ceria dan menyokong, rakan belajar pelajar SPM Matematik Tambahan Malaysia. "
           "Bercakap Bahasa Melayu mudah (atau English jika diminta), sedikit lawak, tidak pernah mengejek kesilapan. Jangan reka fakta matematik: "
           "gunakan alat untuk mengesahkan.")


class AgentState(TypedDict, total=False):
    payload: Dict[str, Any]
    diagnosis: Dict[str, Any]
    action: str
    message: str
    next_topic: Optional[str]
    trace: List[str]


# ---------- LLM client (injectable for tests) ----------
class ClaudeClient:
    def __init__(self):
        import anthropic
        self.c = anthropic.Anthropic()

    def run(self, system: str, user: str, tools: Optional[list] = None, max_steps: int = 4) -> str:
        msgs = [{"role": "user", "content": user}]
        for _ in range(max_steps):
            r = self.c.messages.create(model=MODEL, max_tokens=700, system=system, messages=msgs, **({"tools": tools} if tools else {}))
            if r.stop_reason != "tool_use":
                return "".join(b.text for b in r.content if b.type == "text")
            msgs.append({"role": "assistant", "content": r.content})
            msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(run_tool(b.name, b.input))}
                for b in r.content if b.type == "tool_use"]})
        return ""


def default_client():
    return ClaudeClient() if os.environ.get("ANTHROPIC_API_KEY") else None


def _json(text: str) -> Optional[dict]:
    a, z = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[a:z + 1]) if a >= 0 else None
    except Exception:
        return None


def build_graph(llm=None):
    """llm: object with .run(system,user,tools,max_steps)->str, or None for rule-only mode."""

    def diagnostic(s: AgentState) -> AgentState:
        p, tr = s["payload"], list(s.get("trace", []))
        tags = p.get("error_tags", {})
        top = max(tags, key=tags.get) if tags else None
        diag = {"misconception": top, "confidence": "tinggi" if tags.get(top, 0) >= 2 else "rendah" if top else "-", "prerequisite_gap": False, "explanation": p.get("result_msg", "")}
        if llm:
            prompt = (f"Soalan: {p.get('question')}\nJawapan pelajar: {p.get('student_answer')}\nJawapan betul: {p.get('correct_answer')}\n"
                      f"Topik: {p.get('topic')} tahap {p.get('level')}. Corak ralat sejarah: {tags}. Ralat sistem: {p.get('result_msg')}\n"
                      "Guna alat (check_equivalence/calculus/get_syllabus) untuk mengesahkan, kemudian balas JSON SAHAJA: "
                      '{"misconception":str,"confidence":"rendah|sederhana|tinggi","prerequisite_gap":bool,"explanation":str}. '
                      "Jangan simpulkan salah faham daripada satu jawapan sahaja; nyatakan keyakinan rendah jika bukti sedikit.")
            try:
                d = _json(llm.run(PERSONA, prompt, TOOL_SPECS))
                if d:
                    diag.update({k: d[k] for k in ("misconception", "confidence", "prerequisite_gap", "explanation") if k in d})
                    tr.append("Diagnostic Agent (LLM + SymPy): " + str(diag.get("misconception")))
                else:
                    tr.append("Diagnostic Agent: LLM tidak memulangkan JSON, guna peraturan.")
            except Exception as e:
                tr.append(f"Diagnostic Agent: LLM gagal ({type(e).__name__}), guna peraturan.")
        else:
            tr.append("Diagnostic Agent (peraturan): " + str(top))
        return {"diagnosis": diag, "trace": tr}

    def orchestrator(s: AgentState) -> AgentState:
        p, d, tr = s["payload"], s["diagnosis"], list(s["trace"])
        m = p.get("mastery", {})
        recent = p.get("recent", [])[-5:]
        acc = sum(1 for r in recent if r.get("ok")) / len(recent) if recent else 0
        topic = p.get("topic")
        if topic in ("dif", "integ") and (d.get("prerequisite_gap") or d.get("misconception") in ("exp", "coef", "mul", "add", "div")) \
                and m.get("ind", 0) < 0.6 and d.get("confidence") != "rendah":
            action, nxt = "prerequisite", "ind"
        elif acc >= 0.8 and len(recent) >= 3:
            action, nxt = "advance", None
        elif d.get("confidence") == "rendah" and d.get("misconception"):
            action, nxt = "practice", None
        else:
            action, nxt = "teach", None
        tr.append(f"Orchestrator: ketepatan terkini {acc:.0%} -> tindakan '{action}'" + (f" ({nxt})" if nxt else ""))
        return {"action": action, "next_topic": nxt, "trace": tr}

    def route(s: AgentState) -> str:
        return {"prerequisite": "prerequisite", "teach": "teaching"}.get(s["action"], "challenge")

    def _say(s: AgentState, role: str, fallback: str) -> AgentState:
        tr = list(s["trace"])
        msg = fallback
        if llm:
            try:
                out = llm.run(PERSONA, f"Diagnosis: {json.dumps(s['diagnosis'], ensure_ascii=False)}\nSoalan: {s['payload'].get('question')}\n"
                              f"Tugas ({role}): tulis mesej Oyen 2-4 ayat kepada pelajar. Jika perlu, beri satu petunjuk (bukan jawapan penuh).", None, 1)
                msg = out.strip() or fallback
                tr.append(f"{role} (LLM): mesej dijana")
            except Exception as e:
                tr.append(f"{role}: LLM gagal ({type(e).__name__}), guna templat")
        else:
            tr.append(f"{role} (templat)")
        return {"message": msg, "trace": tr}

    def prerequisite(s):
        return _say(s, "Teaching Agent", "Oyen perasan kesilapan ini berpunca daripada asas indeks. Jom ulang kaji Hukum Indeks dahulu, lepas tu kita sambung! 🐱")

    def teaching(s):
        d = s["diagnosis"]
        return _say(s, "Teaching Agent", f"Hampir! {d.get('explanation') or 'Semak semula langkah kamu.'} Cuba kaedah penerangan lain bersama Oyen. 🐾")

    def challenge(s):
        if s["action"] == "advance":
            fb = "Kamu semakin laju! Oyen sediakan soalan yang lebih mencabar. LOCK IN! 🐈"
        else:
            fb = "Satu kesilapan belum cukup untuk Oyen buat kesimpulan. Jom cuba beberapa soalan lagi pada tahap ini dan kita lihat coraknya. 🐾"
        return _say(s, "Challenge Agent", fb)

    g = StateGraph(AgentState)
    for name, fn in [("diagnostic", diagnostic), ("orchestrator", orchestrator), ("prerequisite", prerequisite), ("teaching", teaching), ("challenge", challenge)]:
        g.add_node(name, fn)
    g.add_edge(START, "diagnostic")
    g.add_edge("diagnostic", "orchestrator")
    g.add_conditional_edges("orchestrator", route, {"prerequisite": "prerequisite", "teaching": "teaching", "challenge": "challenge"})
    for n in ("prerequisite", "teaching", "challenge"):
        g.add_edge(n, END)
    return g.compile()


_GRAPH = None


def run_agent(payload: dict, llm="auto") -> dict:
    global _GRAPH
    client = default_client() if llm == "auto" else llm
    graph = build_graph(client) if (llm != "auto" or _GRAPH is None) else _GRAPH
    if llm == "auto":
        _GRAPH = graph
    out = graph.invoke({"payload": payload, "trace": []})
    return {"diagnosis": out["diagnosis"], "action": out["action"], "next_topic": out.get("next_topic"),
            "message": out["message"], "trace": out["trace"], "llm": bool(client)}
