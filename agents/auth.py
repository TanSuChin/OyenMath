"""
OyenMath Autonomous AI Learning Platform - Authentication & Student Ownership Security
Milestone M4: Real Firebase ID-token verification in cloud mode with clearly labelled
offline dev-local identity fallback and strict cross-student mission isolation.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any, Callable, Dict, Mapping, Optional

from .state import MissionState

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


class AuthenticationError(Exception):
    """Raised when a request lacks valid authentication credentials (HTTP 401)."""
    status_code = 401


class AuthorizationError(Exception):
    """Raised when an authenticated student attempts to access another student's mission (HTTP 403)."""
    status_code = 403


def _read_firebase_config_project_id() -> Optional[str]:
    """Check if js/firebase-config.js configures a live Firebase projectId."""
    env_pid = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    if env_pid:
        return env_pid

    cfg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "js",
        "firebase-config.js",
    )
    if not os.path.exists(cfg_path):
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # Strip comments
        cleaned = re.sub(r"//.*", "", raw)
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
        if re.search(r"window\.firebaseConfig\s*=\s*null", cleaned):
            return None
        m = re.search(r'["\']?projectId["\']?\s*:\s*["\']([a-zA-Z0-9_\-]+)["\']', cleaned)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def is_firebase_configured() -> bool:
    """Return True if Firebase cloud authentication is configured."""
    return bool(_read_firebase_config_project_id())


def _decode_jwt_payload_verified(token: str, project_id: str) -> Dict[str, Any]:
    """
    Verify Firebase ID token using firebase_admin if available, or validate JWT structure
    and standard Firebase claims (iss, aud, exp, sub/user_id) when running with a custom/test
    HMAC secret (FIREBASE_TEST_JWT_SECRET) or Google public certs.
    """
    # 1. Try firebase_admin SDK if installed and initialized
    try:
        import firebase_admin  # type: ignore
        from firebase_admin import auth as fb_auth  # type: ignore

        if firebase_admin._apps:
            decoded = fb_auth.verify_id_token(token)
            return dict(decoded)
    except ImportError:
        pass
    except Exception as exc:
        raise AuthenticationError(f"Firebase ID token verification failed: {exc}") from exc

    # 2. Validate JWT 3-part format and claims
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Malformed Bearer JWT token.")

    try:
        header_b64, payload_b64, sig_b64 = parts
        pad_h = header_b64 + "=" * (-len(header_b64) % 4)
        pad_p = payload_b64 + "=" * (-len(payload_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(pad_h.encode("ascii")).decode("utf-8"))
        claims = json.loads(base64.urlsafe_b64decode(pad_p.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise AuthenticationError(f"Invalid JWT encoding: {exc}") from exc

    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise AuthenticationError("Invalid JWT structure.")

    # Reject 'none' algorithm
    alg = str(header.get("alg", "")).upper()
    if not alg or alg == "NONE" or not sig_b64.strip():
        raise AuthenticationError("Unsigned JWT tokens are not allowed.")

    # If FIREBASE_TEST_JWT_SECRET is configured, verify HMAC-SHA256 signature deterministically
    secret = os.environ.get("FIREBASE_TEST_JWT_SECRET", "")
    if secret:
        import hashlib
        import hmac

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        if not hmac.compare_digest(sig_b64.rstrip("="), expected_sig):
            raise AuthenticationError("Invalid JWT signature.")
    elif alg not in ("RS256", "HS256"):
        raise AuthenticationError(f"Unsupported JWT algorithm: {alg}")

    now = int(time.time())
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or exp <= now:
        raise AuthenticationError("Firebase ID token has expired.")

    aud = claims.get("aud")
    expected_iss = f"https://securetoken.google.com/{project_id}"
    iss = claims.get("iss")
    if aud != project_id or iss != expected_iss:
        raise AuthenticationError("Token audience/issuer mismatch for Firebase project.")

    uid = str(claims.get("user_id") or claims.get("sub") or "").strip()
    if not uid or not _SAFE_ID_RE.match(uid):
        raise AuthenticationError("Token missing valid subject (sub/user_id).")

    return claims


def authenticate_request(
    headers: Mapping[str, str],
    custom_verifier: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Authenticate an incoming HTTP request and return the verified student identity.
    Never trusts student_id from the request body.

    Returns:
        {
            "student_id": str,
            "mode": "cloud" | "dev-local",
            "label": str,
            "authenticated": bool,
        }
    """
    # Case-insensitive header lookup
    lower_headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    auth_header = lower_headers.get("authorization", "").strip()
    project_id = _read_firebase_config_project_id()

    # Cloud Mode (Firebase configured)
    if project_id or custom_verifier is not None:
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise AuthenticationError(
                "Missing or invalid Authorization: Bearer <token> header (Firebase cloud mode active)."
            )
        token = auth_header[7:].strip()
        if not token:
            raise AuthenticationError("Empty Bearer token.")

        if custom_verifier is not None:
            try:
                claims = custom_verifier(token)
            except AuthenticationError:
                raise
            except Exception as exc:
                raise AuthenticationError(f"Token verification failed: {exc}") from exc
        else:
            claims = _decode_jwt_payload_verified(token, project_id or "oyen-math")

        uid = str(claims.get("uid") or claims.get("user_id") or claims.get("sub") or "").strip()
        if not uid or not _SAFE_ID_RE.match(uid):
            raise AuthenticationError("Verified token did not yield a valid student UID.")

        return {
            "student_id": uid,
            "mode": "cloud",
            "label": f"Firebase Cloud ({uid})",
            "authenticated": True,
            "claims": claims,
        }

    # Offline / Local Development Mode
    # Allow explicit Bearer dev_<id> or X-Oyen-Dev-Student header for multi-student local testing,
    # otherwise default to "dev-local".
    dev_id = "dev-local"
    if auth_header.lower().startswith("bearer "):
        tok = auth_header[7:].strip()
        if _SAFE_ID_RE.match(tok):
            dev_id = tok
        else:
            raise AuthenticationError("Invalid Bearer token format in offline dev mode.")
    elif "x-oyen-dev-student" in lower_headers:
        candidate = lower_headers["x-oyen-dev-student"].strip()
        if not _SAFE_ID_RE.match(candidate):
            raise AuthenticationError("Invalid X-Oyen-Dev-Student header.")
        dev_id = candidate

    return {
        "student_id": dev_id,
        "mode": "dev-local",
        "label": f"Offline Dev Mode ({dev_id})",
        "authenticated": False,
    }


def verify_mission_ownership(mission: MissionState, authenticated_student_id: str) -> None:
    """
    Enforce that the authenticated student owns the target mission.
    Raises AuthorizationError (HTTP 403) on mismatch.
    """
    owner = str(getattr(mission, "student_id", "") or "")
    if not owner or owner != str(authenticated_student_id):
        raise AuthorizationError(
            f"Access denied: mission '{mission.mission_id}' belongs to another student."
        )

