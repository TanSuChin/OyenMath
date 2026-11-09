"""
OyenMath Autonomous AI Learning Platform - Mission REST API & Security Tests (Milestone M4 & M6)
Tests:
- All exact /api/missions/{mission_id}/* endpoints over live ThreadingHTTPServer
- Cross-student ownership isolation (403 Forbidden)
- Firebase Bearer token verification (401 Unauthorized on missing/expired/invalid tokens)
- Offline dev-local mode fallback
- Idempotency key protection against duplicate mission launches
- Full end-to-end mission lifecycle (start -> waiting_for_student -> respond -> pause -> resume -> cancel -> history)
- Backward compatibility of POST /api/agent
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from agents.checkpoint import OyenFileCheckpointer
from agents.mission_runner import MissionRunner
import server


def _make_jwt(header: dict, payload: dict, secret: str = "test-secret-key") -> str:
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("ascii").rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    if header.get("alg", "").upper() == "NONE" or not secret:
        sig_b64 = ""
    else:
        sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{h_b64}.{p_b64}.{sig_b64}"


class MissionAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["OYEN_QUIET_LOGS"] = "1"
        cls.tmp_dir = tempfile.mkdtemp(prefix="oyen_api_test_")
        checkpointer = OyenFileCheckpointer(base_dir=cls.tmp_dir)
        cls.runner = MissionRunner(checkpointer=checkpointer, llm=None)
        server.set_mission_runner(cls.runner)

        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.runner.shutdown(wait=False)
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self) -> None:
        os.environ.pop("FIREBASE_PROJECT_ID", None)
        os.environ.pop("FIREBASE_TEST_JWT_SECRET", None)
        server.set_custom_token_verifier(None)

    def _req(self, method: str, path: str, body: dict = None, headers: dict = None):
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"error": raw}

    # ------------------------------------------------------------------
    # 1. Mission Lifecycle over exact /api/missions/{mission_id}/* routes
    # ------------------------------------------------------------------

    def test_full_mission_lifecycle_routes(self) -> None:
        # 1. POST /api/missions/start
        code, started = self._req(
            "POST",
            "/api/missions/start",
            {
                "topic_id": "dif",
                "target_mastery": 0.80,
                "goal": "Master Differentiation to 80%",
                "initial_mastery": {"dif": 0.30, "ind": 0.75},
            },
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 201)
        mid = started["mission_id"]
        self.assertEqual(started["student_id"], "student_aiman")
        self.assertEqual(started["status"], "WAITING_FOR_STUDENT")
        self.assertEqual(started["auth_mode"], "dev-local")
        self.assertTrue(len(started["plan"]["activities"]) > 0)

        # 2. GET /api/missions/{mission_id}
        code, detail = self._req(
            "GET",
            f"/api/missions/{mid}",
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(detail["mission_id"], mid)
        self.assertIn("progress_summary", detail)

        # 3. GET /api/missions/{mission_id}/status
        code, status_data = self._req(
            "GET",
            f"/api/missions/{mid}/status",
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(status_data["status"], "WAITING_FOR_STUDENT")
        self.assertIsNotNone(status_data["current_activity"])

        # 4. POST /api/missions/{mission_id}/respond with verified correct answer
        cur_act = status_data["current_activity"]
        correct_ans = cur_act.get("expected_answer") or cur_act.get("correct_answer") or "6*x + 5"
        code, responded = self._req(
            "POST",
            f"/api/missions/{mid}/respond",
            {"answer": correct_ans},
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(responded.get("learning_history", [])), 1)

        # 5. POST /api/missions/{mission_id}/pause
        code, paused = self._req(
            "POST",
            f"/api/missions/{mid}/pause",
            {},
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(paused["status"], "PAUSED")

        # 6. POST /api/missions/{mission_id}/resume
        code, resumed = self._req(
            "POST",
            f"/api/missions/{mid}/resume",
            {},
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertIn(resumed["status"], ("WAITING_FOR_STUDENT", "RUNNING", "COMPLETED"))

        # 7. GET /api/missions/{mission_id}/history
        code, hist = self._req(
            "GET",
            f"/api/missions/{mid}/history",
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(hist["mission_id"], mid)
        self.assertTrue(len(hist["trace"]) > 0)

        # 8. POST /api/missions/{mission_id}/cancel
        code, cancelled = self._req(
            "POST",
            f"/api/missions/{mid}/cancel",
            {},
            headers={"X-Oyen-Dev-Student": "student_aiman"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(cancelled["status"], "CANCELLED")

    # ------------------------------------------------------------------
    # 2. Cross-Student Ownership Validation (403 Forbidden)
    # ------------------------------------------------------------------

    def test_cross_student_access_denied(self) -> None:
        code, started = self._req(
            "POST",
            "/api/missions/start",
            {"topic_id": "integ", "target_mastery": 0.80},
            headers={"X-Oyen-Dev-Student": "student_alice"},
        )
        self.assertEqual(code, 201)
        mid = started["mission_id"]

        # Student Bob attempts to read, pause, respond, and cancel Alice's mission
        for method, path, payload in [
            ("GET", f"/api/missions/{mid}", None),
            ("GET", f"/api/missions/{mid}/status", None),
            ("GET", f"/api/missions/{mid}/history", None),
            ("POST", f"/api/missions/{mid}/pause", {}),
            ("POST", f"/api/missions/{mid}/resume", {}),
            ("POST", f"/api/missions/{mid}/respond", {"answer": "x^2 + C"}),
            ("POST", f"/api/missions/{mid}/cancel", {}),
        ]:
            code, err = self._req(
                method,
                path,
                payload,
                headers={"X-Oyen-Dev-Student": "student_bob"},
            )
            self.assertEqual(code, 403, f"Expected 403 for {method} {path}, got {code}")
            self.assertEqual(err.get("code"), "FORBIDDEN")

    # ------------------------------------------------------------------
    # 3. Firebase Cloud ID-Token Verification (401 on missing/invalid/expired)
    # ------------------------------------------------------------------

    def test_firebase_bearer_token_enforcement(self) -> None:
        os.environ["FIREBASE_PROJECT_ID"] = "oyen-math-spm"
        os.environ["FIREBASE_TEST_JWT_SECRET"] = "super-secret-oyen-hmac"

        # A. Missing Authorization header -> 401
        code, err = self._req("POST", "/api/missions/start", {"topic_id": "dif"})
        self.assertEqual(code, 401)
        self.assertEqual(err.get("code"), "UNAUTHENTICATED")

        # B. Expired JWT token -> 401
        expired_tok = _make_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {
                "iss": "https://securetoken.google.com/oyen-math-spm",
                "aud": "oyen-math-spm",
                "sub": "firebase_uid_123",
                "exp": int(time.time()) - 120,
            },
            secret="super-secret-oyen-hmac",
        )
        code, _ = self._req(
            "POST",
            "/api/missions/start",
            {"topic_id": "dif"},
            headers={"Authorization": f"Bearer {expired_tok}"},
        )
        self.assertEqual(code, 401)

        # C. Unsigned alg=none token -> 401
        none_tok = _make_jwt(
            {"alg": "none", "typ": "JWT"},
            {
                "iss": "https://securetoken.google.com/oyen-math-spm",
                "aud": "oyen-math-spm",
                "sub": "firebase_uid_123",
                "exp": int(time.time()) + 3600,
            },
            secret="",
        )
        code, _ = self._req(
            "POST",
            "/api/missions/start",
            {"topic_id": "dif"},
            headers={"Authorization": f"Bearer {none_tok}"},
        )
        self.assertEqual(code, 401)

        # D. Valid Firebase JWT token -> 201 Created, ignores spoofed body student_id
        valid_tok = _make_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {
                "iss": "https://securetoken.google.com/oyen-math-spm",
                "aud": "oyen-math-spm",
                "sub": "firebase_uid_123",
                "exp": int(time.time()) + 3600,
            },
            secret="super-secret-oyen-hmac",
        )
        code, created = self._req(
            "POST",
            "/api/missions/start",
            {"topic_id": "dif", "student_id": "spoofed_attacker_id"},
            headers={"Authorization": f"Bearer {valid_tok}"},
        )
        self.assertEqual(code, 201)
        self.assertEqual(created["student_id"], "firebase_uid_123")
        self.assertEqual(created["auth_mode"], "cloud")

    # ------------------------------------------------------------------
    # 4. Idempotency & Legacy /api/agent Backward Compatibility
    # ------------------------------------------------------------------

    def test_idempotency_and_legacy_agent_compatibility(self) -> None:
        # Idempotent start replay returns same mission_id without launching duplicate
        code1, m1 = self._req(
            "POST",
            "/api/missions/start",
            {"topic_id": "quad", "idempotency_key": "idem_unique_99"},
            headers={"X-Oyen-Dev-Student": "student_idem"},
        )
        code2, m2 = self._req(
            "POST",
            "/api/missions/start",
            {"topic_id": "quad", "idempotency_key": "idem_unique_99"},
            headers={"X-Oyen-Dev-Student": "student_idem"},
        )
        self.assertEqual(code1, 201)
        self.assertEqual(code2, 200)
        self.assertEqual(m1["mission_id"], m2["mission_id"])
        self.assertTrue(m2.get("idempotent_replay"))

        # Legacy POST /api/agent still works
        code_leg, leg_out = self._req(
            "POST",
            "/api/agent",
            {
                "topic": "dif",
                "question": "f(x)=3x^2+5x-2",
                "student_answer": "6x^2+5",
                "correct_answer": "6x+5",
                "level": 2,
                "error_tags": {"exp": 2},
                "recent": [{"ok": False}] * 3,
                "mastery": {"ind": 0.2},
            },
        )
        self.assertEqual(code_leg, 200)
        self.assertEqual(leg_out["action"], "prerequisite")
        self.assertEqual(leg_out["next_topic"], "ind")


if __name__ == "__main__":
    unittest.main()

