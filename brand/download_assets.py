"""Download the Higgsfield art listed in art/manifest.json into brand/art/.

Needs network access to the Higgsfield CDN (d8j0ntlcm91z4.cloudfront.net).
Usage:  python brand/download_assets.py
"""

import json
import sys
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent / "art"
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
failed = 0
for item in manifest:
    target = root / item["file"]
    if target.exists() and target.stat().st_size > 1000:
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(item["url"], timeout=60) as response:
            target.write_bytes(response.read())
        print("ok  ", item["file"])
    except Exception as exc:  # noqa: BLE001 - report and continue
        failed += 1
        print("FAIL", item["file"], exc, file=sys.stderr)
print(f"{len(manifest) - failed}/{len(manifest)} files ready in {root}")
sys.exit(1 if failed else 0)
