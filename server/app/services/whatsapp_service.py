"""WhatsApp integration through the official Meta WhatsApp Cloud API.

Each connection links one WhatsApp Business phone number (owned by whoever
registers it) to one Open Dots agent. Inbound messages arrive on a per-connection
webhook, are checked against the app secret signature and a sender allowlist,
answered by the agent, and sent back through the Graph API.
"""

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.services.provider_service import provider_service
from app.services.storage_service import storage_service

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
WHATSAPP_MAX_CHARS = 4000
HISTORY_LIMIT = 20
SECRET_FIELDS = ("access_token", "app_secret")


class WhatsAppError(RuntimeError):
    pass


def normalize_number(value: str) -> str:
    """Keep digits only, e.g. '+34 600 111 222' -> '34600111222'."""
    return "".join(ch for ch in str(value) if ch.isdigit())


def split_text(text: str, limit: int = WHATSAPP_MAX_CHARS) -> List[str]:
    text = text.strip()
    parts: List[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return parts


class WhatsAppService:
    def __init__(self) -> None:
        self._seen: List[str] = []

    # ---- storage -------------------------------------------------------
    @property
    def _path(self):
        return storage_service.data_dir / "whatsapp.json"

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, connections: List[Dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(connections, indent=2), encoding="utf-8")
        try:
            self._path.chmod(0o600)
        except OSError:
            pass

    def _reveal(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        revealed = dict(connection)
        for field in SECRET_FIELDS:
            revealed[field] = storage_service.secret_store.decrypt(connection[field])
        return revealed

    @staticmethod
    def public(connection: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in connection.items() if k not in SECRET_FIELDS}

    def list_connections(self) -> List[Dict[str, Any]]:
        return [self.public(c) for c in self._load()]

    def get(self, connection_id: str) -> Optional[Dict[str, Any]]:
        return next((c for c in self._load() if c["id"] == connection_id), None)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        bot_id = data["bot_id"]
        if not any(b["id"] == bot_id for b in storage_service.get_bots()):
            raise WhatsAppError("Unknown agent.")
        connection = {
            "id": f"wa-{uuid.uuid4().hex[:8]}",
            "bot_id": bot_id,
            "label": (data.get("label") or "WhatsApp").strip(),
            "phone_number_id": str(data["phone_number_id"]).strip(),
            "allowed_numbers": sorted({n for n in map(normalize_number, data.get("allowed_numbers", [])) if n}),
            "verify_token": secrets.token_urlsafe(24),
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        for field in SECRET_FIELDS:
            connection[field] = storage_service.secret_store.encrypt(str(data[field]).strip())
        connections = self._load()
        connections.append(connection)
        self._save(connections)
        return self.public(connection)

    def update(self, connection_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        connections = self._load()
        for connection in connections:
            if connection["id"] != connection_id:
                continue
            if "bot_id" in updates:
                if not any(b["id"] == updates["bot_id"] for b in storage_service.get_bots()):
                    raise WhatsAppError("Unknown agent.")
                connection["bot_id"] = updates["bot_id"]
            for field in ("label", "phone_number_id", "enabled"):
                if field in updates:
                    connection[field] = updates[field]
            if "allowed_numbers" in updates:
                connection["allowed_numbers"] = sorted(
                    {n for n in map(normalize_number, updates["allowed_numbers"]) if n}
                )
            for field in SECRET_FIELDS:
                if updates.get(field):
                    connection[field] = storage_service.secret_store.encrypt(str(updates[field]).strip())
            self._save(connections)
            return self.public(connection)
        return None

    def delete(self, connection_id: str) -> bool:
        connections = self._load()
        kept = [c for c in connections if c["id"] != connection_id]
        if len(kept) == len(connections):
            return False
        self._save(kept)
        return True

    # ---- webhook -------------------------------------------------------
    def verify_subscription(self, connection_id: str, mode: str, token: str) -> bool:
        connection = self.get(connection_id)
        return bool(
            connection
            and mode == "subscribe"
            and token
            and hmac.compare_digest(token, connection["verify_token"])
        )

    def valid_signature(self, connection_id: str, body: bytes, header: Optional[str]) -> bool:
        connection = self.get(connection_id)
        if not connection or not header or not header.startswith("sha256="):
            return False
        secret = self._reveal(connection)["app_secret"]
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, header[len("sha256="):])

    @staticmethod
    def extract_texts(payload: Dict[str, Any], phone_number_id: str) -> List[Dict[str, str]]:
        found = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("metadata", {}).get("phone_number_id") != phone_number_id:
                    continue
                for message in value.get("messages", []):
                    if message.get("type") == "text":
                        found.append({
                            "id": message.get("id", ""),
                            "from": normalize_number(message.get("from", "")),
                            "text": message.get("text", {}).get("body", ""),
                        })
        return found

    def _is_duplicate(self, message_id: str) -> bool:
        if not message_id:
            return False
        if message_id in self._seen:
            return True
        self._seen.append(message_id)
        del self._seen[:-500]
        return False

    async def handle_payload(self, connection_id: str, payload: Dict[str, Any]) -> None:
        connection = self.get(connection_id)
        if not connection or not connection.get("enabled", True):
            return
        for incoming in self.extract_texts(payload, connection["phone_number_id"]):
            if self._is_duplicate(incoming["id"]):
                continue
            # Deny by default: only numbers explicitly allowed can talk to the agent.
            if incoming["from"] not in connection["allowed_numbers"]:
                continue
            reply = await self.generate_reply(connection, incoming["from"], incoming["text"])
            if reply:
                await self.send_text(connection_id, incoming["from"], reply)

    async def generate_reply(self, connection: Dict[str, Any], sender: str, text: str) -> str:
        bot = next((b for b in storage_service.get_bots() if b["id"] == connection["bot_id"]), None)
        if not bot:
            return ""
        thread_id = f"{connection['id']}:{sender}"
        now = datetime.now(timezone.utc).isoformat()
        storage_service.add_message({
            "id": f"msg-{uuid.uuid4().hex[:8]}", "thread_id": thread_id, "bot_id": bot["id"],
            "sender": "user", "text": text, "created_at": now, "model": bot["model"],
            "item_type": "user_text",
        })
        history = [
            {"role": "user" if m["sender"] == "user" else "assistant", "content": m.get("text", "")}
            for m in storage_service.get_messages(thread_id=thread_id)
            if m["sender"] in ("user", "bot")
        ][-HISTORY_LIMIT:]
        system_prompt = (
            f"Current Date & Time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}.\n\n"
            f"{bot['system_prompt']}\n\n"
            "You are replying over WhatsApp: keep answers short and use plain text."
        )
        reply = ""
        ok = True
        async for event in provider_service.stream_chat_completion(
            model=bot["model"], messages=history, system_prompt=system_prompt
        ):
            if event["type"] == "content.delta":
                reply += event["delta"]
            elif event["type"] == "turn.completed":
                ok = event.get("ok", True)
        if not ok or not reply.strip():
            return "Ho sento, ara no puc respondre. Torna-ho a provar més tard."
        storage_service.add_message({
            "id": f"msg-{uuid.uuid4().hex[:8]}", "thread_id": thread_id, "bot_id": bot["id"],
            "sender": "bot", "text": reply, "created_at": datetime.now(timezone.utc).isoformat(),
            "model": bot["model"], "item_type": "assistant_text",
        })
        return reply

    async def send_text(self, connection_id: str, to: str, text: str) -> None:
        connection = self.get(connection_id)
        if not connection:
            raise WhatsAppError("Unknown connection.")
        token = self._reveal(connection)["access_token"]
        async with httpx.AsyncClient(timeout=20) as client:
            for part in split_text(text):
                response = await client.post(
                    f"{GRAPH_API_BASE}/{connection['phone_number_id']}/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {"body": part},
                    },
                )
                if response.status_code >= 400:
                    raise WhatsAppError(f"WhatsApp API error {response.status_code}")


whatsapp_service = WhatsAppService()
