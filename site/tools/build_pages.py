#!/usr/bin/env python3
"""Generate docs/ — the GitHub Pages deployment of the site.

  python3 site/tools/build_pages.py

GitHub Pages publishes from /docs on a branch with no workflow file, so this
folder is the whole deployment: push, and it is live.

This is an *interim* host. rhymemates.com is served from here today; the plan is
to move to Cloudflare Pages, which honours site/_headers and so keeps the
immutable asset caching and the header-only security headers GitHub Pages
discards. The move needs no content changes — same files, same URLs.

Differences from site/, all deliberate:

  * A <meta> Content-Security-Policy replaces the one in _headers, which Pages
    ignores. frame-ancestors is dropped because meta-delivered CSP cannot
    express it; Referrer-Policy is re-added as <meta name="referrer">.
  * Absolute "/" paths in site.webmanifest become relative, so the page works
    from a project subpath as well as from the domain root.
  * .nojekyll is added, or Pages runs the output through Jekyll and skips
    underscore-prefixed paths.
  * An existing docs/CNAME is preserved across the rebuild — Pages reads the
    custom domain from that file.
  * A README.md marks the folder as generated, visible to anyone browsing it
    on github.com.

Build-time files (tools/, data/, _headers, DEPLOY.md) are not copied; nothing in
the page fetches them at runtime.

SEO tags are NOT stripped. This folder serves the live domain, so the canonical
tag, sitemap.xml and robots.txt are copied through unchanged and the page stays
indexable.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DOCS = ROOT / "docs"

COPY_DIRS = ("css", "js", "assets")
COPY_FILES = ("index.html", "favicon.svg", "site.webmanifest",
              "robots.txt", "sitemap.xml")

# style-src needs 'unsafe-inline' — the page uses inline style attributes for the
# LQIP placeholders, the For Parents accent colours and the reveal stagger. CSP
# strips them silently without it (no violation event is raised). script-src
# stays strict at 'self'.
CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "
    "frame-src https://www.youtube-nocookie.com https://www.youtube.com; "
    "base-uri 'self'; "
    "form-action 'none'"
)

# Delivered in the document because GitHub Pages cannot send custom headers.
# frame-ancestors has no meta equivalent and is simply unavailable here.
HEAD_META = f"""<!-- Added by build_pages.py: GitHub Pages cannot send custom headers,
     so these travel in the document instead of site/_headers. -->
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
"""

# GitHub renders a folder's README.md in its listing, so this lands exactly where
# someone browsing docs/ on github.com will look. It matters because main() calls
# shutil.rmtree(DOCS) — anything hand-edited here is destroyed without warning.
DOCS_README = """# docs/ — generated, do not edit

**Every file in this folder is generated.** It is rebuilt from scratch by
`site/tools/build_pages.py`, which deletes the whole directory first. Edits made
here are lost silently on the next run.

Edit [`site/`](../site) instead — that is the source of truth — then run:

```bash
python3 site/tools/build_pages.py
```

The one exception is `CNAME`: the script reads it before wiping the folder and
writes it back afterwards, so the custom domain survives a rebuild.

## What this folder is

The live deployment. GitHub Pages publishes `/docs` from `main`, and `CNAME`
points **rhymemates.com** at it.

This is an **interim host**. The intended home is Cloudflare Pages, which
honours [`site/_headers`](../site/_headers) and so keeps the immutable asset
caching and the header-only security headers that GitHub Pages discards. The
migration needs no content changes — same files, same URLs.

## How it differs from site/

- Content-Security-Policy and Referrer-Policy moved into `<meta>` tags, since
  Pages ignores `_headers`. `frame-ancestors`, `X-Content-Type-Options` and
  `Permissions-Policy` have no meta form and are unavailable here.
- `site.webmanifest` paths made relative, so the page works from a subpath too.
- `.nojekyll` added.

SEO tags are unchanged — the canonical, `sitemap.xml` and `robots.txt` are
copied through, and the page is indexable.

Full rationale: [`site/DEPLOY.md`](../site/DEPLOY.md).

## Migrating to Cloudflare

Point Cloudflare Pages at `site/` as the build output directory, move the DNS,
then `rm -rf docs` and set **Settings → Pages → Source** to *None*. Nothing else
in the repository depends on this folder.
"""


def rewrite_index(html: str) -> str:
    anchor = '<meta name="theme-color"'
    if anchor not in html:
        sys.exit("could not find the theme-color meta tag to anchor the insert")
    return html.replace(anchor, HEAD_META + anchor, 1)


def rewrite_manifest(raw: str) -> str:
    data = json.loads(raw)
    data["start_url"] = "./"
    data["scope"] = "./"
    for icon in data.get("icons", []):
        icon["src"] = icon["src"].lstrip("/")
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    if not (SITE / "index.html").exists():
        sys.exit("site/index.html missing — run render_site.py first")
    if not (SITE / "assets").is_dir():
        sys.exit("site/assets missing — run build_assets.py first")

    # Pages stores the custom domain as a CNAME file inside the published folder
    # and mirrors it into repo settings. Since this script wipes the directory,
    # an existing CNAME has to be carried across — losing it silently un-sets
    # the custom domain on the next deploy.
    cname = None
    existing = DOCS / "CNAME"
    if existing.is_file():
        cname = existing.read_text(encoding="utf-8").strip()

    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)

    for name in COPY_DIRS:
        shutil.copytree(SITE / name, DOCS / name)
    for name in COPY_FILES:
        shutil.copy2(SITE / name, DOCS / name)

    (DOCS / "index.html").write_text(
        rewrite_index((SITE / "index.html").read_text(encoding="utf-8")), encoding="utf-8")
    (DOCS / "site.webmanifest").write_text(
        rewrite_manifest((SITE / "site.webmanifest").read_text(encoding="utf-8")), encoding="utf-8")
    (DOCS / "README.md").write_text(DOCS_README, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    if cname:
        (DOCS / "CNAME").write_text(cname + "\n", encoding="utf-8")

    files = [p for p in DOCS.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"docs/  {len(files)} files, {size / 1_048_576:.1f} MB")
    print(f"       CNAME: {cname}" if cname else
          "       no CNAME — serving from the github.io URL")
    for name in sorted(p.name for p in DOCS.iterdir()):
        print(f"       {name}")
    print("\nnot copied (build-time only): tools/, data/, _headers, DEPLOY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
