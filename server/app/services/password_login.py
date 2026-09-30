"""Password logins for testing: a shared member password and an admin password.

Local development (no PUBLIC_BASE_URL) defaults to 123456 and admin so the app
can be tried at once. A public deployment has no default: it must set
TEST_MEMBER_PASSWORD / ADMIN_PASSWORD, and passwords shorter than 8 characters
are refused unless ALLOW_WEAK_TEST_LOGINS=1.
"""

import re
import secrets
import time
from typing import Dict, List, Optional

from app.config import settings

DEV_MEMBER = "123456"
DEV_ADMIN = "admin"
MIN_LENGTH = 8
WINDOW = 60
MAX_FAILS = 6


def dev_mode() -> bool:
    return not settings.PUBLIC_BASE_URL and settings.HOST in {"127.0.0.1", "localhost", "::1"}


def _accept(password: str) -> str:
    if not password:
        return ""
    if len(password) < MIN_LENGTH and settings.ALLOW_WEAK_TEST_LOGINS not in {"1", "true", "yes"} and not dev_mode():
        return ""
    return password


def member_password() -> str:
    return _accept(settings.TEST_MEMBER_PASSWORD) or (DEV_MEMBER if dev_mode() and not settings.TEST_MEMBER_PASSWORD else "")


def admin_password() -> str:
    return _accept(settings.ADMIN_PASSWORD) or (DEV_ADMIN if dev_mode() and not settings.ADMIN_PASSWORD else "")


def enabled() -> Dict[str, bool]:
    return {"password": bool(member_password()), "admin": bool(admin_password())}


class RateLimiter:
    def __init__(self) -> None:
        self._fails: Dict[str, List[float]] = {}

    def blocked(self, key: str) -> bool:
        now = time.time()
        recent = [t for t in self._fails.get(key, []) if t > now - WINDOW]
        self._fails[key] = recent
        return len(recent) >= MAX_FAILS

    def fail(self, key: str) -> None:
        self._fails.setdefault(key, []).append(time.time())

    def clear(self, key: str) -> None:
        self._fails.pop(key, None)


limiter = RateLimiter()


def check(username: str, password: str) -> Optional[str]:
    """Return "admin", "member" or None."""
    if username.strip().lower() == "admin":
        expected = admin_password()
        return "admin" if expected and secrets.compare_digest(password, expected) else None
    expected = member_password()
    return "member" if expected and secrets.compare_digest(password, expected) else None


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")[:32] or "tester"
