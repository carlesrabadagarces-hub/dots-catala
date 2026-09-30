"""Logo = our blue Dot (plush blob). Writes brand/logo-*.png, the site favicon and the app icons.
Run:  python brand/make_logo.py
"""

import base64
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image

from build_art import RAW, bbox, strip_shadow  # noqa: E402

ROOT = Path(__file__).resolve().parent
SRC = RAW / "bodies" / "blob-blue.png"


def square(img, size, pad=0.06):
    img = img.crop(bbox(img))
    k = size * (1 - 2 * pad) / max(img.size)
    img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, ((size - img.width) // 2, (size - img.height) // 2 + round(size * 0.02)), img)
    return out


def main():
    base = strip_shadow(Image.open(SRC).convert("RGBA"))
    for size in (512, 180, 64, 32):
        square(base, size).save(ROOT / f"logo-blue-{size}.png")
    (ROOT.parent / "client" / "app").mkdir(exist_ok=True)
    square(base, 64).save(ROOT.parent / "client" / "app" / "icon.png")
    square(base, 180, 0.1).save(ROOT.parent / "client" / "app" / "apple-icon.png")
    square(base, 512).save(ROOT.parent / "client" / "public" / "logo.png")
    buf = io.BytesIO()
    square(base, 64).save(buf, "PNG", optimize=True)
    (ROOT.parent / "site" / "favicon.datauri").write_text("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), encoding="utf-8")
    sq = square(base, 256)
    sq.save(ROOT.parent / "site" / "dots" / "logo.png")
    print("logo ready")


if __name__ == "__main__":
    main()
