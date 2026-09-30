import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.main import app
from app.routers import auth as auth_router
from app.services import user_service as user_module, whatsapp_service as wa_module
from app.services.auth_service import SESSION_COOKIE, auth_service
from app.services.context import current_owner
from app.services.oauth_service import BINDING_COOKIE, OAuthError, oauth_service
from app.services.storage_service import StorageService
from app.services.user_service import UserService
from app.services.whatsapp_service import WhatsAppService
from app.routers import bots as bots_router


class SocialLoginTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(Path(self.dir.name))
        self.patches = [
            patch.object(user_module, "storage_service", self.storage),
            patch.object(auth_router, "storage_service", self.storage),
            patch.object(bots_router, "storage_service", self.storage),
            patch("app.config.settings.GOOGLE_CLIENT_ID", "gid"),
            patch("app.config.settings.GOOGLE_CLIENT_SECRET", "gsecret"),
            patch("app.config.settings.FRONTEND_URL", "http://front.test"),
        ]
        for p in self.patches:
            p.start()
        self.users = UserService()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("1.2.3.4", 1)),
                                        base_url="http://api.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in self.patches:
            p.stop()
        self.dir.cleanup()

    async def test_providers_and_local_login_switch(self):
        status = (await self.client.get("/api/v1/auth/status")).json()
        self.assertTrue(status["providers"]["google"])
        self.assertFalse(status["providers"]["apple"])
        self.assertFalse(status["providers"]["local"])  # a provider is configured
        denied = await self.client.post("/api/v1/auth/login", json={"token": auth_service.token})
        self.assertEqual(denied.status_code, 401)

    async def test_start_redirects_to_google_with_state_and_binding_cookie(self):
        r = await self.client.get("/api/v1/auth/oauth/google/start")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["location"].startswith("https://accounts.google.com/"))
        self.assertIn("client_id=gid", r.headers["location"])
        self.assertIn(BINDING_COOKIE, r.headers["set-cookie"])
        self.assertEqual((await self.client.get("/api/v1/auth/oauth/apple/start")).status_code, 404)

    def test_state_is_signed_and_expires(self):
        state = oauth_service.make_state("google", "n1")
        self.assertEqual(oauth_service.read_state(state, "google")["n"], "n1")
        with self.assertRaises(OAuthError):
            oauth_service.read_state(state[:-2] + "aa", "google")
        with self.assertRaises(OAuthError):
            oauth_service.read_state(state, "apple")
        with patch("time.time", return_value=time.time() + 1000):
            with self.assertRaises(OAuthError):
                oauth_service.read_state(state, "google")

    async def _login(self, sub, email):
        nonce = "nonce-" + sub
        state = oauth_service.make_state("google", nonce)
        self.client.cookies.set(BINDING_COOKIE, oauth_service.binding(nonce))
        claims = {"sub": sub, "email": email, "email_verified": True, "name": "Ada " + sub, "nonce": nonce}
        with patch.object(oauth_service, "exchange_code", new=AsyncMock(return_value="idt")), \
                patch.object(oauth_service, "verify_id_token", new=AsyncMock(return_value=claims)):
            return await self.client.get("/api/v1/auth/oauth/google/callback",
                                         params={"code": "c", "state": state})

    async def test_callback_creates_member_session_and_starter_dot(self):
        r = await self._login("g-1", "ada@example.com")
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "http://front.test/")
        me = (await self.client.get("/api/v1/auth/status")).json()
        self.assertTrue(me["authenticated"])
        self.assertEqual(me["user"]["email"], "ada@example.com")
        bots = (await self.client.get("/api/v1/bots")).json()
        self.assertEqual([b["name"] for b in bots], ["El meu primer Dot"])

    async def test_members_only_see_their_own_dots(self):
        await self._login("g-1", "a@example.com")
        created = await self.client.post("/api/v1/bots", json={"name": "Secret A"})
        self.assertEqual(created.status_code, 200)
        self.client.cookies.delete(SESSION_COOKIE)
        await self._login("g-2", "b@example.com")
        names = [b["name"] for b in (await self.client.get("/api/v1/bots")).json()]
        self.assertNotIn("Secret A", names)
        self.assertEqual(len(names), 1)
        # B cannot delete A's bot either
        a_id = created.json()["id"]
        self.assertEqual((await self.client.delete(f"/api/v1/bots/{a_id}")).status_code, 404)

    async def test_same_verified_email_links_accounts(self):
        a = self.users.upsert_social("google", "g-1", "same@example.com", "A", "", True)
        b = self.users.upsert_social("apple", "ap-9", "same@example.com", "", "", True)
        self.assertEqual(a["id"], b["id"])
        c = self.users.upsert_social("apple", "ap-10", "same@example.com", "", "", False)
        self.assertNotEqual(a["id"], c["id"])

    async def test_binding_cookie_is_required(self):
        state = oauth_service.make_state("google", "n")
        self.client.cookies.delete(BINDING_COOKIE)
        r = await self.client.get("/api/v1/auth/oauth/google/callback", params={"code": "c", "state": state})
        self.assertEqual(r.status_code, 303)
        self.assertIn("login_error", r.headers["location"])

    async def test_tampered_session_cookie_is_rejected(self):
        await self._login("g-1", "a@example.com")
        good = self.client.cookies.get(SESSION_COOKIE)
        self.client.cookies.clear()
        self.client.cookies.set(SESSION_COOKIE, good[:-1] + ("0" if good[-1] != "0" else "1"), domain="api.test")
        self.assertEqual((await self.client.get("/api/v1/bots")).status_code, 401)

    async def test_whatsapp_connections_are_private_to_their_owner(self):
        wa = WhatsAppService()
        with patch.object(wa_module, "storage_service", self.storage):
            t = current_owner.set("usr-a")
            try:
                self.storage.seed_owner()
                bot = self.storage.get_bots()[0]["id"]
                conn = wa.create({"bot_id": bot, "phone_number_id": "1", "access_token": "t", "app_secret": "s"})
                self.assertEqual(len(wa.list_connections()), 1)
            finally:
                current_owner.reset(t)
            t = current_owner.set("usr-b")
            try:
                self.assertEqual(wa.list_connections(), [])
                self.assertIsNone(wa.update(conn["id"], {"label": "x"}))
                self.assertFalse(wa.delete(conn["id"]))
            finally:
                current_owner.reset(t)

    async def test_apple_client_secret_and_form_post_url(self):
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        with patch("app.config.settings.APPLE_CLIENT_ID", "com.example.web"), \
                patch("app.config.settings.APPLE_TEAM_ID", "TEAM123456"), \
                patch("app.config.settings.APPLE_KEY_ID", "KEY1234567"), \
                patch("app.config.settings.APPLE_PRIVATE_KEY", pem):
            self.assertTrue(oauth_service.enabled()["apple"])
            secret = oauth_service.apple_client_secret()
            claims = jwt.decode(secret, key.public_key(), algorithms=["ES256"], audience="https://appleid.apple.com")
            self.assertEqual((claims["iss"], claims["sub"]), ("TEAM123456", "com.example.web"))
            self.assertEqual(jwt.get_unverified_header(secret)["kid"], "KEY1234567")
            r = await self.client.get("/api/v1/auth/oauth/apple/start")
            self.assertIn("response_mode=form_post", r.headers["location"])


if __name__ == "__main__":
    unittest.main()
