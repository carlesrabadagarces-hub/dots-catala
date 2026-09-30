"""Inline the sprite libraries into explainer.src.html -> explainer.html (used by render_explainer.py)."""
import re
from pathlib import Path

here = Path(__file__).resolve().parent
lib = here.parent.parent / "client" / "lib"


def strip(text):
    text = re.sub(r"^import .*?;\n", "", text, flags=re.M)
    text = re.sub(r"^export ", "", text, flags=re.M)
    return re.sub(r"^/\*.*?\*/\n", "", text, count=1, flags=re.S)


code = strip((lib / "dotSpriteData.js").read_text(encoding="utf-8")) + "\n" + strip((lib / "dotSprite.js").read_text(encoding="utf-8"))
html = (here / "explainer.src.html").read_text(encoding="utf-8").replace("/*LIBS*/", code)
(here / "explainer.html").write_text(html, encoding="utf-8")
