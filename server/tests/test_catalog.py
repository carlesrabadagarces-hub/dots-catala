import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from app.services import catalog_service
from app.services.auth_service import auth_service
from app.services.catalog_data import CATALOG, META, SECTORS
from app.services.storage_service import StorageService
from app.routers import bots as bots_router


class CatalogContentTests(unittest.TestCase):
    def test_every_sector_is_covered_and_ids_are_unique(self):
        specs = CATALOG + META
        ids = [s["id"] for s in specs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(specs), 70)
        self.assertEqual({s["sector"] for s in specs}, set(SECTORS))
        for sector in SECTORS:
            self.assertGreaterEqual(sum(1 for s in specs if s["sector"] == sector), 3, sector)

    def test_every_spec_builds_a_complete_prompt(self):
        for spec in CATALOG + META:
            with self.subTest(spec["id"]):
                self.assertGreaterEqual(len(spec["expertise"]), 3)
                self.assertGreaterEqual(len(spec["tasks"]), 3)
                self.assertEqual(len(spec["starters"]), 3)
                prompt = catalog_service.build_prompt(spec)
                for section in ("IDIOMA I FORMAT", "EXPERTESA", "QUÈ FAS", "MÈTODE", "LÍMITS I SEGURETAT", "QUAN DERIVAR"):
                    self.assertIn(section, prompt)
                self.assertIn(spec["name"], prompt)
                self.assertLess(len(prompt), 6000)

    def test_sensitive_sectors_carry_their_safety_rules(self):
        health = catalog_service.build_prompt(catalog_service.get_spec("metge-capcalera"))
        self.assertIn("112", health)
        self.assertIn("no diagnostiques", health)
        legal = catalog_service.build_prompt(catalog_service.get_spec("assessor-fiscal"))
        self.assertIn("no inventis", legal.lower())

    def test_search_and_filter(self):
        self.assertTrue(all(a["sector"] == "salut" for a in catalog_service.list_catalog("salut")))
        names = [a["name"] for a in catalog_service.list_catalog(query="fontaner")]
        self.assertIn("Fontaner", names)


class CatalogApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(Path(self.dir.name))
        self.patches = [patch.object(catalog_service, "storage_service", self.storage),
                        patch.object(bots_router, "storage_service", self.storage)]
        for p in self.patches:
            p.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 9)),
                                        base_url="http://127.0.0.1")
        await self.client.post("/api/v1/auth/login", json={"token": auth_service.token})

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in self.patches:
            p.stop()
        self.dir.cleanup()

    async def test_list_sectors_and_install(self):
        sectors = (await self.client.get("/api/v1/catalog/sectors")).json()
        self.assertEqual({s["id"] for s in sectors}, set(SECTORS))
        listing = (await self.client.get("/api/v1/catalog", params={"sector": "oficis"})).json()
        self.assertTrue(listing and all(a["sector"] == "oficis" for a in listing))
        before = len(self.storage.get_bots())
        r = await self.client.post("/api/v1/catalog/fontaner/install")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "Fontaner")
        self.assertIn("MÈTODE", r.json()["system_prompt"])
        self.assertEqual(len(self.storage.get_bots()), before + 1)
        self.assertEqual((await self.client.post("/api/v1/catalog/no-existeix/install")).status_code, 404)

    async def test_generate_from_description(self):
        design = """Aquí tens:
```json
{"name": "Anna de la Gestoria", "role": "Assistent de gestoria", "persona": "Ordenada i amable.",
 "expertise": ["IVA", "IRPF", "Autònoms"], "tasks": ["Recordar terminis", "Explicar models", "Ordenar factures"],
 "safety": ["No inventis imports"], "escalate": "Consulta el gestor.", "starters": ["a", "b", "c"],
 "icon": "🧾", "sector": "legal"}
```"""

        async def fake_stream(**kwargs):
            yield {"type": "content.delta", "delta": design}
            yield {"type": "turn.completed", "ok": True}

        with patch.object(catalog_service.provider_service, "stream_chat_completion", fake_stream):
            r = await self.client.post("/api/v1/catalog/generate",
                                       json={"description": "Un agent per a la meva gestoria petita"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["name"], "Anna de la Gestoria")
        self.assertIn("IVA", r.json()["system_prompt"])
        self.assertIn("MÈTODE", self.storage.get_bots()[-1]["system_prompt"])

    async def test_generate_rejects_bad_model_output(self):
        async def bad_stream(**kwargs):
            yield {"type": "content.delta", "delta": "no és JSON"}
            yield {"type": "turn.completed", "ok": True}

        with patch.object(catalog_service.provider_service, "stream_chat_completion", bad_stream):
            r = await self.client.post("/api/v1/catalog/generate", json={"description": "Un agent per a una botiga"})
        self.assertEqual(r.status_code, 502)
        short = await self.client.post("/api/v1/catalog/generate", json={"description": "curt"})
        self.assertEqual(short.status_code, 422)


if __name__ == "__main__":
    unittest.main()
