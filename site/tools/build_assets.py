#!/usr/bin/env python3
"""Derive web assets in site/assets/ from the masters in Images_Videos/.

  python3 site/tools/build_assets.py

Produces:
  assets/brand/{lily,max,logo}.{webp,png}   transparent cutouts
  assets/thumbs/<slug>-{480,960,1600}.webp  + a 960 jpg fallback
  assets/shorts/<slug>-{300,600}.webp
  assets/scenes/<slug>-1600.webp
  data/lqip.json                            tiny blurred placeholders

Masters in Images_Videos/ are never modified.
"""

import base64
import io
import json
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("Pillow is required:  python3 -m pip install Pillow")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Images_Videos"
SITE = ROOT / "site"
ASSETS = SITE / "assets"

WEBP_Q = 82
JPEG_Q = 84

# Background removal: how far a pixel may stray from the corner colour and
# still count as background. The plates are flat ~#FEFEFE so this is generous.
BG_TOLERANCE = 34


# --------------------------------------------------------------------------
# transparent cutouts
# --------------------------------------------------------------------------

def background_mask(img: Image.Image, tolerance: int = BG_TOLERANCE) -> Image.Image:
    """Flood-fill inward from all four edges; returns L-mode mask, 255 = background.

    Connectivity-based on purpose: white *inside* the subject (Max's sneakers,
    Lily's socks, the highlight in an eye) is never reached from the border and
    so stays opaque.
    """
    w, h = img.size
    px = img.convert("RGB").load()
    seen = bytearray(w * h)
    queue = deque()

    def seed(x, y):
        idx = y * w + x
        if not seen[idx]:
            seen[idx] = 1
            queue.append((x, y))

    # Sample the corners to establish what "background" looks like.
    samples = [px[1, 1], px[w - 2, 1], px[1, h - 2], px[w - 2, h - 2]]
    br = sum(s[0] for s in samples) / 4
    bg = sum(s[1] for s in samples) / 4
    bb = sum(s[2] for s in samples) / 4

    def is_bg(x, y):
        r, g, b = px[x, y]
        return abs(r - br) <= tolerance and abs(g - bg) <= tolerance and abs(b - bb) <= tolerance

    for x in range(w):
        if is_bg(x, 0):
            seed(x, 0)
        if is_bg(x, h - 1):
            seed(x, h - 1)
    for y in range(h):
        if is_bg(0, y):
            seed(0, y)
        if is_bg(w - 1, y):
            seed(w - 1, y)

    out = bytearray(w * h)
    while queue:
        x, y = queue.popleft()
        out[y * w + x] = 255
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and is_bg(nx, ny):
                seen[ny * w + nx] = 1
                queue.append((nx, ny))

    return Image.frombytes("L", (w, h), bytes(out))


def cutout(path: Path, max_height: int) -> Image.Image:
    """White-plate JPEG -> RGBA with feathered edges and no white fringing."""
    img = Image.open(path).convert("RGB")
    mask = background_mask(img)

    # Feather the hard flood-fill boundary so edges are not aliased.
    alpha = Image.eval(mask, lambda v: 255 - v).filter(ImageFilter.GaussianBlur(0.8))

    # Decontaminate: the JPEG edge pixels are the subject blended toward white.
    # Un-premultiply against white so the cutout reads correctly on any colour.
    rgba = img.convert("RGBA")
    rp = rgba.load()
    ap = alpha.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            a = ap[x, y]
            if a == 0 or a == 255:
                continue
            f = a / 255.0
            r, g, b, _ = rp[x, y]
            rp[x, y] = (
                min(255, max(0, int((r - 255 * (1 - f)) / f))),
                min(255, max(0, int((g - 255 * (1 - f)) / f))),
                min(255, max(0, int((b - 255 * (1 - f)) / f))),
                a,
            )
    rgba.putalpha(alpha)

    bbox = alpha.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)

    if rgba.height > max_height:
        ratio = max_height / rgba.height
        rgba = rgba.resize((round(rgba.width * ratio), max_height), Image.LANCZOS)
    return rgba


# --------------------------------------------------------------------------
# raster derivatives
# --------------------------------------------------------------------------

def lqip(img: Image.Image, width: int = 20) -> str:
    """Base64 data URI of a tiny blurred version, for the card background."""
    small = img.convert("RGB")
    ratio = width / small.width
    small = small.resize((width, max(1, round(small.height * ratio))), Image.LANCZOS)
    small = small.filter(ImageFilter.GaussianBlur(0.6))
    buf = io.BytesIO()
    small.save(buf, "WEBP", quality=40)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def derive(src_dir: Path, out_dir: Path, widths, jpeg_at=None, placeholders=None):
    if not src_dir.is_dir():
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(src_dir.glob("*.jpg")):
        img = Image.open(path).convert("RGB")
        slug = path.stem
        if placeholders is not None:
            placeholders[slug] = lqip(img)
        for width in widths:
            if width > img.width:
                continue
            ratio = width / img.width
            resized = img.resize((width, round(img.height * ratio)), Image.LANCZOS)
            resized.save(out_dir / f"{slug}-{width}.webp", "WEBP", quality=WEBP_Q, method=6)
            if jpeg_at == width:
                resized.save(out_dir / f"{slug}-{width}.jpg", "JPEG",
                             quality=JPEG_Q, optimize=True, progressive=True)
            count += 1
    return count


def main() -> int:
    if not SRC.is_dir():
        sys.exit(f"missing {SRC} — run reorganize_images.py first")

    ASSETS.mkdir(parents=True, exist_ok=True)
    placeholders = {}

    # --- cutouts ---
    brand_out = ASSETS / "brand"
    brand_out.mkdir(parents=True, exist_ok=True)
    for name, slug, height, widths in (
        ("lily-full.jpg", "lily", 1100, (200, 320, 480, 700)),
        ("max-full.jpg", "max", 1100, (200, 320, 480, 700)),
        ("logo-roundel.jpg", "logo", 640, (128, 200, 400)),
    ):
        src = SRC / "brand" / name
        if not src.exists():
            print(f"  ! missing {src.name}, skipped")
            continue
        img = cutout(src, height)
        img.save(brand_out / f"{slug}.webp", "WEBP", quality=90, method=6)
        img.save(brand_out / f"{slug}.png", "PNG", optimize=True)
        for w in widths:
            if w >= img.width:
                continue
            small = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
            small.save(brand_out / f"{slug}-{w}.webp", "WEBP", quality=90, method=6)
            small.save(brand_out / f"{slug}-{w}.png", "PNG", optimize=True)
        pct = round(100 * sum(1 for p in img.getdata() if p[3] < 250) / (img.width * img.height))
        print(f"  cutout {slug:<5} {img.width}x{img.height}  {pct}% soft-edge  "
              f"+{len([w for w in widths if w < img.width])} renditions")

    # model sheet stays flat, it is a reference image
    sheet = SRC / "brand" / "character-sheet.jpg"
    if sheet.exists():
        s = Image.open(sheet).convert("RGB")
        s.thumbnail((1400, 1400), Image.LANCZOS)
        s.save(brand_out / "character-sheet-1400.webp", "WEBP", quality=WEBP_Q, method=6)

    # --- thumbnails / shorts / scenes ---
    n = derive(SRC / "thumbnails-16x9", ASSETS / "thumbs",
               (360, 480, 960, 1600), jpeg_at=960, placeholders=placeholders)
    print(f"  thumbs  {n} renditions")
    n = derive(SRC / "thumbnails-9x16", ASSETS / "shorts",
               (240, 300, 600), placeholders=placeholders)
    print(f"  shorts  {n} renditions")
    n = derive(SRC / "scenes", ASSETS / "scenes", (960, 1600))
    print(f"  scenes  {n} renditions")

    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "data" / "lqip.json").write_text(
        json.dumps(placeholders, indent=1, sort_keys=True), encoding="utf-8")
    print(f"  lqip    {len(placeholders)} placeholders")

    total = sum(p.stat().st_size for p in ASSETS.rglob("*") if p.is_file())
    print(f"\nassets/ total {total / 1_048_576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
