import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from app.routers import auth as auth_router, bots as bots_router
from app.services import password_login, usage_service, user_service as user_module
from app.services.context import current_owner, current_channel
from app.services.provider_service import provider_service
from app.services.storage_service import StorageService
from app.services.user_service import UserService


class AdminAndUsageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(Path(self.dir.name))
        self.patches = [patch.object(m, "storage_service", self.storage)
                        for m in (user_module, usage_service, auth_router, bots_router)]
        self.patches.append(patch("app.services.provider_service.storage_service", self.storage))
        for p in self.patches:
            p.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("9.9.9.9", 1)),
                                        base_url="http://api.test")
        password_login.limiter._fails.clear()

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in self.patches:
            p.stop()
        self.dir.cleanup()

    async def login(self, username, password):
        return await self.client.post("/api/v1/auth/login/password", json={"username": username, "password": password})

    async def test_dev_defaults_and_wrong_password(self):
        self.assertTrue(password_login.dev_mode())
        self.assertEqual((await self.login("Anna", "123456")).status_code, 200)
        self.assertEqual((await self.login("Anna", "nope")).status_code, 401)
        self.assertEqual((await self.login("admin", "admin")).json()["user"]["role"], "admin")

    async def test_public_deployment_has_no_default_passwords(self):
        with patch("app.config.settings.PUBLIC_BASE_URL", "https://api.example.org"):
            self.assertFalse(password_login.enabled()["password"])
            self.assertEqual((await self.login("Anna", "123456")).status_code, 401)
            with patch("app.config.settings.TEST_MEMBER_PASSWORD", "abc"):
                self.assertFalse(password_login.enabled()["password"])  # too short
            with patch("app.config.settings.TEST_MEMBER_PASSWORD", "long-enough-pass"):
                self.assertEqual((await self.login("Anna", "long-enough-pass")).status_code, 200)

    async def test_rate_limit(self):
        for _ in range(6):
            await self.login("x", "bad")
        self.assertEqual((await self.login("x", "123456")).status_code, 429)

    async def test_members_cannot_see_admin_stats_but_admin_can(self):
        await self.login("Anna", "123456")
        self.assertEqual((await self.client.get("/api/v1/admin/stats")).status_code, 403)
        self.client.cookies.clear()
        await self.login("admin", "admin")
        r = await self.client.get("/api/v1/admin/stats")
        self.assertEqual(r.status_code, 200)
        self.assertIn("totals", r.json())

    async def test_usage_is_recorded_and_aggregated(self):
        async def fake_raw(self_, model, messages, system_prompt=""):
            yield {"type": "content.delta", "delta": "Hola, sóc un Dot."}
            yield {"type": "turn.completed", "ok": True}

        await self.login("Anna", "123456")
        me = (await self.client.get("/api/v1/auth/status")).json()["user"]
        token = current_owner.set(me["id"])
        try:
            with patch.object(type(provider_service), "_stream_raw", fake_raw):
                out = [e async for e in provider_service.stream_chat_completion("m1", [{"role": "user", "content": "Hola"}], "sys")]
        finally:
            current_owner.reset(token)
        self.assertEqual(out[-1]["type"], "turn.completed")
        self.client.cookies.clear()
        await self.login("admin", "admin")
        stats = (await self.client.get("/api/v1/admin/stats")).json()
        self.assertEqual(stats["totals"]["requests"], 1)
        self.assertGreater(stats["totals"]["tokens_out"], 0)
        self.assertEqual(stats["by_model"][0]["model"], "m1")
        self.assertEqual(stats["by_channel"][0]["channel"], "web")
        anna = next(u for u in stats["users"] if u["id"] == me["id"])
        self.assertEqual(anna["requests"], 1)
        self.assertEqual(anna["dots"], 1)

    async def test_quota_and_suspension_are_enforced(self):
        await self.login("Anna", "123456")
        me = (await self.client.get("/api/v1/auth/status")).json()["user"]
        self.client.cookies.clear()
        await self.login("admin", "admin")
        r = await self.client.patch(f"/api/v1/admin/users/{me['id']}", json={"token_limit": 1})
        self.assertEqual(r.json()["token_limit"], 1)
        usage_service.record(me["id"], "b", "m", "web", 5, 5, 10, True)
        self.assertIn("límit", usage_service.quota_status(me["id"]))
        r = await self.client.patch(f"/api/v1/admin/users/{me['id']}", json={"disabled": True})
        self.assertTrue(r.json()["disabled"])
        self.client.cookies.clear()
        self.assertEqual((await self.login("Anna", "123456")).status_code, 403)
        # admins cannot be suspended
        admin = (await self.login("admin", "admin")).json()["user"]
        self.assertEqual((await self.client.patch(f"/api/v1/admin/users/{admin['id']}", json={"disabled": True})).status_code, 400)


if __name__ == "__main__":
    unittest.main()
