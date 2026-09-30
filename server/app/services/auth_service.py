"""Authentication: local owner token plus signed sessions for social-login members."""

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import Request, Response

from app.config import settings


LOCAL_USER_ID = "local-user"
LOCAL_USERNAME = "local"
SESSION_COOKIE = "open_dots_session"


class AuthService:
    """Validate the owner token and issue separate, short-lived browser sessions.

    With no environment token, the owner token is generated in a mode-0600 file.
    A client must present that token to log in; source address alone never grants
    an owner session because container and proxy traffic can appear as loopback.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = (data_dir or settings.DATA_DIR).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.token_path = self.data_dir / ".auth-token"
        self.configured_token = os.getenv("APP_AUTH_TOKEN", "").strip()
        self.token = self.configured_token or self._load_or_create_token()
        self.secret = self._load_or_create_secret()
        self._revoked: Dict[str, float] = {}

    @property
    def user(self) -> Dict[str, str]:
        return {"id": LOCAL_USER_ID, "username": LOCAL_USERNAME, "role": "owner"}

    def _load_or_create_token(self) -> str:
        if self.token_path.exists():
            existing = self.token_path.read_text(encoding="utf-8").strip()
            if existing:
                os.chmod(self.token_path, 0o600)
                return existing

        token = secrets.token_urlsafe(32)
        self.token_path.write_text(token + "\n", encoding="utf-8")
        os.chmod(self.token_path, 0o600)
        return token

    def _load_or_create_secret(self) -> bytes:
        configured = os.getenv("SESSION_SECRET", "").strip()
        if configured:
            return configured.encode()
        path = self.data_dir / ".session-secret"
        if path.exists() and path.read_text(encoding="utf-8").strip():
            os.chmod(path, 0o600)
            return path.read_text(encoding="utf-8").strip().encode()
        value = secrets.token_urlsafe(48)
        path.write_text(value + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
        return value.encode()

    def sign(self, payload: str) -> str:
        return hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()

    def _session_value(self, user_id: str) -> str:
        body = f"{user_id}.{int(time.time()) + settings.AUTH_SESSION_MAX_AGE}.{secrets.token_hex(6)}"
        return f"{body}.{self.sign(body)}"

    def _user_from_session(self, value: str) -> Optional[Dict[str, str]]:
        if not value or value in self._revoked:
            return None
        try:
            user_id, expires, nonce, signature = value.rsplit(".", 3)
            if not hmac.compare_digest(signature, self.sign(f"{user_id}.{expires}.{nonce}")):
                return None
            if int(expires) <= time.time():
                return None
        except ValueError:
            return None
        if user_id == LOCAL_USER_ID:
            return self.user
        from app.services.user_service import user_service  # avoids an import cycle

        return user_service.get(user_id)

    def authenticate_token(self, token: Optional[str]) -> bool:
        return bool(token) and secrets.compare_digest(token, self.token)

    def authenticate_request(self, request: Request) -> Optional[Dict[str, str]]:
        authorization = request.headers.get("authorization", "")
        scheme, _, bearer = authorization.partition(" ")
        if scheme.lower() == "bearer" and self.authenticate_token(bearer.strip()):
            return self.user

        return self._user_from_session(request.cookies.get(SESSION_COOKIE, ""))

    def can_bootstrap(self, request: Request) -> bool:
        # A loopback peer is not proof of an owner: Docker containers and
        # same-host proxies may also appear as loopback to the API.
        return False

    def set_session_cookie(self, response: Response, *, secure: Optional[bool] = None,
                           user_id: str = LOCAL_USER_ID) -> None:
        session = self._session_value(user_id)
        response.set_cookie(
            SESSION_COOKIE,
            session,
            max_age=settings.AUTH_SESSION_MAX_AGE,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE if secure is None else secure,
            samesite="lax",
        )

    @staticmethod
    def clear_session_cookie(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")

    def clear_request_session(self, request: Request, response: Response) -> None:
        session = request.cookies.get(SESSION_COOKIE, "")
        if session:
            self._revoked[session] = time.time()
            for key in [k for k, t in self._revoked.items() if t < time.time() - settings.AUTH_SESSION_MAX_AGE]:
                self._revoked.pop(key, None)
        self.clear_session_cookie(response)


auth_service = AuthService()
