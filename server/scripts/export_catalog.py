"""Write the public catalogue into the landing page (site/body.html).

Run from the server folder:  python scripts/export_catalog.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import catalog_service  # noqa: E402

TARGET = Path(__file__).resolve().parents[2] / "site" / "body.html"


def main() -> None:
    data = {"sectors": catalog_service.sectors(),
            "agents": [{k: a[k] for k in ("id", "name", "role", "icon", "sector", "color", "starters", "look")}
                       for a in catalog_service.list_catalog()]}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TARGET.read_text(encoding="utf-8")
    block = f'<!--CATALOG_START--><script id="catalog-data" type="application/json">{payload}</script><!--CATALOG_END-->'
    html, n = re.subn(r"<!--CATALOG_START-->.*?<!--CATALOG_END-->", lambda _: block, html, flags=re.S)
    if n != 1:
        raise SystemExit("Markers not found in site/body.html")
    TARGET.write_text(html, encoding="utf-8")
    print(f"{len(data['agents'])} Dots exported")


if __name__ == "__main__":
    main()
