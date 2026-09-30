"""Turn a photo of a walking person into an articulated cut-out rig.

The generated sprite sheets only ever showed one leg position, so the footer walk
always limped. Here we cut one good frame into a torso and two legs that pivot at the
hip, and export them with their joint positions; the page then drives a real walk
cycle with CSS transforms.

Run:  python tools/rig_people.py            (rebuild layers from the source photos)
      python tools/rig_people.py --sheet    (also render a PNG contact sheet to check)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
SRC = Path("/tmp/claude-0/-home-user-dots-catala/307cc249-a9ba-5077-be18-0763d39c3edd/images")
OUT = HERE / "people"
HEIGHT = 420            # exported person height in pixels
PAD = 34                # transparent margin so swinging legs stay on the canvas
TOL = 11                # chroma key tolerance against the flat studio background
SOURCES = {"a": ("3.webp", 3), "b": ("4.webp", 3)}   # file, which of the 4 frames to rig


# ---------------------------------------------------------------- cut-out
def keyed(path):
    """Remove the flat background and return RGBA, keeping soft edges."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    h, w, _ = a.shape
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3),
                             a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    d = np.linalg.norm(a - bg, axis=2)
    cand = d < TOL
    reg = np.zeros_like(cand)
    reg[0] |= cand[0]; reg[-1] |= cand[-1]; reg[:, 0] |= cand[:, 0]; reg[:, -1] |= cand[:, -1]
    while True:                                   # flood fill from the frame edges
        n = reg.copy()
        n[1:] |= reg[:-1]; n[:-1] |= reg[1:]; n[:, 1:] |= reg[:, :-1]; n[:, :-1] |= reg[:, 1:]
        n &= cand
        if (n == reg).all():
            break
        reg = n
    grow = reg.copy()
    for _ in range(2):
        g = grow.copy()
        g[1:] |= grow[:-1]; g[:-1] |= grow[1:]; g[:, 1:] |= grow[:, :-1]; g[:, :-1] |= grow[:, 1:]
        grow = g
    band = grow & ~reg
    alpha = np.ones((h, w), np.float32)
    alpha[reg] = 0
    alpha[band] = np.clip((d[band] - TOL * 0.6) / (TOL * 2.6), 0, 1)
    out = a.copy()
    soft = band & (alpha < 1)
    k = (1 - alpha[soft])[:, None]
    out[soft] = np.clip((a[soft] - k * bg) / np.maximum(alpha[soft][:, None], 0.25), 0, 255)
    return Image.fromarray(np.dstack([out, alpha * 255]).astype(np.uint8), "RGBA")


def largest_blob(img):
    """Keep the biggest connected shape (drops keying speckle)."""
    from collections import deque
    a = np.array(img)
    m = a[..., 3] > 30
    seen = np.zeros_like(m)
    best, best_n = None, 0
    for y in range(m.shape[0]):
        for x in range(m.shape[1]):
            if m[y, x] and not seen[y, x]:
                q, pts = deque([(y, x)]), []
                seen[y, x] = True
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                if len(pts) > best_n:
                    best, best_n = pts, len(pts)
    keep = np.zeros_like(m)
    for y, x in best:
        keep[y, x] = True
    a[..., 3] = np.where(keep, a[..., 3], 0)
    return Image.fromarray(a)


def person(path, index):
    """One frame of the source sheet, background removed and scaled to HEIGHT."""
    img = keyed(path)
    w, h = img.size
    fw = w // 4
    frame = largest_blob(img.crop((index * fw, 0, (index + 1) * fw, h)))
    bb = frame.getchannel("A").point(lambda v: 255 if v > 30 else 0).getbbox()
    frame = frame.crop(bb)
    s = HEIGHT / frame.size[1]
    frame = frame.resize((max(1, round(frame.size[0] * s)), HEIGHT), Image.LANCZOS)
    # room around the figure so a swinging leg is never clipped by the canvas
    canvas = Image.new("RGBA", (frame.size[0] + PAD * 2, frame.size[1] + PAD * 2), (0, 0, 0, 0))
    canvas.alpha_composite(frame, (PAD, PAD))
    return canvas


# ---------------------------------------------------------------- joints
def rows_runs(mask, y, gap=3):
    idx = np.where(mask[y])[0]
    if not len(idx):
        return []
    brk = np.where(np.diff(idx) > gap)[0]
    out, s = [], 0
    for b in brk:
        out.append((int(idx[s]), int(idx[b])))
        s = b + 1
    out.append((int(idx[s]), int(idx[-1])))
    return out


def blobs_below(m, split):
    """Connected shapes below the waist line: one per leg."""
    from collections import deque
    h, w = m.shape
    seen = np.zeros_like(m)
    out = []
    for y in range(int(split), h):
        for x in range(w):
            if m[y, x] and not seen[y, x]:
                q, pts = deque([(y, x)]), []
                seen[y, x] = True
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                        ny, nx = cy + dy, cx + dx
                        if int(split) <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                if len(pts) > 200:
                    out.append(pts)
    out.sort(key=len, reverse=True)
    return out[:2]


def joints(img):
    """Find where the legs separate, the hip pivot and each leg's foot."""
    m = np.array(img)[..., 3] > 40
    h, w = m.shape
    split = None
    for y in range(int(h * 0.45), h - PAD - 20):
        r = rows_runs(m, y)
        if len(r) == 2 and r[1][0] - r[0][1] > 4 and min(b - a for a, b in r) > 5:
            if all(len(rows_runs(m, yy)) >= 2 for yy in range(y, min(y + 20, h))):
                split = y
                break
    if split is None:
        raise SystemExit("legs never separate; pick another source frame")
    blobs = blobs_below(m, split)
    if len(blobs) != 2:
        raise SystemExit(f"expected two legs below the waist, found {len(blobs)}")
    legs = []
    for pts in blobs:
        ar = np.array(pts)
        low = ar[:, 0].max()
        foot = ar[ar[:, 0] >= low - 4][:, 1].mean()          # centre of the shoe
        top = ar[ar[:, 0] <= int(split) + 3][:, 1]
        legs.append({"pts": pts, "foot": float(foot), "top": float(top.mean()),
                     "x0": int(top.min()), "x1": int(top.max())})
    legs.sort(key=lambda l: l["foot"])                       # back leg first, front leg second
    # the pivot sits on the waist line itself: the cut there then never slides
    # sideways when a leg swings, so no wedge of cloth can poke out of the body
    hip = ((legs[0]["top"] + legs[1]["top"]) / 2, split - 2)
    ground = h - PAD - 4
    for leg in legs:
        dx, dy = leg["foot"] - hip[0], ground - hip[1]
        leg["angle"] = float(np.degrees(np.arctan2(dx, dy)))
        leg["len"] = float(np.hypot(dx, dy))
    across = rows_runs(m, int(split) + 2)                   # both thighs, side by side
    band = [across[0][0], across[-1][1]]
    radius = float(np.clip(0.5 * (band[1] - band[0]), h * 0.06, h * 0.12))
    return {"h": h, "w": w, "split": float(split), "ground": float(ground), "radius": radius, "band": band,
            "hip": [float(hip[0]), float(hip[1])],
            "len": float(np.mean([l["len"] for l in legs])), "legs": legs}


def layers(img, j):
    """Split the photo into a torso and one rigid piece per leg, on a shared canvas."""
    a = np.array(img)
    h, w = a.shape[:2]
    split = j["split"]
    hipx, hipy = j["hip"]
    radius = j["radius"]
    yy = np.arange(h)[:, None]
    # The hip disc rotates with the leg, so it must hold nothing but trouser. Above the
    # waist we paint it flat in the trouser colour: a plain fill has no pattern to swirl,
    # and the hem of a coat can never swing into view.
    xx = np.arange(w)[None, :]
    patch = ((xx - hipx) ** 2 + (yy - hipy) ** 2 < radius ** 2) \
        & (xx >= j["band"][0]) & (xx <= j["band"][1])       # never wider than the hips
    strip = a[int(split) + 2:int(split) + 14]
    cloth = (np.median(strip[strip[..., 3] > 200][:, :3], axis=0) if (strip[..., 3] > 200).any()
             else np.array([70, 70, 80])).astype(np.uint8)
    legsrc = a.copy()
    thin = patch & (a[..., 3] < 210)                        # the notch between the legs, and any
    for c in range(3):                                      # soft edge the cut-out left behind
        legsrc[..., c] = np.where(thin, cloth[c], legsrc[..., c])
    legsrc[..., 3] = np.where(patch, 255, legsrc[..., 3])
    below = np.repeat(yy >= split, w, axis=1)
    parts = {}
    torso = a.copy()
    torso[..., 3] = np.where(below, 0, torso[..., 3])        # torso keeps everything above the waist
    parts["torso"] = Image.fromarray(torso)
    for i, leg in enumerate(j["legs"]):
        sel = np.zeros((h, w), bool)
        for y, x in leg["pts"]:
            sel[y, x] = True
        # Carry a solid disc of hip around with the leg. A filled circle centred on the
        # pivot looks identical however far the leg swings, so the join never opens a
        # gap or lets a wedge of cloth poke out. It is small enough to stay inside the
        # body, and its few transparent pixels (the notch between the legs) are filled in.
        sel |= patch
        p = legsrc.copy()
        p[..., 3] = np.where(sel, p[..., 3], 0)
        parts["back" if i == 0 else "front"] = Image.fromarray(p)
    return parts


# ---------------------------------------------------------------- walk cycle (also used by the page)
AMPLITUDE = 21.0            # how far the legs swing, in degrees


def pose(t):
    """Hip angle (degrees) of one leg at phase t of the cycle.

    Stance (the foot on the ground) is a steady sweep backwards; the swing
    forward is quicker, which is what makes a walk read as a walk.
    """
    t %= 1.0
    if t < 0.62:                                             # stance: front to back, even pace
        u = t / 0.62
        return AMPLITUDE * (1 - 2 * u)
    u = (t - 0.62) / 0.38                                    # swing: back to front, eased
    u = u * u * (3 - 2 * u)
    return AMPLITUDE * (2 * u - 1)


def rise(t, leg_len):
    """How far the hips lift at this phase.

    The leg carrying the weight is a strut of fixed length, so the body is
    lowest when the legs are furthest apart and highest as one passes vertical.
    Following that keeps the planted foot still instead of skating.
    """
    straightest = min(abs(pose(t)), abs(pose(t + 0.5)))
    return leg_len * (np.cos(np.radians(straightest)) - np.cos(np.radians(AMPLITUDE)))


def render(parts, j, t):
    """Compose one frame of the cycle (used only to check the rig visually)."""
    h, w = j["h"], j["w"]
    hip = j["hip"]
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bob = -rise(t, j["len"])
    order = [("back", t + 0.5), ("torso", None), ("front", t)]
    for name, phase in order:
        if name == "torso":
            canvas.alpha_composite(shift(parts["torso"], 0, bob))
            continue
        leg = j["legs"][0 if name == "back" else 1]
        layer = rot(parts[name], hip, pose(phase) - leg["angle"])
        layer = shift(layer, 0, bob)
        m = np.array(layer)                                  # the torso owns everything above the waist
        m[:int(j["split"] + bob), :, 3] = 0
        canvas.alpha_composite(Image.fromarray(m))
    return canvas


def rot(img, pivot, deg):
    """Swing a layer around a joint. Positive degrees move the foot forwards."""
    return img.rotate(deg, resample=Image.BICUBIC, center=(pivot[0], pivot[1]))


def shift(img, dx, dy):
    return img.transform(img.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BICUBIC)


# ---------------------------------------------------------------- build
OUT.mkdir(exist_ok=True)
meta = {}
for key, (src, idx) in SOURCES.items():
    img = person(SRC / src, idx)
    j = joints(img)
    parts = layers(img, j)
    for name, p in parts.items():
        p.save(OUT / f"{key}-{name}.webp", quality=86, method=6)
    meta[key] = {"w": j["w"], "h": j["h"], "ground": round(j["ground"], 1), "len": round(j["len"], 1),
                 "split": j["split"], "hip": [round(j["hip"][0], 1), round(j["hip"][1], 1)],
                 "legs": [{"angle": round(l["angle"], 2)} for l in j["legs"]],
                 "amplitude": AMPLITUDE}
    print(key, "size", img.size, "split", round(j["split"]), "hip", [round(v) for v in j["hip"]],
          "leg angles", [round(l["angle"], 1) for l in j["legs"]],
          "feet", [round(l["foot"]) for l in j["legs"]])
    if "--sheet" in sys.argv:
        n = 8
        sheet = Image.new("RGBA", (img.size[0] * n, j["h"]), (235, 236, 240, 255))
        for i in range(n):
            sheet.alpha_composite(render(parts, j, i / n), (img.size[0] * i, 0))
        sheet.convert("RGB").save(f"/tmp/claude-0/rig_{key}.png")
(OUT / "rig.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print("layers written to", OUT)
