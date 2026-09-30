"""Inline client/lib/dotSvg.js into body.html so the page and the app draw identical Dots."""
import re
from pathlib import Path

here = Path(__file__).resolve().parent
src = (here.parent / "client" / "lib" / "dotSvg.js").read_text(encoding="utf-8")
src = re.sub(r"^export ", "", src, flags=re.M)
src = re.sub(r"^/\*.*?\*/\n", "", src, count=1, flags=re.S)
target = here / "body.html"
html = target.read_text(encoding="utf-8")
new, n = re.subn(r"/\*DOTSVG_START\*/.*?/\*DOTSVG_END\*/", lambda _: "/*DOTSVG_START*/\n" + src + "\n  /*DOTSVG_END*/", html, flags=re.S)
if n != 1:
    raise SystemExit("DOTSVG markers not found")
target.write_text(new, encoding="utf-8")
