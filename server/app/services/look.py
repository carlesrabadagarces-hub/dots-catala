"""Appearance of a Dot (shape, colours, face and accessories).

The lists must match OPTIONS in client/lib/dotSvg.js; a test keeps them in sync.
"""

import re
from typing import Any, Dict, Optional

OPTIONS = {
    "shape": ["circle", "tri", "drop", "hex", "arch", "square"],
    "eyes": ["pill", "round", "happy", "sleepy", "wide", "wink", "heart"],
    "mouth": ["none", "smile", "open", "smirk", "tongue"],
    "hat": ["none", "cap", "beanie", "tophat", "crown", "party", "cowboy", "wizard", "chef",
            "graduation", "hardhat", "antenna", "flower"],
    "glasses": ["none", "round", "square", "shades", "monocle", "visor"],
    "accessory": ["none", "bowtie", "tie", "scarf", "stethoscope", "headphones", "mustache", "blush",
                  "badge", "cape"],
}
DEFAULT = {"shape": "circle", "color": "#7a4cf0", "accent": "#0a0a0a", "eyes": "pill", "mouth": "none",
           "hat": "none", "glasses": "none", "accessory": "none"}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def sanitize_look(look: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Keep only known options and valid colours, so a look can never carry markup."""
    look = look if isinstance(look, dict) else {}
    clean: Dict[str, str] = {}
    for key, allowed in OPTIONS.items():
        value = look.get(key)
        clean[key] = value if value in allowed else DEFAULT[key]
    for key in ("color", "accent"):
        value = look.get(key)
        clean[key] = value.lower() if isinstance(value, str) and _HEX.match(value) else DEFAULT[key]
    return clean


# Profession props for catalogue Dots; the rest get a look from their sector.
AGENT_LOOKS = {
    "metge-capcalera": {"accessory": "stethoscope", "glasses": "round", "eyes": "pill", "mouth": "smile", "shape": "circle"},
    "infermer": {"accessory": "stethoscope", "hat": "cap", "accent": "#2fb5ff", "mouth": "smile"},
    "pediatre": {"accessory": "stethoscope", "eyes": "happy", "mouth": "smile", "hat": "beanie", "accent": "#ffc21a"},
    "psicoleg": {"glasses": "round", "eyes": "sleepy", "mouth": "smile", "accent": "#7a4cf0"},
    "dentista": {"hat": "cap", "accent": "#19c3a6", "mouth": "open", "eyes": "happy"},
    "veterinari": {"accessory": "stethoscope", "eyes": "round", "mouth": "tongue", "shape": "drop"},
    "mestra-infantil-primaria": {"hat": "flower", "eyes": "happy", "mouth": "smile", "accessory": "blush"},
    "professor-matematiques": {"glasses": "square", "hat": "graduation", "accent": "#0a0a0a"},
    "professor-llengues": {"glasses": "round", "hat": "beanie", "accent": "#ff4d7d", "eyes": "happy"},
    "professor-ciencies": {"glasses": "round", "eyes": "wide", "mouth": "open", "hat": "antenna"},
    "professor-idiomes": {"hat": "cap", "accent": "#2f7bff", "eyes": "wink", "mouth": "smile"},
    "professor-musica": {"accessory": "headphones", "eyes": "happy", "mouth": "smile"},
    "tutor-tfg": {"hat": "graduation", "glasses": "round"},
    "jurista-generalista": {"accessory": "tie", "glasses": "square", "accent": "#0a0a0a"},
    "assessor-fiscal": {"accessory": "tie", "glasses": "square", "accent": "#19c3a6", "eyes": "round"},
    "laboralista": {"accessory": "tie", "hat": "hardhat"},
    "jurista-penal": {"accessory": "tie", "glasses": "shades", "mouth": "smirk"},
    "fontaner": {"hat": "cap", "accent": "#2f7bff", "accessory": "mustache", "eyes": "round"},
    "electricista": {"hat": "hardhat", "eyes": "wide", "mouth": "open"},
    "paleta-reformes": {"hat": "hardhat", "accessory": "mustache"},
    "fuster": {"hat": "cap", "accent": "#c47a3a", "accessory": "mustache"},
    "pintor": {"hat": "beanie", "accent": "#ff8a3d", "eyes": "happy"},
    "mecanic": {"hat": "cap", "accent": "#ff4d7d", "accessory": "mustache"},
    "jardiner": {"hat": "cowboy", "accent": "#7c5a2a", "eyes": "happy", "mouth": "smile"},
    "cuiner": {"hat": "chef", "accessory": "mustache", "eyes": "happy", "mouth": "smile"},
    "sommelier": {"accessory": "bowtie", "glasses": "monocle", "accent": "#7a1e3c", "mouth": "smirk"},
    "panader-pastisser": {"hat": "chef", "accessory": "blush", "eyes": "happy", "mouth": "smile"},
    "programador": {"glasses": "square", "accessory": "headphones", "eyes": "pill"},
    "ciberseguretat": {"glasses": "shades", "hat": "beanie", "accent": "#0a0a0a", "mouth": "smirk"},
    "creador-de-dots": {"hat": "wizard", "eyes": "heart", "mouth": "smile", "accent": "#ffc21a"},
    "recepcionista": {"accessory": "bowtie", "eyes": "happy", "mouth": "smile", "hat": "cap", "accent": "#ff4d7d"},
    "comercial-vendes": {"accessory": "tie", "glasses": "shades", "mouth": "smirk"},
    "consultor-emprenedoria": {"hat": "crown", "eyes": "wink", "mouth": "smile"},
    "assistent-personal": {"accessory": "headphones", "eyes": "happy", "mouth": "smile"},
    "guia-catalunya": {"hat": "cap", "accent": "#ff4d7d", "eyes": "happy", "mouth": "smile", "accessory": "scarf"},
    "agronom": {"hat": "cowboy", "accent": "#c4a15a"},
    "logistica": {"hat": "hardhat", "accessory": "badge"},
    "prl": {"hat": "hardhat", "accessory": "badge", "eyes": "wide"},
}
SECTOR_BASES = {
    "educacio": {"shape": "arch", "color": "#ffc21a"}, "salut": {"shape": "tri", "color": "#ff4d7d"},
    "legal": {"shape": "square", "color": "#52657a"}, "oficis": {"shape": "drop", "color": "#ff8a3d"},
    "negoci": {"shape": "drop", "color": "#2f7bff"}, "hostaleria": {"shape": "hex", "color": "#19c3a6"},
    "tecnologia": {"shape": "circle", "color": "#7a4cf0"}, "vida": {"shape": "circle", "color": "#2fb5ff"},
    "public": {"shape": "square", "color": "#6b7cff"}, "industria": {"shape": "hex", "color": "#7cd13b"},
}


def look_for_agent(agent_id: str, sector: str) -> Dict[str, str]:
    base = SECTOR_BASES.get(sector, {})
    return sanitize_look({**base, **AGENT_LOOKS.get(agent_id, {})})
