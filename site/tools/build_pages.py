#!/usr/bin/env python3
"""Generate docs/ — a self-contained copy of the site for GitHub Pages.

  python3 site/tools/build_pages.py

GitHub Pages can publish from /docs on a branch with no workflow, so this is the
lowest-friction way to get a preview online. The folder is disposable: delete
docs/ and nothing else in the repo changes.

Differences from site/, all of them deliberate:

  * Absolute "/" paths in site.webmanifest become relative, so the page works
    when served from a project subpath (user.github.io/rhymemates/) as well as
    from a domain root.
  * A <meta> Content-Security-Policy replaces the one in _headers, which Pages
    ignores. frame-ancestors is dropped because meta-delivered CSP cannot
    express it.
  * noindex is set, and sitemap.xml is not copied. This preview lives at a
    throwaway URL that will 404 once the folder is deleted; letting Google index
    it would leave dead results competing with rhymemates.com later.
  * Build-time files (tools/, data/, _headers, DEPLOY.md) are not copied —
    nothing in the page fetches them at runtime.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DOCS = ROOT / "docs"

# Runtime files only. data/ is build-time (cards are baked into index.html),
# tools/ is the pipeline, _headers is a Cloudflare/Netlify convention.
COPY_DIRS = ("css", "js", "assets")
COPY_FILES = ("index.html", "favicon.svg", "site.webmanifest")

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

PREVIEW_META = f"""<!-- Added by build_pages.py for the GitHub Pages preview. -->
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
"""

ROBOTS = """# Temporary GitHub Pages preview.
# Crawling is allowed so that the noindex meta tag in index.html can be read;
# blocking here would hide it and the URL could still be indexed from links.
User-agent: *
Allow: /
"""


def rewrite_index(html: str) -> str:
    """Insert the preview meta block and drop domain-specific SEO tags."""
    # The canonical points at rhymemates.com, which is not live yet. Leaving it
    # on a throwaway URL just asserts a relationship to a page that 404s.
    html = re.sub(r'\s*<link rel="canonical"[^>]*>\n?', "\n", html, count=1)

    anchor = '<meta name="theme-color"'
    if anchor not in html:
        sys.exit("could not find the theme-color meta tag to anchor the insert")
    return html.replace(anchor, PREVIEW_META + anchor, 1)


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
    (DOCS / "robots.txt").write_text(ROBOTS, encoding="utf-8")

    # Without this, Pages runs the content through Jekyll, which skips files and
    # folders beginning with an underscore.
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    files = [p for p in DOCS.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"docs/  {len(files)} files, {size / 1_048_576:.1f} MB")
    for name in sorted(p.name for p in DOCS.iterdir()):
        print(f"       {name}")
    print("\nnot copied (build-time only): tools/, data/, _headers, DEPLOY.md, sitemap.xml")
    print("delete the folder to undo: rm -rf docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
