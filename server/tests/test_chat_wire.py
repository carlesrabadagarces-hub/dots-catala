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
