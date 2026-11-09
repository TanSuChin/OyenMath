"""
Oyen Math - real LangGraph multi-agent pipeline.
START -> diagnostic (LLM + SymPy tool-calling) -> orchestrator (policy) -> {prerequisite | teaching | challenge} -> END
Without ANTHROPIC_API_KEY every node falls back to deterministic rules, so the graph always runs.
"""
import json
import os
import urllib.request
from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .math_tools import TOOL_SPECS, run_tool

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
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


# ---------- LLM clients (Anthropic Claude & Groq OpenAI-compatible, injectable for tests) ----------
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


class GroqClient:
    """Zero-dependency Groq API client with OpenAI-compatible tool-calling support."""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key.strip()
        self.model = model or os.environ.get("GROQ_MODEL", GROQ_MODEL)

    @staticmethod
    def _to_openai_tools(tools: Optional[list]) -> list:
        if not tools:
            return []
        out = []
        for t in tools:
            out.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
        return out

    def run(self, system: str, user: str, tools: Optional[list] = None, max_steps: int = 4) -> str:
        msgs: List[Dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        oai_tools = self._to_openai_tools(tools)

        for _ in range(max_steps):
            body: Dict[str, Any] = {
                "model": self.model,
                "messages": msgs,
                "max_tokens": 700,
                "temperature": 0.3,
            }
            if oai_tools:
                body["tools"] = oai_tools
                body["tool_choice"] = "auto"

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "OyenMath-Agent/4.0",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return str(msg.get("content") or "")

            msgs.append(msg)
            for tc in tool_calls:
                fn = tc.get("function") or {}
                fn_name = fn.get("name", "")
                try:
                    fn_args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    fn_args = {}
                result = run_tool(fn_name, fn_args if isinstance(fn_args, dict) else {})
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", "call_1"),
                    "name": fn_name,
                    "content": json.dumps(result),
                })
        return ""


def _reload_env_keys() -> None:
    """Dynamically read GROQ_API_KEY / ANTHROPIC_API_KEY from .env if not already set in os.environ."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (os.path.join(here, ".env"), os.path.join(os.path.dirname(here), ".env")):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            k, v = line.strip().split("=", 1)
                            k = k.strip()
                            val = v.strip().strip('"').strip("'")
                            if k in ("GROQ_API_KEY", "GROQ_MODEL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
                                if val and not val.startswith("your-"):
                                    os.environ[k] = val
            except Exception:
                pass


def default_client():
    _reload_env_keys()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    anth_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if groq_key and not groq_key.startswith("your-"):
        return GroqClient(groq_key)
    if anth_key.startswith("gsk_"):
        # User pasted a Groq gsk_... key into ANTHROPIC_API_KEY
        return GroqClient(anth_key)
    if anth_key and not anth_key.startswith("your-"):
        return ClaudeClient()
    return None


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


# =====================================================================
# Milestone M3: Stateful 12-Node Autonomous Mission Graph
# =====================================================================

def build_autonomous_mission_graph(checkpointer=None, llm=None):
    """
    Construct and compile the stateful 12-Node Autonomous LangGraph workflow.

    Workflow topology:
    START -> goal_understanding -> profile_retrieval -> diagnostic -> learning_plan -> orchestrator
          -> {teaching | challenge | prerequisite} -> student_interaction (LangGraph interrupt)
          -> evaluation -> solver_verification (SymPy gate) -> state_updater -> progress_evaluator
          -> {replan -> learning_plan | continue -> orchestrator | wait -> student_interaction | complete/terminate -> END}

    Args:
        checkpointer: Persistent checkpoint saver (e.g. OyenLangGraphCheckpointer)
        llm: Optional LLM client with .run() method

    Returns:
        CompiledStateGraph ready for invoke() and Command(resume=...)
    """
    from .nodes import (
        goal_understanding_node,
        profile_retrieval_node,
        diagnostic_node,
        learning_plan_node,
        orchestrator_node,
        route_orchestrator,
        teaching_node,
        challenge_node,
        prerequisite_node,
        student_interaction_node,
        evaluation_node,
        solver_verification_node,
        state_updater_node,
        progress_evaluator_node,
        route_progress_evaluation,
    )
    from .state import MissionState

    builder = StateGraph(MissionState)

    # 1. Register all 13 specialized agent nodes
    if llm is not None:
        builder.add_node("goal_understanding", goal_understanding_node)
        builder.add_node("profile_retrieval", profile_retrieval_node)
        builder.add_node("diagnostic", lambda s: diagnostic_node(s, llm=llm))
        builder.add_node("learning_plan", learning_plan_node)
        builder.add_node("orchestrator", orchestrator_node)
        builder.add_node("teaching", lambda s: teaching_node(s, llm=llm))
        builder.add_node("challenge", lambda s: challenge_node(s, llm=llm))
        builder.add_node("prerequisite", lambda s: prerequisite_node(s, llm=llm))
        builder.add_node("student_interaction", student_interaction_node)
        builder.add_node("evaluation", lambda s: evaluation_node(s, llm=llm))
        builder.add_node("solver_verification", solver_verification_node)
        builder.add_node("state_updater", state_updater_node)
        builder.add_node("progress_evaluator", progress_evaluator_node)
    else:
        builder.add_node("goal_understanding", goal_understanding_node)
        builder.add_node("profile_retrieval", profile_retrieval_node)
        builder.add_node("diagnostic", diagnostic_node)
        builder.add_node("learning_plan", learning_plan_node)
        builder.add_node("orchestrator", orchestrator_node)
        builder.add_node("teaching", teaching_node)
        builder.add_node("challenge", challenge_node)
        builder.add_node("prerequisite", prerequisite_node)
        builder.add_node("student_interaction", student_interaction_node)
        builder.add_node("evaluation", evaluation_node)
        builder.add_node("solver_verification", solver_verification_node)
        builder.add_node("state_updater", state_updater_node)
        builder.add_node("progress_evaluator", progress_evaluator_node)

    # 2. Linear preparation pipeline
    builder.add_edge(START, "goal_understanding")
    builder.add_edge("goal_understanding", "profile_retrieval")
    builder.add_edge("profile_retrieval", "diagnostic")
    builder.add_edge("diagnostic", "learning_plan")
    builder.add_edge("learning_plan", "orchestrator")

    # 3. Autonomous orchestrator routing
    builder.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "teaching": "teaching",
            "teach": "teaching",
            "challenge": "challenge",
            "prerequisite": "prerequisite",
            "prerequisite_intervention": "prerequisite",
        },
    )

    # 4. Instruction / Challenge converge to student interaction gate
    builder.add_edge("teaching", "student_interaction")
    builder.add_edge("challenge", "student_interaction")
    builder.add_edge("prerequisite", "student_interaction")

    # 5. Post-interaction evaluation, SymPy verification, and state update
    builder.add_edge("student_interaction", "evaluation")
    builder.add_edge("evaluation", "solver_verification")
    builder.add_edge("solver_verification", "state_updater")
    builder.add_edge("state_updater", "progress_evaluator")

    # 6. Autonomous progress evaluation and conditional replan / continue / finish loop
    builder.add_conditional_edges(
        "progress_evaluator",
        route_progress_evaluation,
        {
            "replan": "learning_plan",
            "continue": "orchestrator",
            "wait": "student_interaction",
            "complete": END,
            "terminate": END,
        },
    )

    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()

