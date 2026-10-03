import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from app.routers import auth as auth_router, bots as bots_router
from app.services import password_login, usage_service, user_service as user_module
from app.services.storage_service import StorageService
from app.services.user_service import user_service


class SignupTests(unittest.IsolatedAsyncioTestCase):
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

    def signup(self, email="ana@example.com", password="correct-horse", name="Ana"):
        return self.client.post("/api/v1/auth/register", json={"email": email, "password": password, "name": name})

    async def test_register_logs_in_and_can_log_back_in(self):
        res = await self.signup()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["role"], "member")
        self.assertNotIn("password_hash", res.json()["user"])
        status = (await self.client.get("/api/v1/auth/status")).json()
        self.assertTrue(status["authenticated"])
        await self.client.post("/api/v1/auth/logout")
        self.client.cookies.clear()
        ok = await self.client.post("/api/v1/auth/login/password",
                                    json={"username": "ANA@example.com", "password": "correct-horse"})
        self.assertEqual(ok.status_code, 200)
        self.client.cookies.clear()
        bad = await self.client.post("/api/v1/auth/login/password",
                                     json={"username": "ana@example.com", "password": "wrong-password"})
        self.assertEqual(bad.status_code, 401)

    async def test_rejects_bad_email_short_password_and_duplicates(self):
        self.assertEqual((await self.signup(email="nope")).status_code, 400)
        self.assertEqual((await self.signup(password="short")).status_code, 400)
        self.assertEqual((await self.signup()).status_code, 200)
        self.assertEqual((await self.signup(password="another-password")).status_code, 400)

    async def test_signup_can_be_closed(self):
        with patch.object(auth_router.settings, "SIGNUP_OPEN", "0"):
            self.assertEqual((await self.signup()).status_code, 403)
            status = (await self.client.get("/api/v1/auth/status")).json()
            self.assertFalse(status["providers"]["signup"])

    async def test_each_member_is_separate_and_cannot_become_admin(self):
        a = (await self.signup("a@example.com")).json()["user"]
        b = (await self.signup("b@example.com")).json()["user"]
        self.assertNotEqual(a["id"], b["id"])
        with patch.object(auth_router.settings, "ADMIN_EMAILS", "a@example.com"):
            self.client.cookies.clear()
            res = await self.client.post("/api/v1/auth/login/password",
                                         json={"username": "a@example.com", "password": "correct-horse"})
            self.assertEqual(res.json()["user"]["role"], "member")

    async def test_google_sign_in_never_merges_into_a_password_account(self):
        # Someone registers with a victim's email; the victim later uses Google.
        mine = user_service.register_password("victim@example.com", "attacker-pass", "x")
        google = user_service.upsert_social("google", "g-123", "victim@example.com", "Victim", "", True)
        self.assertNotEqual(mine["id"], google["id"])

    async def test_suspended_account_cannot_log_in(self):
        made = (await self.signup()).json()["user"]
        user_service.set_controls(made["id"], disabled=True)
        self.client.cookies.clear()
        res = await self.client.post("/api/v1/auth/login/password",
                                     json={"username": "ana@example.com", "password": "correct-horse"})
        self.assertEqual(res.status_code, 403)

    async def test_signup_is_throttled(self):
        codes = [(await self.signup(email=f"u{i}@example.com")).status_code for i in range(8)]
        self.assertIn(429, codes)
