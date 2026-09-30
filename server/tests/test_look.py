import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from app.routers import bots as bots_router
from app.services import catalog_service
from app.services.auth_service import auth_service
from app.services.catalog_data import CATALOG, META
from app.services.look import OPTIONS, sanitize_look, look_for_agent
from app.services.storage_service import StorageService


class LookTests(unittest.IsolatedAsyncioTestCase):
    def test_sanitize_drops_unknown_values_and_markup(self):
        look = sanitize_look({"shape": "star", "color": "red", "accent": "#ABCDEF", "hat": "<script>", "eyes": "heart"})
        self.assertEqual(look["shape"], "circle")
        self.assertEqual(look["color"], "#7a4cf0")
        self.assertEqual(look["accent"], "#abcdef")
        self.assertEqual(look["hat"], "none")
        self.assertEqual(look["eyes"], "heart")
        self.assertEqual(sanitize_look(None)["hat"], "none")

    def test_options_match_the_client_renderer(self):
        js = (Path(__file__).resolve().parents[2] / "client" / "lib" / "dotSvg.js").read_text(encoding="utf-8")
        block = js[js.index("export const OPTIONS"):js.index("export const PALETTE")]
        for key, values in OPTIONS.items():
            match = re.search(rf"{key}: \[(.*?)\]", block, re.S)
            self.assertIsNotNone(match, key)
            self.assertEqual(re.findall(r"'([^']+)'", match.group(1)), values, key)

    def test_every_catalogue_dot_has_a_valid_look(self):
        for spec in CATALOG + META:
            look = look_for_agent(spec["id"], spec["sector"])
            self.assertEqual(look, sanitize_look(look), spec["id"])
        self.assertEqual(look_for_agent("fontaner", "oficis")["hat"], "cap")

    async def test_bot_look_round_trip_and_catalogue_install(self):
        with tempfile.TemporaryDirectory() as d:
            storage = StorageService(Path(d))
            with patch.object(bots_router, "storage_service", storage), patch.object(catalog_service, "storage_service", storage):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5)),
                                             base_url="http://127.0.0.1") as c:
                    await c.post("/api/v1/auth/login", json={"token": auth_service.token})
                    made = (await c.post("/api/v1/bots", json={"name": "Lluna", "look": {"hat": "wizard", "color": "#ff4d7d", "x": 1}})).json()
                    self.assertEqual(made["look"]["hat"], "wizard")
                    self.assertNotIn("x", made["look"])
                    upd = (await c.put(f"/api/v1/bots/{made['id']}", json={"look": {"glasses": "monocle", "hat": "nope"}})).json()
                    self.assertEqual((upd["look"]["glasses"], upd["look"]["hat"]), ("monocle", "none"))
                    inst = (await c.post("/api/v1/catalog/cuiner/install")).json()
                    self.assertEqual(inst["look"]["hat"], "chef")


if __name__ == "__main__":
    unittest.main()
