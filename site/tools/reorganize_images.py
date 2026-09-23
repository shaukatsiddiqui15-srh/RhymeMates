#!/usr/bin/env python3
"""Rename and sort the raw WhatsApp exports in Images_Videos/ into a named library.

Run once. Safe to re-run: files already in place are skipped, nothing is deleted.
Duplicates (verified by md5) are parked in _unused/_duplicates/ rather than removed.
"""

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Images_Videos"

# original filename -> destination relative to Images_Videos/
MAPPING = {
    # --- brand kit -------------------------------------------------------
    "WhatsApp Image 2026-09-23 at 20.56.42.jpeg": "brand/logo-roundel.jpg",
    "WhatsApp Image 2026-09-23 at 20.56.43.jpeg": "brand/character-sheet.jpg",
    "WhatsApp Image 2026-09-.jpeg": "brand/lily-full.jpg",
    "Whatsmage 2026-09-23 at 20.56.43.jpeg": "brand/max-full.jpg",

    # --- 16:9 thumbnails -------------------------------------------------
    "WhatsApp Image 2026-09-23 at 20.52.33.jpeg": "thumbnails-16x9/happy-birthday-song.jpg",
    "WhatsApp Image 2026-09-23 at 20.53.26.jpeg": "thumbnails-16x9/dino-park.jpg",
    "WhatsApp Image 2026-09-23 at 20.53.27.jpeg": "thumbnails-16x9/ek-mota-hathi.jpg",
    "WhatsApp Image 2026-09-23 at 20.53.34.jpeg": "thumbnails-16x9/the-magic-show.jpg",
    "WhatsApp Image 2026-09-23 at 20.53.35.jpeg": "thumbnails-16x9/alien-planet.jpg",
    "WhatsApp Image 2026-9-23 at 20.53.35.jpeg": "thumbnails-16x9/jungle-adventure.jpg",
    "WhatsApp Image 2026at 20.53.35.jpeg": "thumbnails-16x9/aaha-tamatar.jpg",
    "WhatsApp Image 2026-09-23 at 20.54.37.jpeg": "thumbnails-16x9/laddu-ludhka.jpg",
    "WhatsApp Image 6-09-23 at 20.54.37.jpeg": "thumbnails-16x9/veggie-market.jpg",
    "WhatsApp Image 2026-09-23 at 20.54.46.jpeg": "thumbnails-16x9/five-senses.jpg",
    "WhatsApp 2026-09-23 at 20.54.46.jpeg": "thumbnails-16x9/types-of-vehicles.jpg",
    "WhatsApp Image 2026-09-23 at 20.56.01.jpeg": "thumbnails-16x9/abc-alphabet-song.jpg",
    "WhatsApp Imag026-09-23 at 20.56.01.jpeg": "thumbnails-16x9/abc-a-for-apple.jpg",
    "WhatsApp Image 2026-09-23 20.56.01.jpeg": "thumbnails-16x9/weather-can-change.jpg",
    "WhatsApp Image 2026-09-23 at 20.56.02.jpeg": "thumbnails-16x9/shapes-night-scene.jpg",
    "WhatsApp Image 2026-09-23 at 0.56.02.jpeg": "thumbnails-16x9/lets-learn-shapes.jpg",
    "WhatsAp2026-09-23 at 20.56.02.jpeg": "thumbnails-16x9/days-of-the-week-arch.jpg",
    "WhatsApp Image 2026- at 20.56.02.jpeg": "thumbnails-16x9/days-of-the-week-sign.jpg",
    "WhatsApp Ima 2026-09-23 at 20.56.03.jpeg": "thumbnails-16x9/chidiya-rani.jpg",
    "WhatsApp Ima026-09-23 at 20.56.03.jpeg": "thumbnails-16x9/lets-learn-numbers-1-to-10.jpg",
    "WhatsApp Image 209-23 at 20.56.03.jpeg": "thumbnails-16x9/lets-learn-fruits.jpg",
    "img789.jpeg": "thumbnails-16x9/abc-alphabet-rainbow.jpg",

    # --- 9:16 Shorts covers ----------------------------------------------
    "WhatsApp Image 2026-09-23 at 20.54.44.jpeg": "thumbnails-9x16/the-magic-door.jpg",
    "WhatsApp Image 2026-09-23 at 20.54.45.jpeg": "thumbnails-9x16/bandar-mama-ka-dance.jpg",
    "WhatsApp Image 2026-09-23.jpeg": "thumbnails-9x16/tiny-dino-peekaboo.jpg",
    "WhatsApp Image 2026-09-2 at 20.56.04.jpeg": "thumbnails-9x16/chanda-mama.jpg",

    # --- text-free scene plates ------------------------------------------
    "WhatsApp Image 2026-09-23 at 20.54.32.jpeg": "scenes/beach-dive.jpg",
    "WhatsApp Image 2026-09-23 at 20.54.36.jpeg": "scenes/underwater-reef.jpg",
    "WhatsApp Image 226-09-23 at 20.54.36.jpeg": "scenes/jungle-trail.jpg",

    # --- off-model, parked but kept --------------------------------------
    "WhatsApp Image 2026-09-23 at 20.56.00.jpeg": "_unused/family-home-sweet-home.jpg",

    # --- exact duplicates (md5-verified) ---------------------------------
    "WhatsApp 26-09-23 at 20.56.00.jpeg": "_unused/_duplicates/dup-of-family-home-sweet-home.jpg",
    "WhatsApp Image 2026-09-23 at 20.56.43 (1).jpeg": "_unused/_duplicates/dup-of-lily-full.jpg",
    "imgjj.jpeg": "_unused/_duplicates/dup-of-abc-a-for-apple.jpg",
}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not SRC.is_dir():
        print(f"error: {SRC} not found", file=sys.stderr)
        return 1

    on_disk = {p.name for p in SRC.iterdir() if p.is_file() and not p.name.startswith(".")}
    expected = set(MAPPING)

    missing = expected - on_disk
    unknown = on_disk - expected

    if missing:
        print("Already moved or absent (skipping):")
        for name in sorted(missing):
            print(f"  - {name}")
    if unknown:
        print("\nNot in mapping — left where they are, review manually:")
        for name in sorted(unknown):
            print(f"  ? {name}")

    moved = []
    for src_name, dest_rel in sorted(MAPPING.items()):
        src = SRC / src_name
        if not src.exists():
            continue
        dest = SRC / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"skip (exists): {dest_rel}")
            continue
        digest = md5(src)
        shutil.move(str(src), str(dest))
        moved.append((src_name, dest_rel, digest))

    print(f"\nMoved {len(moved)} file(s).")
    write_manifest(moved)
    return 0


def write_manifest(moved):
    manifest = SRC / "MANIFEST.md"
    lines = [
        "# Rhyme Mates — asset library",
        "",
        "Generated by `site/tools/reorganize_images.py`. Maps the original WhatsApp",
        "export filenames to their current names so nothing becomes untraceable.",
        "",
        "## Layout",
        "",
        "| Folder | Contents |",
        "| --- | --- |",
        "| `brand/` | Logo roundel, Max & Lily model sheet, full-body character cutouts |",
        "| `thumbnails-16x9/` | Video thumbnail masters, 1600x900 |",
        "| `thumbnails-9x16/` | Shorts cover masters, 900x1600 |",
        "| `scenes/` | Text-free scene plates, usable as backgrounds |",
        "| `_unused/` | Off-model art kept for reference |",
        "| `_unused/_duplicates/` | Byte-identical copies of files already in the library |",
        "",
        "## Naming",
        "",
        "Files are named by **slug only** — no dates. Publish dates are unreliable for the",
        "older assets and live in `site/data/videos.json` instead, keyed by the same slug.",
        "",
    ]
    if moved:
        lines += [
            "## Rename map",
            "",
            "| Original | Current | md5 |",
            "| --- | --- | --- |",
        ]
        for src_name, dest_rel, digest in sorted(moved, key=lambda r: r[1]):
            lines.append(f"| `{src_name}` | `{dest_rel}` | `{digest[:12]}` |")
        lines.append("")
    manifest.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {manifest.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
