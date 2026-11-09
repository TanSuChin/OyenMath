#!/usr/bin/env python3
"""
Oyen Math - Local & Production HTTP Server
Serves the Oyen Math web application and Autonomous Mission Lifecycle REST API on http://localhost:8080
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Callable, Dict, Optional, Tuple


def _load_env() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, ".env"),
        os.path.join(os.path.dirname(here), ".env"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        val = v.strip().strip('"').strip("'")
                        if val and val != "your-key-here":
                            os.environ.setdefault(k.strip(), val)


_load_env()
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
GROQ_VISION_MODEL = os.environ.get(
    "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)

OCR_PROMPT = (
    "You are Detective Oyen, marking a Malaysian SPM Additional Mathematics student's handwritten working. "
    "Transcribe every line of working in the image in order, in plain text using ^ for powers. "
    "For each line decide if it is mathematically valid given the previous line; if not, explain the error briefly in Bahasa Melayu. "
    "Question (may be empty): {q}\n"
    "Reply with ONLY JSON: {{\"lines\":[{{\"text\":str,\"valid\":bool,\"error\":str|null}}],\"finalAnswer\":str}}. "
    "finalAnswer is the student's final answer only, in plain text (e.g. 6x+5)."
)


def run_ocr(image_data_url: str, question: str) -> Tuple[int, Dict[str, Any]]:
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    anth_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anth_key.startswith("gsk_") and not groq_key:
        groq_key, anth_key = anth_key, ""

    if groq_key and groq_key != "your-key-here":
        body = {
            "model": GROQ_VISION_MODEL,
            "max_tokens": 1200,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {"type": "text", "text": OCR_PROMPT.format(q=question[:300])},
                    ],
                }
            ],
        }
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "OyenMath-OCR/4.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp_json = json.load(r)
                text = (resp_json.get("choices") or [{}])[0].get("message", {}).get("content", "")
            a, z = text.find("{"), text.rfind("}")
            data = json.loads(text[a : z + 1])
            data["engine"] = "groq-vision"
            return 200, data
        except urllib.error.HTTPError as e:
            return 502, {"error": "Groq API ralat %s" % e.code}
        except Exception as e:
            return 502, {"error": "Groq OCR gagal: %s" % e}

    key = anth_key
    if not key:
        return 503, {"error": "GROQ_API_KEY atau ANTHROPIC_API_KEY belum ditetapkan (lihat .env.example)"}
    header, _, b64 = image_data_url.partition(",")
    media = header.split(";")[0].replace("data:", "") or "image/jpeg"
    body = {
        "model": MODEL,
        "max_tokens": 1200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
                    {"type": "text", "text": OCR_PROMPT.format(q=question[:300])},
                ],
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = "".join(b.get("text", "") for b in json.load(r)["content"])
        a, z = text.find("{"), text.rfind("}")
        data = json.loads(text[a : z + 1])
        data["engine"] = "claude-vision"
        return 200, data
    except urllib.error.HTTPError as e:
        return 502, {"error": "Anthropic API ralat %s" % e.code}
    except Exception as e:
        return 502, {"error": "OCR gagal: %s" % e}


PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Singleton MissionRunner & Idempotency Registry
_RUNNER_LOCK = threading.Lock()
_MISSION_RUNNER = None
_IDEMPOTENCY_CACHE: Dict[str, str] = {}
_CUSTOM_TOKEN_VERIFIER: Optional[Callable[[str], Dict[str, Any]]] = None


def get_mission_runner():
    """Return or initialize singleton MissionRunner instance."""
    global _MISSION_RUNNER
    with _RUNNER_LOCK:
        if _MISSION_RUNNER is None:
            from agents.graph import default_client
            from agents.mission_runner import MissionRunner

            _MISSION_RUNNER = MissionRunner(llm=default_client())
        return _MISSION_RUNNER


def set_mission_runner(runner) -> None:
    """Override MissionRunner singleton (used by unit/integration tests)."""
    global _MISSION_RUNNER
    with _RUNNER_LOCK:
        _MISSION_RUNNER = runner
        _IDEMPOTENCY_CACHE.clear()


def set_custom_token_verifier(verifier: Optional[Callable[[str], Dict[str, Any]]]) -> None:
    """Override Firebase token verifier (used by security tests)."""
    global _CUSTOM_TOKEN_VERIFIER
    _CUSTOM_TOKEN_VERIFIER = verifier


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _serialize_mission_summary(state, auth_info: Dict[str, Any]) -> Dict[str, Any]:
    """Build full API payload for a MissionState."""
    d = state.to_dict()
    plan_acts = d.get("plan", {}).get("activities", []) or []
    completed_count = sum(1 for a in plan_acts if str(a.get("status", "")).upper() == "COMPLETED")
    total_count = max(1, len(plan_acts))
    topic = d.get("topic_id") or d.get("goal", {}).get("topic", "dif")
    current_mastery = float(
        d.get("verified_mastery", {}).get(topic, d.get("mastery", {}).get(topic, 0.0))
    )
    target_mastery = float(d.get("goal", {}).get("target_mastery", 0.80))

    # Next recommended activity
    next_act = d.get("current_activity")
    if not next_act:
        for act in plan_acts:
            if str(act.get("status", "")).upper() in ("PENDING", "IN_PROGRESS"):
                next_act = act
                break

    d["auth_mode"] = auth_info.get("mode", "dev-local")
    d["auth_label"] = auth_info.get("label", "Offline Dev Mode (dev-local)")
    d["progress_summary"] = {
        "completed_activities_count": len(d.get("completed_activities", [])),
        "plan_completed_count": completed_count,
        "plan_total_count": len(plan_acts),
        "plan_progress_pct": round((completed_count / total_count) * 100, 1) if plan_acts else 0.0,
        "initial_mastery": float(d.get("initial_mastery", {}).get(topic, 0.0)),
        "current_verified_mastery": current_mastery,
        "target_mastery": target_mastery,
        "goal_progress_pct": round(min(100.0, (current_mastery / max(0.01, target_mastery)) * 100), 1),
        "questions_answered": len(d.get("learning_history", [])),
        "next_recommended_activity": next_act,
    }
    return d


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        if os.environ.get("OYEN_QUIET_LOGS") == "1":
            return
        super().log_message(format, *args)

    def _send_json(self, code: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self, max_bytes: int = 200_000) -> Dict[str, Any]:
        length_str = self.headers.get("Content-Length", "0")
        try:
            n = int(length_str)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        if n > max_bytes:
            raise ValueError("Payload terlalu besar / Payload too large")
        raw = self.rfile.read(n)
        if not raw:
            return {}
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    def _authenticate(self) -> Dict[str, Any]:
        from agents.auth import authenticate_request

        hdrs = {k: v for k, v in self.headers.items()}
        return authenticate_request(hdrs, custom_verifier=_CUSTOM_TOKEN_VERIFIER)

    def _load_owned_mission(self, mission_id: str, auth_info: Dict[str, Any]):
        from agents.auth import AuthorizationError, verify_mission_ownership
        from agents.checkpoint import CheckpointNotFoundError

        if not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", mission_id or ""):
            raise ValueError("Invalid mission_id format.")

        runner = get_mission_runner()
        # First locate mission across storage to distinguish 404 vs 403
        mission = runner.get_mission(mission_id, student_id=None)
        if mission is None:
            raise CheckpointNotFoundError(f"Mission '{mission_id}' not found.")

        verify_mission_ownership(mission, auth_info["student_id"])
        return runner, mission

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/") or "/"

        if path.startswith("/api/missions") or path.startswith("/api/mission"):
            return self._handle_missions_get(path, parsed_url.query)

        return super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/") or "/"

        if path == "/api/agent":
            return self._agent()
        if path == "/api/ocr":
            return self._ocr()
        if path.startswith("/api/missions") or path.startswith("/api/mission"):
            return self._handle_missions_post(path)

        self._send_json(404, {"error": "Endpoint tidak ditemui / Endpoint not found"})

    # -------------------------------------------------------------------------
    # Legacy Endpoints (/api/ocr and /api/agent)
    # -------------------------------------------------------------------------

    def _ocr(self) -> None:
        n = int(self.headers.get("Content-Length", 0))
        if n > 8 * 1024 * 1024:
            code, out = 413, {"error": "Gambar terlalu besar"}
        else:
            try:
                req = json.loads(self.rfile.read(n))
                code, out = run_ocr(req.get("image", ""), req.get("question", ""))
            except Exception as e:
                code, out = 400, {"error": "Permintaan tidak sah: %s" % e}
        self._send_json(code, out)

    def _agent(self) -> None:
        n = int(self.headers.get("Content-Length", 0))
        try:
            from agents.graph import run_agent

            code, out = 200, run_agent(json.loads(self.rfile.read(min(n, 200000))))
        except ImportError as e:
            code, out = 501, {"error": "Pasang kebergantungan: pip install -r requirements.txt (%s)" % e}
        except Exception as e:
            code, out = 500, {"error": "Ejen gagal: %s" % e}
        self._send_json(code, out)

    # -------------------------------------------------------------------------
    # Autonomous Mission Endpoints (/api/missions/*)
    # -------------------------------------------------------------------------

    def _handle_missions_get(self, path: str, query_str: str) -> None:
        from agents.auth import AuthenticationError, AuthorizationError
        from agents.checkpoint import CheckpointNotFoundError

        try:
            auth_info = self._authenticate()
            student_id = auth_info["student_id"]
            runner = get_mission_runner()

            # GET /api/missions -> list authenticated student's missions
            if path in ("/api/missions", "/api/mission"):
                missions = runner.list_missions(student_id=student_id)
                return self._send_json(
                    200,
                    {
                        "student_id": student_id,
                        "auth_mode": auth_info["mode"],
                        "auth_label": auth_info["label"],
                        "missions": missions,
                    },
                )

            # Support query-param style GET /api/mission/status?mission_id=...
            qs = urllib.parse.parse_qs(query_str)
            q_mid = (qs.get("mission_id") or [None])[0]

            # Match /api/missions/{mission_id} or /api/missions/{mission_id}/{sub}
            m = re.match(r"^/api/missions?/([a-zA-Z0-9_\-]+)(?:/(status|history))?$", path)
            if not m:
                return self._send_json(404, {"error": f"Unknown mission GET route: {path}"})

            part1, sub = m.group(1), m.group(2)
            if part1 in ("status", "history") and q_mid:
                mission_id = q_mid
                sub = part1
            else:
                mission_id = part1

            _, state = self._load_owned_mission(mission_id, auth_info)
            full_payload = _serialize_mission_summary(state, auth_info)

            if sub == "status":
                return self._send_json(
                    200,
                    {
                        "mission_id": state.mission_id,
                        "student_id": state.student_id,
                        "status": state.status.value if hasattr(state.status, "value") else str(state.status),
                        "topic_id": state.topic_id,
                        "current_agent": state.current_agent,
                        "current_activity": full_payload.get("current_activity"),
                        "waiting_interaction": full_payload.get("waiting_interaction"),
                        "goal": full_payload.get("goal"),
                        "plan": full_payload.get("plan"),
                        "mastery": full_payload.get("mastery"),
                        "verified_mastery": full_payload.get("verified_mastery"),
                        "initial_mastery": full_payload.get("initial_mastery"),
                        "identified_misconceptions": full_payload.get("identified_misconceptions"),
                        "budget": full_payload.get("budget"),
                        "trace": full_payload.get("trace", [])[-30:],
                        "progress_summary": full_payload.get("progress_summary"),
                        "updated_at": state.updated_at,
                        "terminated_at": state.terminated_at,
                        "termination_reason": state.termination_reason,
                        "auth_mode": auth_info["mode"],
                        "auth_label": auth_info["label"],
                    },
                )

            if sub == "history":
                return self._send_json(
                    200,
                    {
                        "mission_id": state.mission_id,
                        "student_id": state.student_id,
                        "status": state.status.value if hasattr(state.status, "value") else str(state.status),
                        "completed_activities": full_payload.get("completed_activities", []),
                        "learning_history": full_payload.get("learning_history", []),
                        "history": full_payload.get("history", []),
                        "trace": full_payload.get("trace", []),
                        "initial_mastery": full_payload.get("initial_mastery", {}),
                        "verified_mastery": full_payload.get("verified_mastery", {}),
                        "identified_misconceptions": full_payload.get("identified_misconceptions", []),
                        "progress_summary": full_payload.get("progress_summary"),
                        "auth_mode": auth_info["mode"],
                    },
                )

            # GET /api/missions/{mission_id}
            return self._send_json(200, full_payload)

        except AuthenticationError as e:
            self._send_json(401, {"error": str(e), "code": "UNAUTHENTICATED"})
        except AuthorizationError as e:
            self._send_json(403, {"error": str(e), "code": "FORBIDDEN"})
        except CheckpointNotFoundError as e:
            self._send_json(404, {"error": str(e), "code": "NOT_FOUND"})
        except ValueError as e:
            self._send_json(400, {"error": str(e), "code": "BAD_REQUEST"})
        except Exception as e:
            self._send_json(500, {"error": f"Server error: {e}", "code": "INTERNAL_ERROR"})

    def _handle_missions_post(self, path: str) -> None:
        from agents.auth import AuthenticationError, AuthorizationError
        from agents.checkpoint import CheckpointNotFoundError

        try:
            auth_info = self._authenticate()
            student_id = auth_info["student_id"]
            body = self._read_json_body()
            runner = get_mission_runner()

            # 1. POST /api/missions/start
            if path in ("/api/missions/start", "/api/mission/start"):
                topic_id = str(body.get("topic_id") or body.get("topic") or "dif").strip().lower()
                if topic_id not in ("dif", "integ", "ind", "quad"):
                    raise ValueError(f"Unsupported topic_id '{topic_id}'. Allowed: dif, integ, ind, quad.")

                target_mastery = float(body.get("target_mastery", 0.80))
                if not (0.1 <= target_mastery <= 1.0):
                    raise ValueError("target_mastery must be between 0.1 and 1.0.")

                language = str(body.get("language", "ms")).strip().lower()
                if language not in ("ms", "en"):
                    language = "ms"

                goal_input = body.get("goal") or body.get("objective")
                budget_input = body.get("budget")
                initial_mastery = body.get("initial_mastery") or body.get("mastery")
                background = bool(body.get("background", False))

                # Idempotency protection against duplicate start clicks
                idem_key = str(
                    body.get("idempotency_key")
                    or self.headers.get("Idempotency-Key")
                    or ""
                ).strip()
                if idem_key:
                    cache_key = f"{student_id}:{idem_key}"
                    with _RUNNER_LOCK:
                        existing_mid = _IDEMPOTENCY_CACHE.get(cache_key)
                    if existing_mid:
                        existing_state = runner.get_mission(existing_mid, student_id=student_id)
                        if existing_state is not None:
                            out = _serialize_mission_summary(existing_state, auth_info)
                            out["idempotent_replay"] = True
                            return self._send_json(200, out)

                created = runner.create_mission(
                    student_id=student_id,
                    goal=goal_input,
                    topic_id=topic_id,
                    target_mastery=target_mastery,
                    budget=budget_input,
                    language=language,
                    initial_mastery=initial_mastery if isinstance(initial_mastery, dict) else None,
                )

                if idem_key:
                    with _RUNNER_LOCK:
                        _IDEMPOTENCY_CACHE[f"{student_id}:{idem_key}"] = created.mission_id

                started = runner.start_mission(
                    created.mission_id,
                    student_id=student_id,
                    background=background,
                )
                return self._send_json(201, _serialize_mission_summary(started, auth_info))

            # 2. Match /api/missions/{mission_id}/{action}
            m = re.match(
                r"^/api/missions?/([a-zA-Z0-9_\-]+)/(pause|resume|cancel|respond)$",
                path,
            )
            if not m:
                # Also allow /api/mission/{action} with mission_id in body
                m_legacy = re.match(r"^/api/missions?/(pause|resume|cancel|respond)$", path)
                if m_legacy and body.get("mission_id"):
                    mission_id = str(body["mission_id"])
                    action = m_legacy.group(1)
                else:
                    return self._send_json(404, {"error": f"Unknown mission POST route: {path}"})
            else:
                mission_id, action = m.group(1), m.group(2)

            runner, state = self._load_owned_mission(mission_id, auth_info)
            background = bool(body.get("background", False))

            if action == "pause":
                updated = runner.pause_mission(mission_id, student_id=student_id)
                return self._send_json(200, _serialize_mission_summary(updated, auth_info))

            if action == "resume":
                updated = runner.resume_paused_mission(
                    mission_id,
                    student_id=student_id,
                    background=background,
                )
                return self._send_json(200, _serialize_mission_summary(updated, auth_info))

            if action == "cancel":
                updated = runner.cancel_mission(mission_id, student_id=student_id)
                return self._send_json(200, _serialize_mission_summary(updated, auth_info))

            if action == "respond":
                if "answer" not in body and "student_answer" not in body and "response" not in body:
                    raise ValueError("Missing 'answer' field in mission respond request.")
                raw_ans = body.get("answer")
                if raw_ans is None:
                    raw_ans = body.get("student_answer")
                if raw_ans is None:
                    raw_ans = body.get("response")
                ans_str = str(raw_ans).strip()
                if not ans_str:
                    raise ValueError("Student answer cannot be empty.")

                student_resp_payload = {
                    "answer": ans_str,
                    "activity_id": body.get("activity_id")
                    or (state.current_activity.activity_id if state.current_activity else None),
                    "question": body.get("question")
                    or (state.current_activity.question if state.current_activity else None),
                    "expected_answer": body.get("expected_answer")
                    or (state.current_activity.expected_answer if state.current_activity else None),
                    "time_spent_sec": float(body.get("time_spent_sec", 0.0)),
                }
                updated = runner.resume_mission(
                    mission_id,
                    student_response=student_resp_payload,
                    student_id=student_id,
                    background=background,
                )
                return self._send_json(200, _serialize_mission_summary(updated, auth_info))

        except AuthenticationError as e:
            self._send_json(401, {"error": str(e), "code": "UNAUTHENTICATED"})
        except AuthorizationError as e:
            self._send_json(403, {"error": str(e), "code": "FORBIDDEN"})
        except CheckpointNotFoundError as e:
            self._send_json(404, {"error": str(e), "code": "NOT_FOUND"})
        except ValueError as e:
            self._send_json(400, {"error": str(e), "code": "BAD_REQUEST"})
        except Exception as e:
            self._send_json(500, {"error": f"Server error: {e}", "code": "INTERNAL_ERROR"})

    def end_headers(self) -> None:
        # Enable CORS and disable caching for smooth development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Oyen-Dev-Student, Idempotency-Key",
        )
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main() -> None:
    os.chdir(DIRECTORY)
    with ThreadingHTTPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 60)
        print("🐱 OYEN MATH - Autonomous Agentic Platform Server Running")
        print(f"📍 URL: {url}")
        print("📖 Press Ctrl+C to stop the server.")
        print("=" * 60)
        if "--open" in sys.argv:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Oyen Math server. Goodbye! Meow!")


if __name__ == "__main__":
    main()
