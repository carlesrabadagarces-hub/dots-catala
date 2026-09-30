"""Catalogue of ready-made Dots, prompt assembly and AI-assisted agent creation."""

import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.catalog_data import CATALOG, META, SECTORS
from app.services.provider_service import provider_service
from app.services.storage_service import storage_service

REQUIRED_SPEC_FIELDS = ("name", "role", "persona", "expertise", "tasks")


class CatalogError(RuntimeError):
    pass


def build_prompt(spec: Dict[str, Any]) -> str:
    """Expand a compact spec into a complete system prompt with one shared method."""
    sector = SECTORS.get(spec.get("sector"), {})
    bullets = lambda items: "\n".join(f"- {x}" for x in items)
    safety = list(sector.get("safety", [])) + list(spec.get("safety", []))
    escalate = " ".join(x for x in (sector.get("escalate", ""), spec.get("escalate", "")) if x)
    return f"""Ets «{spec['name']}», un Dot de superDOTats. El teu rol: {spec['role']}. {spec['persona']}

IDIOMA I FORMAT
- Respons en català per defecte; si la persona escriu en un altre idioma, canvia a aquest.
- Parles per WhatsApp: text pla, frases curtes, com a molt uns 120 paraules. Llistes breus amb guions. Res de taules ni Markdown pesat.
- Si cal més detall, dona el resum i pregunta si vol ampliar-lo.

EXPERTESA
{bullets(spec['expertise'])}

QUÈ FAS
{bullets(spec['tasks'])}

MÈTODE (en totes les respostes)
1. Entén l'objectiu real. Si falta informació clau, fes com a màxim dues preguntes concretes abans de suposar res.
2. Raona pas a pas internament. Dona primer la conclusió o la recomanació i després el perquè.
3. Quan hi hagi decisions, ofereix dues o tres opcions amb avantatges i inconvenients, i digues quina triaries.
4. Distingeix el que saps del que suposes. Verifica xifres, dates, normativa i unitats. Si no n'estàs segur, digues-ho i explica com comprovar-ho. No inventis dades, fonts, lleis, preus ni cites.
5. Acaba amb el següent pas concret que pot fer la persona.
6. Abans de respondre, revisa mentalment que sigui correcte, clar, breu i útil. Si detectes un error teu en un missatge anterior, reconeix-lo i corregeix-lo.

LÍMITS I SEGURETAT
{bullets(safety)}
- Demana només les dades personals imprescindibles i no guardis informació sensible de tercers.
- Si la petició és il·legal, perillosa o fora del teu abast, digues-ho amb amabilitat i proposa una alternativa.

QUAN DERIVAR
{escalate or "Si el cas supera el que pots resoldre, recomana un professional qualificat."}

CONTEXT
- Àmbit per defecte: Catalunya, Espanya i la UE. Indica-ho si una resposta depèn del país o de la comunitat.
- Si t'adrecen missatges sense context, recorda breument què pots fer i ofereix tres exemples."""


def _sector_of(spec: Dict[str, Any]) -> Dict[str, Any]:
    return SECTORS.get(spec.get("sector"), {"name": "General", "color": "#7a4cf0"})


def public_view(spec: Dict[str, Any]) -> Dict[str, Any]:
    sector = _sector_of(spec)
    return {
        "id": spec["id"], "name": spec["name"], "role": spec["role"], "icon": spec["icon"],
        "sector": spec["sector"], "sector_name": sector["name"], "color": sector["color"],
        "starters": spec["starters"], "tasks": spec["tasks"][:3],
    }


def all_specs() -> List[Dict[str, Any]]:
    return CATALOG + META


def sectors() -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for spec in all_specs():
        counts[spec["sector"]] = counts.get(spec["sector"], 0) + 1
    return [{"id": k, "name": v["name"], "color": v["color"], "count": counts.get(k, 0)} for k, v in SECTORS.items()]


def list_catalog(sector: Optional[str] = None, query: str = "") -> List[Dict[str, Any]]:
    q = query.strip().lower()
    out = []
    for spec in all_specs():
        if sector and spec["sector"] != sector:
            continue
        haystack = " ".join([spec["name"], spec["role"], " ".join(spec["expertise"]), " ".join(spec["tasks"])]).lower()
        if q and q not in haystack:
            continue
        out.append(public_view(spec))
    return out


def get_spec(agent_id: str) -> Optional[Dict[str, Any]]:
    return next((s for s in all_specs() if s["id"] == agent_id), None)


def _bot_from_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": f"bot-{uuid.uuid4().hex[:6]}",
        "name": spec["name"],
        "role": spec["role"],
        "description": "; ".join(spec["tasks"][:3])[:240],
        "avatar": spec.get("icon", "🤖"),
        "model": storage_service.get_settings().get("default_model") or settings.DEFAULT_MODEL,
        "accent_color": _sector_of(spec)["color"],
        "system_prompt": build_prompt(spec),
        "tools": [],
        "pinned": False,
        "unread_count": 0,
        "created_at": datetime.now().isoformat(),
    }


def install(agent_id: str) -> Dict[str, Any]:
    from app.schemas.contracts import Bot

    spec = get_spec(agent_id)
    if not spec:
        raise CatalogError("Unknown Dot.")
    bot = Bot.model_validate(_bot_from_spec(spec)).model_dump()
    bots = storage_service.get_bots()
    bots.append(bot)
    storage_service.save_bots(bots)
    return bot


# ---- creation from a description -------------------------------------------------
GENERATOR_SYSTEM = """Ets un dissenyador expert d'agents d'IA. Reps la descripció d'una feina o d'un negoci i respons NOMÉS amb un objecte JSON vàlid (sense text al voltant) amb aquestes claus:
{"name": "nom curt de l'agent", "role": "ofici o rol precís", "persona": "una frase sobre el seu caràcter", "expertise": ["4 a 6 àrees de coneixement concretes"], "tasks": ["4 a 6 coses concretes que fa"], "safety": ["2 a 4 límits o precaucions específiques de l'àmbit"], "escalate": "quan cal derivar a una persona o servei", "starters": ["3 preguntes d'exemple"], "icon": "un únic emoji", "sector": "un de: educacio, salut, legal, oficis, negoci, hostaleria, tecnologia, vida, public, industria"}
Sigues específic i realista. Escriu en català."""


def _extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise CatalogError("The model did not return a valid design.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise CatalogError("The model did not return a valid design.") from exc


def normalise_spec(raw: Dict[str, Any]) -> Dict[str, Any]:
    for field in REQUIRED_SPEC_FIELDS:
        if not raw.get(field):
            raise CatalogError(f"The design is missing '{field}'.")
    as_list = lambda v: [str(x).strip() for x in (v if isinstance(v, list) else [v]) if str(x).strip()][:8]
    sector = raw.get("sector") if raw.get("sector") in SECTORS else "negoci"
    return {
        "sector": sector, "id": "custom",
        "name": str(raw["name"]).strip()[:60], "role": str(raw["role"]).strip()[:120],
        "icon": str(raw.get("icon") or "✨").strip()[:4] or "✨",
        "persona": str(raw["persona"]).strip()[:300],
        "expertise": as_list(raw["expertise"]), "tasks": as_list(raw["tasks"]),
        "starters": as_list(raw.get("starters", [])), "safety": as_list(raw.get("safety", [])),
        "escalate": str(raw.get("escalate", "")).strip()[:400],
    }


async def generate(description: str) -> Dict[str, Any]:
    """Design a new Dot from a plain-language description and install it."""
    from app.schemas.contracts import Bot

    description = description.strip()
    if len(description) < 8:
        raise CatalogError("Describe the Dot with a bit more detail.")
    text, ok = "", True
    async for event in provider_service.stream_chat_completion(
        model=storage_service.get_settings().get("default_model") or settings.DEFAULT_MODEL,
        messages=[{"role": "user", "content": description[:2000]}],
        system_prompt=GENERATOR_SYSTEM,
    ):
        if event["type"] == "content.delta":
            text += event["delta"]
        elif event["type"] == "turn.completed":
            ok = event.get("ok", True)
    if not ok or not text.strip():
        raise CatalogError("The model is not available right now.")
    spec = normalise_spec(_extract_json(text))
    bot = Bot.model_validate(_bot_from_spec(spec)).model_dump()
    bots = storage_service.get_bots()
    bots.append(bot)
    storage_service.save_bots(bots)
    return bot
