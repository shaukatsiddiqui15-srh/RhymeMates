#!/usr/bin/env python3
"""Re-pull the Rhyme Mates catalogue from YouTube into site/data/catalogue.json.

  python3 site/tools/refresh_videos.py

Scrapes the channel's Videos and Shorts tabs (no API key needed) and writes the
full catalogue: id, title, duration, views, category. Run it after uploading.

This writes catalogue.json, NOT videos.json. videos.json is the hand-curated
subset the site actually features — the ones we hold thumbnail masters for.
Use `--report` to see which catalogue entries are not yet featured.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "site" / "data"
CHANNEL_ID = "UCW33QaobRLvND81S_WKr1cA"
HANDLE = "RhymeMates"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

DEVANAGARI = re.compile(r"[ऀ-ॿ]")

ADVENTURE = re.compile(
    r"adventure|dino park|magic|alien|underwater|planet|jungle|explore|"
    r"magical|surprise|peek-a-boo|who is hiding|guess the", re.I)
LEARNING = re.compile(
    r"learn|abc|alphabet|number|count|colou?r|shape|fruit|vegetable|veggie|"
    r"vehicle|weather|days of the week|senses|opposite|places|animal names|"
    r"sea animals|five senses", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def initial_data(html: str) -> dict:
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        raise RuntimeError("could not locate ytInitialData — YouTube markup changed")
    return json.loads(m.group(1))


def walk(node, key, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                out.append(v)
            walk(v, key, out)
    elif isinstance(node, list):
        for item in node:
            walk(item, key, out)


def continuation_token(blob) -> str | None:
    found = []
    walk(blob, "continuationCommand", found)
    return found[0]["token"] if found else None


def browse(token: str, api_key: str, client_version: str) -> dict:
    body = json.dumps({
        "context": {"client": {"clientName": "WEB", "clientVersion": client_version}},
        "continuation": token,
    }).encode()
    req = urllib.request.Request(
        f"https://www.youtube.com/youtubei/v1/browse?key={api_key}&prettyPrint=false",
        data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def categorise(title: str, is_short: bool) -> str:
    if is_short:
        return "shorts"
    if DEVANAGARI.search(title):
        return "hindi"
    if ADVENTURE.search(title):
        return "adventures"
    if LEARNING.search(title):
        return "learning"
    return "rhymes"


def parse_long_form(html: str) -> list[dict]:
    data = initial_data(html)
    api_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html).group(1)
    version = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html).group(1)

    videos, seen = [], set()

    def harvest(blob):
        lockups = []
        walk(blob, "lockupViewModel", lockups)
        for lv in lockups:
            vid = lv.get("contentId")
            if not vid or vid in seen:
                continue
            meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
            title = meta.get("title", {}).get("content", "")
            if not title:
                continue
            rows = []
            for row in meta.get("metadata", {}).get(
                    "contentMetadataViewModel", {}).get("metadataRows", []):
                for part in row.get("metadataParts", []):
                    text = part.get("text", {}).get("content")
                    if text:
                        rows.append(text)
            badges = []
            walk(lv, "thumbnailBadgeViewModel", badges)
            duration = next((b["text"] for b in badges if b.get("text")), "")
            seen.add(vid)
            videos.append({
                "id": vid,
                "title": title,
                "duration": duration,
                "views": next((r for r in rows if "view" in r), ""),
                "published": next((r for r in rows if "ago" in r), ""),
                "category": categorise(title, False),
            })

    harvest(data)
    token = continuation_token(data)
    guard = 0
    while token and guard < 20:
        guard += 1
        page = browse(token, api_key, version)
        before = len(videos)
        harvest(page)
        if len(videos) == before:
            break
        token = continuation_token(page)
    return videos


def parse_shorts(html: str) -> list[dict]:
    data = initial_data(html)
    lockups = []
    walk(data, "shortsLockupViewModel", lockups)
    shorts, seen = [], set()
    for lv in lockups:
        vid = (lv.get("onTap", {}).get("innertubeCommand", {})
               .get("reelWatchEndpoint", {}).get("videoId"))
        if not vid:
            ids = []
            walk(lv, "videoId", ids)
            vid = ids[0] if ids else None
        if not vid or vid in seen:
            continue
        overlay = lv.get("overlayMetadata", {})
        title = overlay.get("primaryText", {}).get("content", "")
        if not title:
            continue
        seen.add(vid)
        shorts.append({
            "id": vid,
            "title": title,
            "duration": "",
            "views": overlay.get("secondaryText", {}).get("content", ""),
            "published": "",
            "category": "shorts",
        })
    return shorts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="list catalogue entries not featured in videos.json")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)

    print(f"Fetching @{HANDLE} …")
    videos = parse_long_form(fetch(f"https://www.youtube.com/@{HANDLE}/videos"))
    shorts = parse_shorts(fetch(f"https://www.youtube.com/@{HANDLE}/shorts"))
    catalogue = videos + shorts

    out = DATA / "catalogue.json"
    out.write_text(json.dumps({
        "channelId": CHANNEL_ID,
        "handle": HANDLE,
        "counts": {
            "longForm": len(videos),
            "shorts": len(shorts),
            "total": len(catalogue),
        },
        "videos": catalogue,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {len(videos)} long-form + {len(shorts)} shorts = {len(catalogue)}")
    print(f"  wrote {out.relative_to(ROOT)}")

    if args.report:
        featured_path = DATA / "videos.json"
        if not featured_path.exists():
            print("\nno videos.json yet")
            return 0
        featured = {v["id"] for v in json.loads(
            featured_path.read_text(encoding="utf-8"))["videos"]}
        missing = [v for v in catalogue if v["id"] not in featured]
        print(f"\n{len(missing)} catalogue entries not featured on the site:")
        for v in missing:
            print(f"  [{v['category']:<10}] {v['id']}  {v['title'][:64]}")
        print("\nTo feature one: add a thumbnail master to Images_Videos/thumbnails-16x9/")
        print("(or -9x16/), rerun build_assets.py, and add an entry to videos.json.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        sys.exit(f"network error: {exc}")
