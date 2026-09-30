"""Automatic Dot routing: pick the best catalogue Dot for a free-text question.

Deterministic and free (no model call): the message is matched against each Dot's
name, role, expertise, tasks and starter questions, weighting rare words more
(IDF). Words are compared by accent-free stems so "fuites" matches "fuita".
"""

import math
import re
import unicodedata
from typing import Any, Dict, List, Optional

from app.services.catalog_data import CATALOG

STOP = set("""
a al als amb aquest aquesta aixo això com de del dels el els en es et hi i la les li lo me mi mis mes més molt no o per pero però que què qui quin quina quins quines se sense si sí son són te tinc tens tenim un una uns unes vull vols volem puc pots podem ho ha han hem
el la los las un una unos unas de del al y o que como para por con sin mi mis tu tus su sus es son soy eres estoy esta está estan hay tengo quiero puedo necesito
the a an and or of to in on for with is are i my me you can how what do does
ajuda ajudar ajuda'm ajudam ajudame ayuda hola bon dia bona tarda nit gracies gràcies gracias
""".split())

# Words people use that the catalogue words do not contain.
ALIASES = {
    "aixeta": "fontaner canonada fuita", "cisterna": "fontaner fuita", "canonada": "fontaner", "grifo": "fontaner fuita",
    "gotera": "fontaner fuita", "desguas": "fontaner", "calentador": "fontaner gas",
    "llum": "electricista", "enchufe": "electricista", "endoll": "electricista", "quadre": "electricista", "cortocircuito": "electricista",
    "irpf": "assessor fiscal renda", "renda": "assessor fiscal", "hisenda": "assessor fiscal", "iva": "assessor fiscal",
    "declaracio": "assessor fiscal", "declaracion": "assessor fiscal", "autonom": "assessor fiscal", "autonomo": "assessor fiscal", "factura": "assessor fiscal",
    "dolor": "metge salut", "febre": "metge salut", "fiebre": "metge salut", "mal": "metge", "tos": "metge", "grip": "metge",
    "pastilla": "farmaceutic", "medicament": "farmaceutic", "medicamento": "farmaceutic",
    "deures": "professor mestra", "deberes": "professor mestra", "fraccions": "professor matematiques", "equacio": "professor matematiques",
    "examen": "professor tutor", "suspendre": "professor", "traduir": "traductor", "traduce": "traductor", "traducir": "traductor idiomes", "traducio": "traductor", "translate": "traductor",
    "recepta": "cuiner", "receta": "cuiner", "sopar": "cuiner", "cenar": "cuiner", "menjar": "cuiner nutricionista", "dieta": "nutricionista",
    "lloguer": "advocat jurista", "alquiler": "advocat jurista", "contracte": "jurista", "contrato": "jurista", "multa": "jurista", "desnonament": "jurista",
    "divorci": "advocat", "divorcio": "advocat", "herencia": "advocat notari", "hipoteca": "assessor financer",
    "cv": "recursos humans", "curriculum": "recursos humans", "feina": "recursos humans", "trabajo": "recursos humans", "entrevista": "recursos humans",
    "gos": "veterinari", "gat": "veterinari", "perro": "veterinari", "gato": "veterinari", "mascota": "veterinari",
    "ansietat": "psicoleg", "ansiedad": "psicoleg", "estres": "psicoleg", "trist": "psicoleg", "depressio": "psicoleg",
    "sticker": "creador stickers", "stickers": "creador stickers",
    "viatge": "guia viatges", "viaje": "guia viatges", "vacances": "guia viatges", "hotel": "guia viatges",
    "web": "desenvolupador", "programar": "desenvolupador", "codi": "desenvolupador", "excel": "consultor",
}


def _strip(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _stem(word: str) -> str:
    return word[:5] if len(word) > 5 else word


def tokens(text: str) -> List[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", _strip(text.replace("·", ""))):
        if len(w) < 3 or w in STOP:
            continue
        out.append(_stem(w))
        alias = ALIASES.get(w)
        if alias:
            out.extend(_stem(a) for a in alias.split())
    return out


class _Index:
    def __init__(self) -> None:
        self.docs: List[Dict[str, Any]] = []
        df: Dict[str, int] = {}
        for spec in CATALOG:
            fields = {
                "name": tokens(spec["name"] + " " + spec["id"].replace("-", " ")),
                "role": tokens(spec["role"]),
                "expertise": tokens(" ".join(spec["expertise"])),
                "tasks": tokens(" ".join(spec["tasks"])),
                "starters": tokens(" ".join(spec["starters"])),
            }
            self.docs.append({"spec": spec, "fields": fields})
            for w in {t for f in fields.values() for t in f}:
                df[w] = df.get(w, 0) + 1
        n = len(self.docs)
        self.idf = {w: math.log((n + 1) / (c + 0.5)) + 0.3 for w, c in df.items()}


_INDEX: Optional[_Index] = None
WEIGHTS = {"name": 3.0, "role": 2.5, "expertise": 2.0, "starters": 1.5, "tasks": 1.0}


def _index() -> _Index:
    global _INDEX
    if _INDEX is None:
        _INDEX = _Index()
    return _INDEX


def rank(text: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Best Dots for the text, each with a 0..1 confidence."""
    idx = _index()
    q = tokens(text)
    if not q:
        return []
    scored = []
    for d in idx.docs:
        s = 0.0
        for w in set(q):
            best = max((WEIGHTS[f] for f, toks in d["fields"].items() if w in toks), default=0.0)
            if best:
                s += best * idx.idf.get(w, 0.5)
        scored.append((s, d["spec"]))
    scored.sort(key=lambda x: -x[0])
    top = scored[0][0]
    if top <= 0:
        return []
    total = sum(s for s, _ in scored[:5]) or 1.0
    out = []
    for s, spec in scored[:limit]:
        if s <= 0:
            break
        out.append({"id": spec["id"], "name": spec["name"], "role": spec["role"], "icon": spec["icon"],
                    "score": round(s, 2), "confidence": round(min(1.0, (s / total) * min(1.0, top / 6.0) * 1.6), 2)})
    return out


def _score_of(text: str, dot_id: str) -> float:
    idx = _index()
    q = set(tokens(text))
    for d in idx.docs:
        if d["spec"]["id"] == dot_id:
            return sum(max((WEIGHTS[f] for f, toks in d["fields"].items() if w in toks), default=0.0) * idx.idf.get(w, 0.5) for w in q)
    return 0.0


SWITCH_MIN = 12.0  # a follow-up must clearly point elsewhere before we change Dot


def route(text: str, current_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Pick a Dot. Stay with the current one unless another clearly fits better."""
    ranked = rank(text, limit=3)
    if not ranked:
        return None
    best = ranked[0]
    if not current_id:
        return best if best["confidence"] >= 0.2 else None
    if best["id"] == current_id:
        return best
    cur_score = _score_of(text, current_id)
    if best["score"] >= max(SWITCH_MIN, cur_score * 1.6) and best["confidence"] >= 0.4:
        return best
    return None  # keep the current Dot
