"""WhatsApp integration through the official Meta WhatsApp Cloud API.

Each connection links one WhatsApp Business phone number (owned by whoever
registers it) to one Open Dots agent. Inbound messages arrive on a per-connection
webhook, are checked against the app secret signature and a sender allowlist,
answered by the agent, and sent back through the Graph API.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.services import memory_service, routing_service
from app.services.context import DEFAULT_OWNER_ID, current_bot, current_channel, current_owner
from app.services.provider_service import provider_service
from app.services.storage_service import storage_service

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
WHATSAPP_MAX_CHARS = 4000
HISTORY_LIMIT = 20
SECRET_FIELDS = ("access_token", "app_secret")
AUTO = "auto"  # connection mode: the Dot is chosen per message
EVENT_TTL_DAYS = 7      # how long a handled delivery is remembered
SWEEP_EVERY = 3600      # seconds between clean-ups of that record

logger = logging.getLogger(__name__)


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
        self._locks: Dict[str, asyncio.Lock] = {}
        self._swept = 0.0

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
        out = {k: v for k, v in connection.items() if k not in SECRET_FIELDS}
        # The address to paste into Meta. Without PUBLIC_BASE_URL we cannot know the
        # server's address from here, so the interface explains what to do instead.
        base = settings.PUBLIC_BASE_URL
        out["webhook_url"] = f"{base}/api/v1/whatsapp/webhook/{connection['id']}" if base else ""
        return out

    @staticmethod
    def _mine(connection: Dict[str, Any]) -> bool:
        return connection.get("owner_id", DEFAULT_OWNER_ID) == current_owner.get()

    def list_connections(self) -> List[Dict[str, Any]]:
        return [self.public(c) for c in self._load() if self._mine(c)]

    def get(self, connection_id: str) -> Optional[Dict[str, Any]]:
        return next((c for c in self._load() if c["id"] == connection_id), None)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        auto = bool(data.get("auto_route")) or data.get("bot_id") in (None, "", AUTO)
        bot_id = AUTO if auto else data["bot_id"]
        if not auto and not any(b["id"] == bot_id for b in storage_service.get_bots()):
            raise WhatsAppError("Unknown agent.")
        connection = {
            "id": f"wa-{uuid.uuid4().hex[:8]}",
            "owner_id": current_owner.get(),
            "bot_id": bot_id,
            "auto_route": auto,
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
            if connection["id"] != connection_id or not self._mine(connection):
                continue
            if updates.get("auto_route") or updates.get("bot_id") == AUTO:
                connection["bot_id"] = AUTO
                connection["auto_route"] = True
            elif "bot_id" in updates:
                if not any(b["id"] == updates["bot_id"] for b in storage_service.get_bots()):
                    raise WhatsAppError("Unknown agent.")
                connection["bot_id"] = updates["bot_id"]
                connection["auto_route"] = False
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
        kept = [c for c in connections if c["id"] != connection_id or not self._mine(c)]
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

    # ---- one delivery, once ---------------------------------------------
    # Meta expects a 2xx within five seconds and retries the same event up to
    # seven times, so the same message does arrive more than once. The record of
    # what we have handled lives in the database: in memory it would be lost on
    # every restart, and the person would get the same answer twice.
    def claim_event(self, event_id: str, connection_id: str) -> bool:
        """Take charge of this delivery. False when someone already did."""
        if not event_id:
            return True
        self._sweep_events()
        try:
            with storage_service.database.connect() as c:
                c.execute("INSERT INTO whatsapp_events(event_id, connection_id, created_at) VALUES (?, ?, ?)",
                          (event_id, connection_id, datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError:
            return False
        return True

    def release_event(self, event_id: str) -> None:
        """Give the delivery back so the provider's retry is answered.

        Used when we claimed a message but could not deliver the reply: without
        this the retry looks like a duplicate and the person is never answered.
        """
        if not event_id:
            return
        with storage_service.database.connect() as c:
            c.execute("DELETE FROM whatsapp_events WHERE event_id = ?", (event_id,))

    def _sweep_events(self) -> None:
        now = time.monotonic()
        if now - self._swept < SWEEP_EVERY:
            return
        self._swept = now
        cutoff = (datetime.now(timezone.utc) - timedelta(days=EVENT_TTL_DAYS)).isoformat()
        with storage_service.database.connect() as c:
            c.execute("DELETE FROM whatsapp_events WHERE created_at < ?", (cutoff,))

    def _lock(self, connection_id: str, sender: str) -> asyncio.Lock:
        """One lock per person.

        People send "hi" and then the real question a moment later. Answering both
        at once means two turns read the same history and reply over each other.
        """
        key = f"{connection_id}:{sender}"
        lock = self._locks.get(key)
        if lock is None:
            lock = self._locks[key] = asyncio.Lock()
        if len(self._locks) > 500:
            for k, held in list(self._locks.items()):
                if k != key and not held.locked():
                    del self._locks[k]
        return lock

    async def handle_payload(self, connection_id: str, payload: Dict[str, Any]) -> None:
        connection = self.get(connection_id)
        if not connection or not connection.get("enabled", True):
            return
        # Webhooks carry no session: act as the member who owns this connection.
        token = current_owner.set(connection.get("owner_id", DEFAULT_OWNER_ID))
        ch_token = current_channel.set("whatsapp")
        bot_token = current_bot.set(connection["bot_id"])
        try:
            for incoming in self.extract_texts(payload, connection["phone_number_id"]):
                # Deny by default: only numbers explicitly allowed can talk to the agent.
                if incoming["from"] not in connection["allowed_numbers"]:
                    continue
                if not self.claim_event(incoming["id"], connection_id):
                    continue
                async with self._lock(connection_id, incoming["from"]):
                    await self._answer(connection, incoming)
        finally:
            current_bot.reset(bot_token)
            current_channel.reset(ch_token)
            current_owner.reset(token)

    WELCOME = (
        "Hola! Sóc superDOTats. Escriu-me el teu dubte (una fuita, la renda, una recepta, una carta…) "
        "i et poso amb el Dot adequat.\n"
        "Recordo el que em diguis de tu (nom, ciutat, família) perquè no ho hagis de repetir. "
        "/memoria ho mostra i /oblida ho esborra. /ajuda per veure les ordres."
    )
    HELP = (
        "Ordres:\n- /dots: alguns Dots que et poden ajudar\n- /tria <nom>: parlar amb un Dot concret (p. ex. /tria fontaner)\n"
        "- /auto: torno a triar-lo jo segons el que preguntis\n- /memoria: el que recordo de tu\n- /oblida: esborro tot el que sé de tu"
    )

    @staticmethod
    def _find_spec(name: str) -> Optional[Dict[str, Any]]:
        from app.services.catalog_data import CATALOG

        needle = routing_service._strip(name.strip().lower())
        if not needle:
            return None
        exact = [s for s in CATALOG if routing_service._strip(s["name"].lower()) == needle]
        part = [s for s in CATALOG if needle in routing_service._strip(s["name"].lower())]
        return (exact or part or [None])[0]

    def _command(self, sender: str, text: str) -> Optional[str]:
        """Handle /commands. Returns the reply, or None when the text is not a command."""
        raw = text.strip()
        if not raw.startswith("/"):
            return None
        cmd, _, arg = raw[1:].partition(" ")
        cmd = cmd.lower()
        if cmd in ("ajuda", "help", "ayuda", "start"):
            return self.HELP
        if cmd == "dots":
            from app.services.catalog_data import CATALOG

            sample = ["fontaner", "metge-capcalera", "assessor-fiscal", "professor-matematiques", "cuiner", "traductor",
                      "jurista-generalista", "veterinari", "psicoleg", "creador-stickers"]
            names = [f"{s['icon']} {s['name']}" for s in CATALOG if s["id"] in sample]
            return "Alguns Dots que et poden ajudar:\n" + "\n".join(names) + f"\n…i {len(CATALOG) - len(names)} més. Escriu el dubte i el triaré jo, o fes /tria <nom>."
        if cmd == "auto":
            memory_service.set_dot(sender, None)
            return "Fet. A partir d'ara triaré el Dot segons el que em preguntis."
        if cmd in ("tria", "elige", "pick"):
            spec = self._find_spec(arg)
            if not spec:
                return "No he trobat aquest Dot. Prova /dots per veure'n alguns."
            memory_service.set_dot(sender, spec["id"])
            return f"{spec['icon']} Ara et respon {spec['name']}. Digues-me el teu dubte. (/auto per tornar a la tria automàtica)"
        if cmd in ("memoria", "memòria", "memory"):
            facts = memory_service.list_facts(sender)
            if not facts:
                return "Encara no recordo res de tu. Pots dir-me «recorda que…» i ho anoto."
            return "Això és el que recordo de tu:\n" + "\n".join(f"- {f}" for f in facts) + "\n/oblida ho esborra tot."
        if cmd in ("oblida", "olvida", "forget"):
            n = memory_service.forget(sender)
            return "Ja he esborrat tot el que sabia de tu." if n else "No tenia res guardat de tu."
        return None

    def _resolve_bot(self, connection: Dict[str, Any], sender: str, text: str):
        """The Dot that answers: the fixed one, or (auto mode) the best match for this message."""
        if not connection.get("auto_route"):
            bot = next((b for b in storage_service.get_bots() if b["id"] == connection["bot_id"]), None)
            return bot, None
        from app.config import settings
        from app.services.catalog_service import build_prompt, get_spec

        current = memory_service.get_dot(sender)
        picked = routing_service.route(text, current)
        spec = get_spec(picked["id"]) if picked else (get_spec(current) if current else None)
        if not spec:
            return None, None
        memory_service.set_dot(sender, spec["id"])
        model = storage_service.get_settings().get("default_model") or settings.DEFAULT_MODEL
        bot = {"id": f"auto:{spec['id']}", "name": spec["name"], "model": model, "system_prompt": build_prompt(spec)}
        current_bot.set(bot["id"])  # usage accounting sees the Dot that really answers
        return bot, {"changed": spec["id"] != current, "icon": spec["icon"], "name": spec["name"]}

    async def _answer(self, connection: Dict[str, Any], incoming: Dict[str, str]) -> None:
        """Answer one message. Nothing is stored until the person has it."""
        try:
            reply, turn = await self.prepare_reply(connection, incoming["from"], incoming["text"])
            if not reply:
                return
            await self.send_text(connection["id"], incoming["from"], reply)
        except Exception:
            self.release_event(incoming["id"])   # let the provider's retry try again
            logger.exception("WhatsApp: could not answer %s", incoming["from"])
            return
        if turn:
            self.remember_turn(turn)

    @staticmethod
    def remember_turn(turn: Dict[str, Any]) -> None:
        """Write the exchange down, now that it really happened."""
        for who, text, kind in (("user", turn["text"], "user_text"), ("bot", turn["reply"], "assistant_text")):
            storage_service.add_message({
                "id": f"msg-{uuid.uuid4().hex[:8]}", "thread_id": turn["thread_id"], "bot_id": turn["bot_id"],
                "sender": who, "text": text, "created_at": datetime.now(timezone.utc).isoformat(),
                "model": turn["model"], "item_type": kind,
            })

    async def prepare_reply(self, connection: Dict[str, Any], sender: str,
                            text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Work out the answer, and the turn to store once it has been sent."""
        reply = self._command(sender, text)
        if reply is not None:
            return reply, None
        first_time = not memory_service.list_facts(sender) and memory_service.get_dot(sender) is None
        explicit = memory_service.EXPLICIT.match(text.strip())
        facts = memory_service.extract_facts(text)
        if facts:
            memory_service.remember(sender, facts, "explicit" if explicit else "auto")
        if explicit:
            return "Anotat ✅ " + (facts[0] if facts else "") + " (/memoria per veure-ho, /oblida per esborrar-ho)", None
        bot, info = self._resolve_bot(connection, sender, text)
        if not bot:
            if connection.get("auto_route"):
                return (self.WELCOME if first_time else
                        "Explica'm una mica més què necessites, per exemple: «tinc una fuita a la cisterna» o «com faig la declaració de la renda».",
                        None)
            return "", None
        thread_id = f"{connection['id']}:{sender}"
        history = [
            {"role": "user" if m["sender"] == "user" else "assistant", "content": m.get("text", "")}
            for m in storage_service.get_messages(thread_id=thread_id)
            if m["sender"] in ("user", "bot")
        ][-(HISTORY_LIMIT - 1):]
        history.append({"role": "user", "content": text})
        memory = memory_service.prompt_block(sender)
        system_prompt = (
            f"Current Date & Time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}.\n\n"
            f"{bot['system_prompt']}\n\n"
            + (f"{memory}\n\n" if memory else "")
            + "You are replying over WhatsApp: keep answers short and use plain text."
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
            # A technical excuse is not a turn of the conversation: storing it would
            # leave it polluting the context of everything that comes after.
            return "Ho sento, ara no puc respondre. Torna-ho a provar més tard.", None
        turn = {"thread_id": thread_id, "bot_id": bot["id"], "model": bot["model"], "text": text, "reply": reply}
        if info and info["changed"]:
            reply = f"{info['icon']} {info['name']}:\n{reply}"
        if first_time and connection.get("auto_route"):
            reply = f"{self.WELCOME}\n\n{reply}"
        return reply, turn

    async def send_test(self, connection_id: str, to: str) -> None:
        """Send one message so the person can see the connection really works."""
        number = normalize_number(to)
        if not number:
            raise WhatsAppError("Falta el número de destinació.")
        connection = self.get(connection_id)
        if connection and number not in connection["allowed_numbers"]:
            raise WhatsAppError("Aquest número no és a la llista de números permesos.")
        await self.send_text(connection_id, number,
                             "Prova de superDOTats ✅ La connexió funciona. Escriu-me quan vulguis.")

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
