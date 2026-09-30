"""Per-contact memory: a few facts the person shared, so Dots stop asking the same thing.

Privacy by design: automatic capture is limited to harmless facts (name, city, family,
work, language). Health, religion, politics or finances are never captured automatically;
they are only stored when the person explicitly says "recorda que …". The person can list
(/memoria) and erase (/oblida) everything at any time.
"""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.services.context import current_owner
from app.services.storage_service import storage_service

MAX_FACTS = 20
MAX_LEN = 160
SENSITIVE = re.compile(
    r"\b(malaltia|enfermedad|diagnos|c[aà]ncer|cancer|vih|sida|depressi|ansiet|embar[aà]s|embaraz|medicaci|"
    r"religi|musulm|cristi|jueu|polític|politic|vot[oa]|partit|orientaci|gai|lesbi|trans\b|"
    r"targeta|tarjeta|iban|contrasenya|password|dni|nie|passaport|pasaporte|salari|sueldo|deute|deuda)\b", re.I)


def _norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


# (regex on accent-free lowercase text, template). Group 1 is the captured value.
PATTERNS = [
    (re.compile(r"\b(?:em dic|me llamo|mi nombre es|my name is)\s+([a-z]{2,20})\b"), "Es diu {}."),
    (re.compile(r"\b(?:visc a|vivo en|vivo a|i live in)\s+([a-z' .-]{2,30}?)(?:[,.;!?]|$| i | y | pero | però )"), "Viu a {}."),
    (re.compile(r"\b(?:tinc|tengo|i have)\s+(un|una|dos|dues|tres|quatre|cuatro|\d)\s+(fills?|filles?|hijos?|hijas?|children|kids)\b"), "Té {} {}."),
    (re.compile(r"\bsoc\s+(autonom|autonoma|jubilat|jubilada|estudiant|funcionari|funcionaria|mestre|mestra|professor|professora)\b"), "És {}."),
    (re.compile(r"\bsoy\s+(autonomo|autonoma|jubilado|jubilada|estudiante|funcionario|funcionaria|maestro|maestra|profesor|profesora)\b"), "És {}."),
    (re.compile(r"\btinc\s+(\d{1,2})\s+anys\b"), "Té {} anys."),
    (re.compile(r"\btengo\s+(\d{1,2})\s+anos\b"), "Té {} anys."),
    (re.compile(r"\b(?:vull que em parlis en|prefereixo (?:que em parlis )?en|habla(?:me)? en)\s+(catala|castella|angles|espanol|ingles)\b"), "Prefereix parlar en {}."),
]
EXPLICIT = re.compile(r"^\s*(?:recorda(?:'t)?|recuerda|remember)(?: que| that)?\s+(.{3,})$", re.I | re.S)


def extract_facts(text: str) -> List[str]:
    """Facts to remember from one message. Sensitive content is skipped unless explicit."""
    out: List[str] = []
    m = EXPLICIT.match(text.strip())
    if m:
        fact = m.group(1).strip().rstrip(".") + "."
        return [fact[:MAX_LEN]]
    low = _norm(text.lower())
    if SENSITIVE.search(low):
        return []
    same = len(low) == len(text)
    for rx, tpl in PATTERNS:
        mm = rx.search(low)
        if not mm:
            continue
        # Prefer the original spelling (accents, capitals) when the text kept its length.
        groups = [(text[mm.start(i):mm.end(i)] if same else mm.group(i)).strip() for i in range(1, (mm.lastindex or 0) + 1) if mm.group(i)]
        if tpl.startswith("Es diu"):
            groups = [groups[0][:1].upper() + groups[0][1:]]
        out.append(tpl.format(*groups)[:MAX_LEN])
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_facts(contact: str) -> List[str]:
    with storage_service.database.connect() as c:
        rows = c.execute("SELECT fact FROM contact_memory WHERE owner_id = ? AND contact = ? ORDER BY id",
                         (current_owner.get(), contact)).fetchall()
    return [r["fact"] for r in rows]


def remember(contact: str, facts: List[str], source: str = "auto") -> List[str]:
    """Store new facts (deduplicated, capped). Returns those actually added."""
    existing = list_facts(contact)
    seen = {_norm(f.lower()) for f in existing}
    added: List[str] = []
    with storage_service.database.connect() as c:
        for f in facts:
            key = _norm(f.lower())
            if not f or key in seen:
                continue
            if len(existing) + len(added) >= MAX_FACTS:
                c.execute("DELETE FROM contact_memory WHERE id = (SELECT MIN(id) FROM contact_memory "
                          "WHERE owner_id = ? AND contact = ?)", (current_owner.get(), contact))
            c.execute("INSERT INTO contact_memory(owner_id, contact, fact, source, created_at) VALUES (?, ?, ?, ?, ?)",
                      (current_owner.get(), contact, f, source, _now()))
            seen.add(key)
            added.append(f)
    return added


def forget(contact: str) -> int:
    with storage_service.database.connect() as c:
        cur = c.execute("DELETE FROM contact_memory WHERE owner_id = ? AND contact = ?", (current_owner.get(), contact))
        c.execute("DELETE FROM contact_state WHERE owner_id = ? AND contact = ?", (current_owner.get(), contact))
    return cur.rowcount


def prompt_block(contact: str) -> str:
    facts = list_facts(contact)
    if not facts:
        return ""
    return ("QUÈ SAPS D'AQUESTA PERSONA (ho ha dit ella; fes-ho servir amb naturalitat i no ho repeteixis si no cal):\n"
            + "\n".join(f"- {f}" for f in facts))


# ---- which Dot is talking to this contact (sticky routing) ----
def get_dot(contact: str) -> Optional[str]:
    with storage_service.database.connect() as c:
        row = c.execute("SELECT dot_id FROM contact_state WHERE owner_id = ? AND contact = ?",
                        (current_owner.get(), contact)).fetchone()
    return row["dot_id"] if row else None


def set_dot(contact: str, dot_id: Optional[str]) -> None:
    with storage_service.database.connect() as c:
        c.execute("INSERT INTO contact_state(owner_id, contact, dot_id, updated_at) VALUES (?, ?, ?, ?) "
                  "ON CONFLICT(owner_id, contact) DO UPDATE SET dot_id = excluded.dot_id, updated_at = excluded.updated_at",
                  (current_owner.get(), contact, dot_id, _now()))
