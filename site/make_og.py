"""Render og.jpg (1200x630) for social cards from the rooftops poster. Needs playwright + chromium."""
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
html = f"""<html><body style="margin:0;width:1200px;height:630px;position:relative;overflow:hidden;font-family:'Helvetica Neue',Arial,sans-serif">
<img src="{(here/'video'/'roofs-bg.jpg').as_uri()}" style="position:absolute;left:0;left:-50px;top:-60px;width:1300px">
<div style="position:absolute;inset:0;background:linear-gradient(0deg,rgba(0,0,0,.78),rgba(0,0,0,.05) 65%)"></div>
<img src="{(here/'dots'/'logo.png').as_uri()}" style="position:absolute;left:64px;top:56px;width:64px;height:64px">
<div style="position:absolute;left:64px;bottom:64px;color:#fff;max-width:1000px">
<div style="font-size:92px;font-weight:700;letter-spacing:-4px;line-height:1">superDOTats</div>
<div style="font-size:34px;margin-top:14px;opacity:.92;line-height:1.25">Un Dot per a cada dubte. En català.</div></div></body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=(glob.glob("/opt/pw-browsers/chromium*/chrome-linux*/chrome") or [None])[0])
    pg = b.new_page(viewport={"width": 1200, "height": 630})
    tmp = here / '.og.tmp.html'
    tmp.write_text(html, encoding='utf-8')
    pg.goto(tmp.as_uri())
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(here / "og.jpg"), type="jpeg", quality=88)
    b.close()
    tmp.unlink()
print("og ok")
