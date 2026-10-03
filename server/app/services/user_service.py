"""Members created by social sign-in (Google, Apple)."""

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.storage_service import storage_service

PUBLIC_FIELDS = ("id", "username", "role", "email", "name", "picture", "provider", "disabled", "token_limit")


def _public(row) -> Dict[str, Any]:
    data = {k: row[k] for k in PUBLIC_FIELDS}
    data["disabled"] = bool(data["disabled"])
    return data


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s.]{2,}$")
MIN_PASSWORD = 8


class SignupError(ValueError):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(got.hex(), digest)
    except (ValueError, AttributeError):
        return False


class UserService:
    def register_password(self, email: str, password: str, name: str = "") -> Dict[str, Any]:
        """Create a member with their own email + password (never linked to Google/Apple)."""
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            raise SignupError("Aquest correu no sembla vàlid.")
        if len(password) < MIN_PASSWORD:
            raise SignupError(f"La contrasenya ha de tenir almenys {MIN_PASSWORD} caràcters.")
        with storage_service.database.connect() as c:
            if c.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
                raise SignupError("Ja hi ha un compte amb aquest correu. Entra-hi o fes servir Google/Apple.")
            user_id = f"usr-{uuid.uuid4().hex[:12]}"
            c.execute(
                "INSERT INTO users(id, username, role, created_at, provider, provider_sub, email, name, password_hash) "
                "VALUES (?, ?, 'member', ?, 'password', ?, ?, ?, ?)",
                (user_id, f"password:{email}", datetime.now(timezone.utc).isoformat(), email, email,
                 name.strip()[:80] or email.split("@")[0], hash_password(password)))
            row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public(row)

    def verify_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        with storage_service.database.connect() as c:
            row = c.execute("SELECT * FROM users WHERE provider = 'password' AND provider_sub = ?",
                            (email.strip().lower(),)).fetchone()
        # Always do the hashing work so timing doesn't reveal which emails exist.
        stored = row["password_hash"] if row and row["password_hash"] else hash_password("x")
        ok = check_password(password, stored)
        return _public(row) if row and ok else None

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        with storage_service.database.connect() as c:
            row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public(row) if row else None

    def set_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        with storage_service.database.connect() as c:
            c.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        return self.get(user_id)

    def touch(self, user_id: str) -> None:
        with storage_service.database.connect() as c:
            c.execute("UPDATE users SET last_seen = ? WHERE id = ?",
                      (datetime.now(timezone.utc).isoformat(), user_id))

    def set_controls(self, user_id: str, disabled=None, token_limit="keep") -> Optional[Dict[str, Any]]:
        with storage_service.database.connect() as c:
            if disabled is not None:
                c.execute("UPDATE users SET disabled = ? WHERE id = ?", (1 if disabled else 0, user_id))
            if token_limit != "keep":
                c.execute("UPDATE users SET token_limit = ? WHERE id = ?", (token_limit, user_id))
        return self.get(user_id)

    def upsert_social(self, provider: str, sub: str, email: str = "", name: str = "",
                      picture: str = "", email_verified: bool = False, role: str = "member") -> Dict[str, Any]:
        """Find the member for a provider identity, linking by verified email."""
        with storage_service.database.connect() as c:
            row = c.execute("SELECT * FROM users WHERE provider = ? AND provider_sub = ?",
                            (provider, sub)).fetchone()
            if row is None and email and email_verified:
                # Same person signing in with a second provider.
                row = c.execute("SELECT * FROM users WHERE lower(email) = lower(?) AND provider IS NOT NULL "
                    "AND provider != 'password'",
                                (email,)).fetchone()
            if row is not None:
                c.execute("UPDATE users SET email = COALESCE(NULLIF(?, ''), email), "
                          "name = COALESCE(NULLIF(?, ''), name), picture = COALESCE(NULLIF(?, ''), picture) "
                          "WHERE id = ?", (email, name, picture, row["id"]))
                row = c.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
                return _public(row)
            user_id = f"usr-{uuid.uuid4().hex[:12]}"
            c.execute(
                "INSERT INTO users(id, username, role, created_at, provider, provider_sub, email, name, picture) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, f"{provider}:{sub}", role, datetime.now(timezone.utc).isoformat(),
                 provider, sub, email or None, name or None, picture or None))
            row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public(row)


user_service = UserService()
