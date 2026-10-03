import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.services import provider_service as ps
from app.services.provider_service import ModelProviderService


def sse(*chunks):
    lines = [f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n" for c in chunks]
    return "".join(lines) + "data: [DONE]\n\n"


class ChatWireTests(unittest.IsolatedAsyncioTestCase):
    async def run_wire(self, handler, messages=None):
        real = httpx.AsyncClient
        transport = httpx.MockTransport(handler)
        with patch.object(ps.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw)):
            out = []
            async for e in ModelProviderService()._stream_chat(
                    "https://api.groq.com/openai/v1", "sk-test", "llama-3.3-70b-versatile",
                    messages or [{"role": "user", "content": "hola"}], "Ets un Dot.", {}):
                out.append(e)
        return out

    async def test_streams_text_and_sends_openai_shaped_request(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["auth"] = request.headers["authorization"]
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, text=sse("Ho", "la!"))

        events = await self.run_wire(handler)
        self.assertEqual(seen["url"], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer sk-test")
        self.assertEqual(seen["body"]["messages"][0], {"role": "system", "content": "Ets un Dot."})
        self.assertEqual("".join(e.get("delta", "") for e in events), "Hola!")
        self.assertTrue(events[-1]["ok"])

    async def test_friendly_errors_do_not_leak_upstream_bodies(self):
        for status, expect in ((401, "clau"), (429, "límit"), (404, "model")):
            events = await self.run_wire(lambda r, s=status: httpx.Response(s, text="secret-upstream-body"))
            text = events[0]["delta"]
            self.assertIn(expect, text)
            self.assertNotIn("secret-upstream-body", text)
            self.assertFalse(events[-1]["ok"])

    async def test_empty_answer_is_reported_as_failure(self):
        events = await self.run_wire(lambda r: httpx.Response(200, text="data: [DONE]\n\n"))
        self.assertFalse(events[-1]["ok"])


class RetargetTests(unittest.TestCase):
    def test_dots_follow_the_new_provider_models(self):
        from app.services.storage_service import StorageService
        with tempfile.TemporaryDirectory() as d:
            st = StorageService(Path(d))
            bots = st.get_bots()
            for b in bots:
                b["model"] = "gpt-5-mini"
            if bots:
                bots[-1]["model"] = "llama-3.3-70b-versatile"
            st.save_bots(bots)
            n = st.retarget_bot_models(["llama-3.3-70b-versatile"], "llama-3.3-70b-versatile")
            self.assertEqual(n, max(len(bots) - 1, 0))
            self.assertTrue(all(b["model"] == "llama-3.3-70b-versatile" for b in st.get_bots()))


class ProviderModelsTests(unittest.IsolatedAsyncioTestCase):
    async def test_lists_models_from_the_saved_provider(self):
        from app.routers import settings as settings_router
        seen = {}

        def handler(request):
            seen["url"], seen["auth"] = str(request.url), request.headers["authorization"]
            return httpx.Response(200, json={"data": [{"id": "b-model"}, {"id": "a-model"}]})

        real = httpx.AsyncClient
        fake = type("S", (), {"get_settings": lambda self: {"model_api_key": "k", "model_api_base_url": "https://x.test/v1/"}})()
        with patch.object(settings_router, "storage_service", fake), \
             patch.object(settings_router.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)):
            out = await settings_router.provider_models()
        self.assertEqual(out["models"], ["a-model", "b-model"])
        self.assertEqual(seen["url"], "https://x.test/v1/models")
        self.assertEqual(seen["auth"], "Bearer k")
