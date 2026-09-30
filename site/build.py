"""Assemble body.html: inline the shared Dot libraries and site/src/app.js into its <script>."""
import re
from pathlib import Path

here = Path(__file__).resolve().parent
lib = here.parent / "client" / "lib"


def strip_exports(text):
    text = re.sub(r"^import .*?;\n", "", text, flags=re.M)
    text = re.sub(r"^export ", "", text, flags=re.M)
    return re.sub(r"^/\*.*?\*/\n", "", text, count=1, flags=re.S)


life = strip_exports((lib / "dotLife.js").read_text(encoding="utf-8"))
data = strip_exports((lib / "dotSpriteData.js").read_text(encoding="utf-8"))
sprite = strip_exports((lib / "dotSprite.js").read_text(encoding="utf-8"))
libs = (
    "var __life = (function () {\n" + life + "\nreturn { attachLife: attachLife };\n})();\nvar attachLife = __life.attachLife;\n"
    "var __sprite = (function () {\n" + data + "\n" + sprite +
    "\nreturn { dotSprite: dotSprite, spriteParts: spriteParts, spriteLayout: spriteLayout, normalizeSpriteLook: normalizeSpriteLook, BODIES: BODIES, TONES: TONES, TONE_COLORS: TONE_COLORS, SPRITE_ITEMS: SPRITE_ITEMS, ensureSpriteStyles: ensureSpriteStyles, randomSpriteLook: randomSpriteLook };\n})();\n"
    "var dotSprite = __sprite.dotSprite, spriteParts = __sprite.spriteParts, spriteLayout = __sprite.spriteLayout, normalizeSpriteLook = __sprite.normalizeSpriteLook, BODIES = __sprite.BODIES, TONES = __sprite.TONES, TONE_COLORS = __sprite.TONE_COLORS, SPRITE_ITEMS = __sprite.SPRITE_ITEMS, ensureSpriteStyles = __sprite.ensureSpriteStyles, randomSpriteLook = __sprite.randomSpriteLook;\n"
)
# The rig metadata for the footer walkers travels inside the page: a fetch would not
# work when the file is opened straight from disk, and it is only a few numbers.
rig = (here / "people" / "rig.json")
libs += "var RIG = " + (rig.read_text(encoding="utf-8").strip() if rig.exists() else "{}") + ";\n"
app = (here / "src" / "app.js").read_text(encoding="utf-8")
target = here / "body.html"
html = target.read_text(encoding="utf-8")
new, n = re.subn(r"(<script>\n)(?:(?!</script>).)*?(</script>\s*)$", lambda m: m.group(1) + libs + app + "\n" + m.group(2), html, flags=re.S)
if n != 1:
    raise SystemExit("main <script> block not found")
target.write_text(new, encoding="utf-8")
