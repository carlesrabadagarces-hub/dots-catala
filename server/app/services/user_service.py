"""Members created by social sign-in (Google, Apple)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.storage_service import storage_service

PUBLIC_FIELDS = ("id", "username", "role", "email", "name", "picture", "provider", "disabled", "token_limit")


def _public(row) -> Dict[str, Any]:
    data = {k: row[k] for k in PUBLIC_FIELDS}
    data["disabled"] = bool(data["disabled"])
    return data


class UserService:
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
                row = c.execute("SELECT * FROM users WHERE lower(email) = lower(?) AND provider IS NOT NULL",
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
