"""Sign in with Google and Apple (OpenID Connect authorization-code flow).

State is a signed, short-lived token that also carries the nonce, so no server
session is needed before login. A cookie holding the nonce hash binds the flow
to the browser that started it.
"""

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
import jwt
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.services.auth_service import auth_service

STATE_TTL = 600
BINDING_COOKIE = "open_dots_oauth"


class OAuthError(RuntimeError):
    pass


PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "jwks": "https://www.googleapis.com/oauth2/v3/certs",
        "issuers": ("https://accounts.google.com", "accounts.google.com"),
        "scope": "openid email profile",
    },
    "apple": {
        "authorize": "https://appleid.apple.com/auth/authorize",
        "token": "https://appleid.apple.com/auth/token",
        "jwks": "https://appleid.apple.com/auth/keys",
        "issuers": ("https://appleid.apple.com",),
        "scope": "name email",
    },
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class OAuthService:
    # ---- configuration -------------------------------------------------
    def client_id(self, provider: str) -> str:
        return settings.GOOGLE_CLIENT_ID if provider == "google" else settings.APPLE_CLIENT_ID

    def apple_private_key(self) -> str:
        if settings.APPLE_PRIVATE_KEY:
            return settings.APPLE_PRIVATE_KEY
        if settings.APPLE_PRIVATE_KEY_PATH:
            return Path(settings.APPLE_PRIVATE_KEY_PATH).expanduser().read_text(encoding="utf-8")
        return ""

    def enabled(self) -> Dict[str, bool]:
        return {
            "google": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            "apple": bool(settings.APPLE_CLIENT_ID and settings.APPLE_TEAM_ID
                          and settings.APPLE_KEY_ID and self.apple_private_key()),
        }

    def local_login_allowed(self) -> bool:
        if settings.ALLOW_LOCAL_LOGIN in {"1", "true", "yes"}:
            return True
        if settings.ALLOW_LOCAL_LOGIN in {"0", "false", "no"}:
            return False
        return not any(self.enabled().values())

    def redirect_uri(self, provider: str, base: str) -> str:
        return f"{settings.PUBLIC_BASE_URL or base.rstrip('/')}/api/v1/auth/oauth/{provider}/callback"

    # ---- state ---------------------------------------------------------
    def make_state(self, provider: str, nonce: str) -> str:
        body = _b64(json.dumps({"p": provider, "n": nonce, "e": int(time.time()) + STATE_TTL}).encode())
        return f"{body}.{auth_service.sign('oauth.' + body)}"

    def read_state(self, state: str, provider: str) -> Dict[str, Any]:
        try:
            body, sig = state.rsplit(".", 1)
            if not secrets.compare_digest(sig, auth_service.sign("oauth." + body)):
                raise ValueError
            data = json.loads(_unb64(body))
        except (ValueError, json.JSONDecodeError) as exc:
            raise OAuthError("Invalid sign-in state.") from exc
        if data.get("p") != provider or data.get("e", 0) < time.time():
            raise OAuthError("Sign-in expired. Try again.")
        return data

    @staticmethod
    def binding(nonce: str) -> str:
        return hashlib.sha256(nonce.encode()).hexdigest()

    # ---- flow ----------------------------------------------------------
    def authorize_url(self, provider: str, base: str):
        nonce = secrets.token_urlsafe(24)
        params = {
            "client_id": self.client_id(provider),
            "redirect_uri": self.redirect_uri(provider, base),
            "response_type": "code",
            "scope": PROVIDERS[provider]["scope"],
            "state": self.make_state(provider, nonce),
            "nonce": nonce,
        }
        if provider == "apple":
            params["response_mode"] = "form_post"
        else:
            params["prompt"] = "select_account"
        return f"{PROVIDERS[provider]['authorize']}?{urlencode(params)}", nonce

    def apple_client_secret(self) -> str:
        now = int(time.time())
        return jwt.encode(
            {"iss": settings.APPLE_TEAM_ID, "iat": now, "exp": now + 300,
             "aud": "https://appleid.apple.com", "sub": settings.APPLE_CLIENT_ID},
            self.apple_private_key(), algorithm="ES256", headers={"kid": settings.APPLE_KEY_ID})

    async def exchange_code(self, provider: str, code: str, base: str) -> str:
        secret = settings.GOOGLE_CLIENT_SECRET if provider == "google" else self.apple_client_secret()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(PROVIDERS[provider]["token"], data={
                "grant_type": "authorization_code", "code": code,
                "client_id": self.client_id(provider), "client_secret": secret,
                "redirect_uri": self.redirect_uri(provider, base)})
        if response.status_code != 200 or "id_token" not in response.json():
            raise OAuthError("The provider rejected the sign-in.")
        return response.json()["id_token"]

    async def verify_id_token(self, provider: str, id_token: str, nonce: str) -> Dict[str, Any]:
        cfg = PROVIDERS[provider]

        def decode() -> Dict[str, Any]:
            key = jwt.PyJWKClient(cfg["jwks"]).get_signing_key_from_jwt(id_token).key
            claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=self.client_id(provider),
                                options={"verify_iss": False})
            if claims.get("iss") not in cfg["issuers"]:
                raise OAuthError("Unexpected token issuer.")
            return claims

        try:
            claims = await run_in_threadpool(decode)
        except jwt.PyJWTError as exc:
            raise OAuthError("Could not verify the sign-in token.") from exc
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise OAuthError("Sign-in nonce mismatch.")
        return claims

    async def complete(self, provider: str, code: str, state: str, cookie: Optional[str],
                       base: str, secure: bool, apple_user: Optional[str] = None) -> Dict[str, Any]:
        """Verify the callback and return the provider identity."""
        data = self.read_state(state, provider)
        # Apple posts back cross-site, so its Lax cookie is only sent over HTTPS with SameSite=None.
        if cookie is not None or provider == "google" or secure:
            if not cookie or not secrets.compare_digest(cookie, self.binding(data["n"])):
                raise OAuthError("Sign-in must finish in the same browser it started in.")
        id_token = await self.exchange_code(provider, code, base)
        claims = await self.verify_id_token(provider, id_token, data["n"])
        name = claims.get("name", "")
        if provider == "apple" and apple_user:
            try:
                parts = json.loads(apple_user).get("name", {})
                name = f"{parts.get('firstName', '')} {parts.get('lastName', '')}".strip()
            except (json.JSONDecodeError, AttributeError):
                pass
        return {
            "sub": str(claims["sub"]),
            "email": claims.get("email", ""),
            "email_verified": str(claims.get("email_verified", "")).lower() == "true",
            "name": name,
            "picture": claims.get("picture", ""),
        }


oauth_service = OAuthService()
