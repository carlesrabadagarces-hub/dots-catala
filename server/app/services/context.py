"""Request-scoped owner identity.

The auth middleware sets the owner for the duration of a request; storage reads
and writes are then scoped to that owner. Outside a request (start-up, tests)
the single local owner is used.
"""

from contextvars import ContextVar

DEFAULT_OWNER_ID = "local-user"
current_owner: ContextVar[str] = ContextVar("current_owner", default=DEFAULT_OWNER_ID)

# Where a model call comes from: "web", "whatsapp" or "generate".
current_channel: ContextVar[str] = ContextVar("current_channel", default="web")
current_bot: ContextVar[str] = ContextVar("current_bot", default="")
