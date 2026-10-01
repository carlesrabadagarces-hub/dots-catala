import asyncio
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.main import app
from app.services import whatsapp_service as wa_module
from app.services.auth_service import auth_service
from app.services.storage_service import StorageService
from app.services.whatsapp_service import WhatsAppService, split_text

SECRET = "app-secret"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def payload(sender="34600111222", text="Hola", msg_id="wamid.1", phone_id="123"):
    return {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": phone_id},
        "messages": [{"id": msg_id, "from": sender, "type": "text", "text": {"body": text}}],
    }}]}]}


class WhatsAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = StorageService(Path(self.directory.name))
        self.service = WhatsAppService()
        self.patches = [
            patch.object(wa_module, "storage_service", self.storage),
            patch("app.routers.whatsapp.whatsapp_service", self.service),
        ]
        for p in self.patches:
            p.start()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
            base_url="http://127.0.0.1",
        )
        await self.client.post("/api/v1/auth/login", json={"token": auth_service.token})
        bot_id = self.storage.get_bots()[0]["id"]
        self.conn = self.service.create({
            "bot_id": bot_id, "phone_number_id": "123", "access_token": "tok",
            "app_secret": SECRET, "allowed_numbers": ["+34 600 111 222"],
        })

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in self.patches:
            p.stop()
        self.directory.cleanup()

    def test_split_text(self):
        self.assertEqual(split_text("a b", 10), ["a b"])
        parts = split_text("word " * 50, 40)
        self.assertTrue(all(len(x) <= 40 for x in parts))

    def test_secrets_are_encrypted_and_hidden(self):
        raw = (Path(self.directory.name) / "whatsapp.json").read_text()
        self.assertNotIn("tok", json.loads(raw)[0]["access_token"])
        self.assertNotIn("access_token", self.conn)
        self.assertEqual(self.conn["allowed_numbers"], ["34600111222"])

    async def test_webhook_verification(self):
        url = f"/api/v1/whatsapp/webhook/{self.conn['id']}"
        ok = await self.client.get(url, params={
            "hub.mode": "subscribe", "hub.verify_token": self.conn["verify_token"], "hub.challenge": "42"})
        self.assertEqual((ok.status_code, ok.text), (200, "42"))
        bad = await self.client.get(url, params={
            "hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "42"})
        self.assertEqual(bad.status_code, 403)

    async def test_webhook_requires_valid_signature(self):
        # A fresh client without a session proves the path is public but signed.
        anon = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 2)),
                                 base_url="http://127.0.0.1")
        url = f"/api/v1/whatsapp/webhook/{self.conn['id']}"
        body = json.dumps(payload()).encode()
        bad = await anon.post(url, content=body, headers={"x-hub-signature-256": "sha256=00"})
        self.assertEqual(bad.status_code, 403)
        with patch.object(self.service, "handle_payload", new=AsyncMock()) as handler:
            good = await anon.post(url, content=body, headers={"x-hub-signature-256": sign(body)})
        self.assertEqual(good.status_code, 200)
        handler.assert_awaited_once()
        await anon.aclose()

    async def test_management_api_requires_auth(self):
        anon = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 3)),
                                 base_url="http://127.0.0.1")
        self.assertEqual((await anon.get("/api/v1/whatsapp/connections")).status_code, 401)
        await anon.aclose()

    async def test_allowed_sender_gets_reply_and_others_ignored(self):
        async def fake_stream(**kwargs):
            yield {"type": "content.delta", "delta": "Ei!"}
            yield {"type": "turn.completed", "ok": True}

        with patch.object(wa_module.provider_service, "stream_chat_completion", fake_stream), \
                patch.object(self.service, "send_text", new=AsyncMock()) as send:
            await self.service.handle_payload(self.conn["id"], payload())
            await self.service.handle_payload(self.conn["id"], payload(sender="34999", msg_id="wamid.2"))
            await self.service.handle_payload(self.conn["id"], payload(msg_id="wamid.1"))  # duplicate
        send.assert_awaited_once_with(self.conn["id"], "34600111222", "Ei!")
        thread = self.storage.get_messages(thread_id=f"{self.conn['id']}:34600111222")
        self.assertEqual([m["sender"] for m in thread], ["user", "bot"])


if __name__ == "__main__":
    unittest.main()


class DeliveryTests(WhatsAppTests):
    """One delivery is answered once, and a failed send is not lost."""

    @staticmethod
    def _stream(text="Ei!", ok=True):
        async def stream(**kwargs):
            yield {"type": "content.delta", "delta": text}
            yield {"type": "turn.completed", "ok": ok}
        return stream

    async def test_retry_is_ignored_even_after_a_restart(self):
        with patch.object(wa_module.provider_service, "stream_chat_completion", self._stream()), \
                patch.object(self.service, "send_text", new=AsyncMock()) as send:
            await self.service.handle_payload(self.conn["id"], payload())
            fresh = WhatsAppService()                    # as if the server had restarted
            with patch.object(fresh, "send_text", new=AsyncMock()) as send2:
                await fresh.handle_payload(self.conn["id"], payload())
            self.assertEqual(send.await_count, 1)
            self.assertEqual(send2.await_count, 0)

    async def test_a_failed_send_is_retried_and_stores_nothing(self):
        thread = f"{self.conn['id']}:34600111222"
        with patch.object(wa_module.provider_service, "stream_chat_completion", self._stream()), \
                patch.object(self.service, "send_text", new=AsyncMock(side_effect=RuntimeError("xarxa"))):
            await self.service.handle_payload(self.conn["id"], payload())
        self.assertEqual(self.storage.get_messages(thread_id=thread), [])

        with patch.object(wa_module.provider_service, "stream_chat_completion", self._stream()), \
                patch.object(self.service, "send_text", new=AsyncMock()) as send:
            await self.service.handle_payload(self.conn["id"], payload())   # the provider tries again
        send.assert_awaited_once()
        self.assertEqual([m["sender"] for m in self.storage.get_messages(thread_id=thread)], ["user", "bot"])

    async def test_two_messages_at_once_are_answered_in_turn(self):
        seen = []

        async def slow(**kwargs):
            seen.append([m["content"] for m in kwargs["messages"]])
            await asyncio.sleep(0.02)                    # long enough for the second to catch up
            yield {"type": "content.delta", "delta": "D'acord."}
            yield {"type": "turn.completed", "ok": True}

        with patch.object(wa_module.provider_service, "stream_chat_completion", slow), \
                patch.object(self.service, "send_text", new=AsyncMock()):
            await asyncio.gather(
                self.service.handle_payload(self.conn["id"], payload(text="Hola", msg_id="wamid.a")),
                self.service.handle_payload(self.conn["id"], payload(text="Tinc una fuita", msg_id="wamid.b")),
            )
        self.assertEqual(len(seen), 2)
        # The second turn was composed with the first already answered, not in parallel.
        self.assertEqual(seen[0], ["Hola"])
        self.assertEqual(seen[1], ["Hola", "D'acord.", "Tinc una fuita"])

    async def test_a_technical_excuse_is_not_remembered(self):
        thread = f"{self.conn['id']}:34600111222"
        with patch.object(wa_module.provider_service, "stream_chat_completion", self._stream(ok=False)), \
                patch.object(self.service, "send_text", new=AsyncMock()) as send:
            await self.service.handle_payload(self.conn["id"], payload())
        self.assertIn("no puc respondre", send.await_args.args[2])
        self.assertEqual(self.storage.get_messages(thread_id=thread), [])
