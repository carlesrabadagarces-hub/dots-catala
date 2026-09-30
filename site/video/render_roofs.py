"""Render the 8 s rooftops clip to frames with Playwright, then encode with ffmpeg.

Usage:  python site/video/render_explainer.py  (needs playwright and ffmpeg)
"""
import glob
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
FPS, DURATION = 30, 16
ffmpeg = shutil.which("ffmpeg") or glob.glob("/tmp/claude-0/venv/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*")[0]
frames = here / "frames"
shutil.rmtree(frames, ignore_errors=True)
frames.mkdir()
exe = (glob.glob("/opt/pw-browsers/chromium*/chrome-linux*/chrome") or [None])[0]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto((here / "roofs.html").as_uri())
    page.wait_for_function("window.READY === true", timeout=30000)
    for i in range(FPS * DURATION):
        page.evaluate(f"seek({i / FPS})")
        page.screenshot(path=str(frames / f"f{i:04d}.jpg"), type="jpeg", quality=93)
    browser.close()
media = here.parent / "media"
subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%04d.jpg"), "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(media / "teulades.mp4")], check=True)
subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%04d.jpg"), "-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-cpu-used", "5", "-row-mt", "1", str(media / "teulades.webm")], check=True)
shutil.copy(frames / f"f{int(5.0 * FPS):04d}.jpg", media / "teulades-poster.jpg")
shutil.rmtree(frames)
print("ok")
