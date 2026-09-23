#!/usr/bin/env python3
"""Inject the video grid, Shorts rail, filters and JSON-LD into index.html.

  python3 site/tools/render_site.py

Reads site/data/videos.json + site/data/lqip.json and rewrites the regions of
index.html marked with <!-- name:start --> / <!-- name:end -->. Cards are real
HTML in the served file, so the page works and is crawlable without JavaScript.

Run after editing videos.json or rerunning build_assets.py.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
INDEX = SITE / "index.html"
ORIGIN = "https://rhymemates.com"

CATEGORY_LABEL = {
    "learning": "Learning Song",
    "hindi": "हिंदी Rhyme",
    "adventures": "Story Adventure",
    "rhymes": "Classic Rhyme",
    "shorts": "Short",
}

PLAY_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>'


def e(text: str) -> str:
    return html.escape(str(text), quote=True)


def replace_region(source: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- {re.escape(name)}:start -->)(.*?)(<!-- {re.escape(name)}:end -->)",
        re.S,
    )
    if not pattern.search(source):
        sys.exit(f"marker <!-- {name}:start --> not found in index.html")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", source)


def media_block(video: dict, lqip: dict) -> str:
    slug = video["slug"]
    short = video["aspect"] == "9x16"
    folder, widths = ("shorts", (240, 300, 600)) if short else ("thumbs", (360, 480, 960, 1600))

    srcset = ", ".join(f"assets/{folder}/{slug}-{w}.webp {w}w" for w in widths)
    sizes = "(max-width: 700px) 72vw, 260px" if short else \
            "(max-width: 700px) 92vw, (max-width: 1100px) 46vw, 340px"
    fallback = f"assets/{folder}/{slug}-{widths[-1]}.webp" if short else \
               f"assets/thumbs/{slug}-960.jpg"

    alt = f"Thumbnail for {video['title']}"
    placeholder = lqip.get(slug, "")
    style = f' style="--lqip:url({placeholder})"' if placeholder else ""
    badge = f'<span class="card__badge">{e(video["duration"])}</span>' if video.get("duration") else ""

    label = f"Play {video['title']}"
    if video.get("romanised"):
        label = f"Play {video['romanised']}"

    return (
        f'<button class="card__media" type="button"{style} '
        f'data-video-id="{e(video["id"])}" data-video-title="{e(video["title"])}" '
        f'aria-label="{e(label)}">'
        f'<img src="{fallback}" srcset="{srcset}" sizes="{sizes}" '
        f'alt="{e(alt)}" loading="lazy" decoding="async" '
        f'width="{widths[-1]}" height="{round(widths[-1] * (16/9 if short else 9/16))}">'
        f'<span class="card__play" aria-hidden="true">{PLAY_ICON}</span>'
        f"{badge}"
        f"</button>"
    )


def card(video: dict, lqip: dict, index: int) -> str:
    short = video["aspect"] == "9x16"
    classes = "card card--short" if short else "card"
    delay = f' style="--d:{min(index, 8) * 55}ms"' if not short else ""
    roman = (f'<p class="card__roman">{e(video["romanised"])}</p>'
             if video.get("romanised") else "")
    blurb = f'<p class="card__blurb">{e(video["blurb"])}</p>' if video.get("blurb") else ""
    tag = CATEGORY_LABEL.get(video["category"], video["category"])

    return (
        f'<article class="{classes}" data-category="{e(video["category"])}" data-reveal{delay}>'
        f"{media_block(video, lqip)}"
        f'<div class="card__body">'
        f'<h3 class="card__title">{e(video["title"])}</h3>'
        f"{roman}{blurb}"
        f'<p class="card__tag">{e(tag)}</p>'
        f"</div></article>"
    )


def json_ld(data: dict) -> str:
    channel = data["channel"]
    graph = [{
        "@type": "Organization",
        "@id": f"{ORIGIN}/#org",
        "name": channel["name"],
        "url": ORIGIN,
        "logo": f"{ORIGIN}/assets/brand/logo.png",
        "sameAs": [channel["url"]],
        "description": "Original nursery rhymes, kids' songs and story adventures "
                       "for toddlers and preschoolers, in English and Hindi.",
    }]

    for video in data["videos"]:
        folder = "shorts" if video["aspect"] == "9x16" else "thumbs"
        width = 600 if video["aspect"] == "9x16" else 1600
        graph.append({
            "@type": "VideoObject",
            "name": video["title"],
            "description": video["blurb"] or video["title"],
            "thumbnailUrl": f"{ORIGIN}/assets/{folder}/{video['slug']}-{width}.webp",
            "embedUrl": f"https://www.youtube-nocookie.com/embed/{video['id']}",
            "contentUrl": f"https://www.youtube.com/watch?v={video['id']}",
            "publisher": {"@id": f"{ORIGIN}/#org"},
            "isFamilyFriendly": True,
            "inLanguage": "hi" if video["category"] == "hindi" else "en",
        })

    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{payload}</script>'


def main() -> int:
    data = json.loads((SITE / "data" / "videos.json").read_text(encoding="utf-8"))
    lqip_path = SITE / "data" / "lqip.json"
    lqip = json.loads(lqip_path.read_text(encoding="utf-8")) if lqip_path.exists() else {}

    long_form = [v for v in data["videos"] if v["aspect"] == "16x9"]
    shorts = [v for v in data["videos"] if v["aspect"] == "9x16"]

    present = {v["category"] for v in long_form}
    filters = "".join(
        f'<button class="filter" type="button" data-filter="{e(c["key"])}" '
        f'aria-pressed="{"true" if c["key"] == "all" else "false"}">{e(c["label"])}</button>'
        for c in data["categories"]
        if c["key"] == "all" or c["key"] in present
    )

    source = INDEX.read_text(encoding="utf-8")
    source = replace_region(source, "filters", filters)
    source = replace_region(source, "videos",
                            "\n".join(card(v, lqip, i) for i, v in enumerate(long_form)))
    source = replace_region(source, "shorts",
                            "\n".join(card(v, lqip, i) for i, v in enumerate(shorts)))
    source = replace_region(source, "jsonld", json_ld(data))
    INDEX.write_text(source, encoding="utf-8")

    missing = [
        f"assets/{'shorts' if v['aspect'] == '9x16' else 'thumbs'}/{v['slug']}-"
        f"{600 if v['aspect'] == '9x16' else 960}.webp"
        for v in data["videos"]
        if not (SITE / f"assets/{'shorts' if v['aspect'] == '9x16' else 'thumbs'}/"
                f"{v['slug']}-{600 if v['aspect'] == '9x16' else 960}.webp").exists()
    ]

    print(f"rendered {len(long_form)} video cards + {len(shorts)} shorts")
    print(f"         {len(filters.split('<button')) - 1} filters, "
          f"{len(data['videos']) + 1} JSON-LD nodes")
    if missing:
        print("\nMISSING ASSETS — run build_assets.py:")
        for path in missing:
            print(f"  ! {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
