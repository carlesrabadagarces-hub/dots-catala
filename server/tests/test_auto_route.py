import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services import memory_service, routing_service
from app.services import whatsapp_service as wa_module
from app.services.storage_service import StorageService
from app.services.whatsapp_service import WhatsAppService


def payload(text, msg_id, sender="34600111222", phone_id="123"):
    return {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": phone_id},
        "messages": [{"id": msg_id, "from": sender, "type": "text", "text": {"body": text}}],
    }}]}]}


class RoutingTests(unittest.TestCase):
    def test_routes_everyday_questions_to_the_right_dot(self):
        cases = {
            "La cisterna perd aigua constantment": "Fontaner",
            "Com presento la declaració de la renda si sóc autònom?": "Assessor fiscal",
            "No entenc les fraccions": "Professor de matemàtiques",
            "Quina recepta puc fer amb ous i patates?": "Cuiner",
            "El meu gos no menja": "Veterinari",
        }
        for text, name in cases.items():
            picked = routing_service.route(text)
            self.assertIsNotNone(picked, text)
            self.assertEqual(picked["name"], name, text)

    def test_small_talk_is_not_routed(self):
        self.assertIsNone(routing_service.route("Hola, bon dia"))
        self.assertIsNone(routing_service.route("gràcies!"))

    def test_sticky_dot_stays_for_follow_ups(self):
        self.assertEqual(routing_service.route("i quant trigarà?", "fontaner")["id"] if routing_service.route("i quant trigarà?", "fontaner") else "fontaner", "fontaner")
        # A clearly different topic switches Dot.
        self.assertEqual(routing_service.route("Ara necessito ajuda amb la declaració de la renda", "fontaner")["name"], "Assessor fiscal")


class MemoryTests(unittest.TestCase):
    def test_extracts_harmless_facts_only(self):
        self.assertIn("Es diu Marta.", memory_service.extract_facts("Hola, em dic marta i visc a Girona"))
        self.assertIn("Viu a Girona.", memory_service.extract_facts("Hola, em dic marta i visc a Girona"))
        self.assertEqual(memory_service.extract_facts("Tinc càncer i visc a Girona"), [])
        self.assertEqual(memory_service.extract_facts("Tinc una fuita"), [])

    def test_explicit_remember_keeps_what_was_asked(self):
        self.assertEqual(memory_service.extract_facts("Recorda que sóc al·lèrgic a la penicil·lina"),
                         ["sóc al·lèrgic a la penicil·lina."])


class AutoRouteWhatsAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = StorageService(Path(self.directory.name))
        self.service = WhatsAppService()
        self.patches = [patch.object(wa_module, "storage_service", self.storage),
                        patch.object(memory_service, "storage_service", self.storage),
                        patch("app.services.catalog_service.storage_service", self.storage)]
        for p in self.patches:
            p.start()
        self.conn = self.service.create({
            "auto_route": True, "phone_number_id": "123", "access_token": "tok",
            "app_secret": "s", "allowed_numbers": ["34600111222"]})

    async def asyncTearDown(self):
        for p in self.patches:
            p.stop()
        self.directory.cleanup()

    async def ask(self, text, msg_id):
        seen = {}

        async def fake_stream(**kwargs):
            seen["system"] = kwargs["system_prompt"]
            yield {"type": "content.delta", "delta": "Resposta."}
            yield {"type": "turn.completed", "ok": True}

        with patch.object(wa_module.provider_service, "stream_chat_completion", fake_stream), \
                patch.object(self.service, "send_text", new=AsyncMock()) as send:
            await self.service.handle_payload(self.conn["id"], payload(text, msg_id))
        reply = send.await_args.args[2] if send.await_args else None
        return reply, seen.get("system", "")

    async def test_connection_is_auto(self):
        self.assertTrue(self.conn["auto_route"])
        self.assertEqual(self.conn["bot_id"], "auto")

    async def test_first_message_is_routed_and_welcomed(self):
        reply, system = await self.ask("La cisterna perd aigua constantment", "w1")
        self.assertIn("Fontaner", system)
        self.assertIn("Sóc superDOTats", reply)
        self.assertIn("Fontaner:", reply)

    async def test_follow_up_keeps_the_dot_without_announcing_again(self):
        await self.ask("La cisterna perd aigua constantment", "w1")
        reply, system = await self.ask("i ara què faig amb el flotador?", "w2")
        self.assertIn("Fontaner", system)
        self.assertEqual(reply, "Resposta.")

    async def test_memory_is_used_and_can_be_erased(self):
        await self.ask("Hola, em dic Marta i visc a Girona. La cisterna perd aigua", "w1")
        _, system = await self.ask("i el flotador?", "w2")
        self.assertIn("Es diu Marta.", system)
        reply, _ = await self.ask("/memoria", "w3")
        self.assertIn("Viu a Girona.", reply)
        reply, _ = await self.ask("/oblida", "w4")
        self.assertIn("esborrat", reply)
        reply, _ = await self.ask("/memoria", "w5")
        self.assertIn("Encara no recordo res", reply)

    async def test_pick_and_auto_commands(self):
        reply, _ = await self.ask("/tria cuiner", "w1")
        self.assertIn("Cuiner", reply)
        reply, system = await self.ask("què faig amb això?", "w2")
        self.assertIn("Cuiner", system)
        reply, _ = await self.ask("/auto", "w3")
        self.assertIn("triaré el Dot", reply)

    async def test_unclear_first_message_gets_a_free_clarifying_answer(self):
        reply, system = await self.ask("hola", "w1")
        self.assertEqual(system, "")  # no model call
        self.assertIn("Sóc superDOTats", reply)


if __name__ == "__main__":
    unittest.main()


class RoutingQualityTests(unittest.TestCase):
    """A fixed set of real questions that must reach a sensible Dot.

    This is the safety net for the automatic router: every time the catalogue or the
    router changes, these questions must still land with the right Dot. Add a case
    here whenever someone reports a question that went to the wrong one.
    """

    CASES = __import__("json").loads((Path(__file__).parent / "data" / "routing_cases.json").read_text(encoding="utf-8"))

    def test_every_expected_dot_exists(self):
        from app.services.catalog_data import CATALOG
        known = {s["id"] for s in CATALOG}
        for case in self.CASES:
            for dot in case["ok"]:
                self.assertIn(dot, known, f"{case['q']!r} expects an unknown Dot {dot!r}")

    def test_questions_reach_a_sensible_dot(self):
        wrong = []
        for case in self.CASES:
            picked = routing_service.route(case["q"])
            got = picked["id"] if picked else None
            if got not in case["ok"]:
                wrong.append(f"{case['q']!r} -> {got} (esperat {case['ok']})")
        self.assertEqual(wrong, [], "Preguntes que han anat al Dot equivocat:\n  " + "\n  ".join(wrong))

    def test_a_translation_request_beats_the_topic_it_mentions(self):
        # «contrato» pulls towards a lawyer; «traducir» says what the job actually is
        self.assertEqual(routing_service.route("Necesito traducir un contrato al inglés")["id"], "traductor")

    def test_everyday_it_words_do_not_collide_with_body_parts(self):
        # «espatllat» used to match «espatlla» (shoulder) and sent the wifi to the physio
        self.assertEqual(routing_service.route("Se m'ha espatllat el wifi")["id"], "suport-informatic")
