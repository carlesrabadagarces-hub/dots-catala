"""Members created by social sign-in (Google, Apple)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.storage_service import storage_service

PUBLIC_FIELDS = ("id", "username", "role", "email", "name", "picture", "provider")


def _public(row) -> Dict[str, Any]:
    return {k: row[k] for k in PUBLIC_FIELDS}


class UserService:
    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        with storage_service.database.connect() as c:
            row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public(row) if row else None

    def upsert_social(self, provider: str, sub: str, email: str = "", name: str = "",
                      picture: str = "", email_verified: bool = False) -> Dict[str, Any]:
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
                "VALUES (?, ?, 'member', ?, ?, ?, ?, ?, ?)",
                (user_id, f"{provider}:{sub}", datetime.now(timezone.utc).isoformat(),
                 provider, sub, email or None, name or None, picture or None))
            row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public(row)


user_service = UserService()
