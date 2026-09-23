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
  * A README.md is written into docs/ marking it generated and temporary, so
    the warning is visible to anyone browsing the folder on github.com.
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

# GitHub renders a folder's README.md directly in its listing, so this lands
# exactly where someone browsing docs/ on github.com will see it. It matters
# because main() calls shutil.rmtree(DOCS) — anything hand-edited in here is
# destroyed without warning on the next run.
DOCS_README = """# docs/ — generated, temporary, do not edit

**Every file in this folder is generated.** It is rebuilt from scratch by
`site/tools/build_pages.py`, which deletes the whole directory first. Edits made
here are lost silently on the next run.

Edit [`site/`](../site) instead — that is the source of truth — then run:

```bash
python3 site/tools/build_pages.py
```

## Why this folder exists

GitHub Pages can publish from `/docs` on a branch with no workflow file, which
makes it the quickest way to get a preview online. **This is a temporary
arrangement.** The long-term host is Cloudflare Pages, which honours
`site/_headers` and so keeps the immutable asset caching and the full security
header set that GitHub Pages discards.

## How it differs from site/

- `noindex, nofollow` — this preview URL 404s once the folder is deleted, so it
  must not end up in search results competing with rhymemates.com
- Content-Security-Policy moved into a `<meta>` tag, since Pages ignores `_headers`
- `site.webmanifest` paths made relative, for serving from a project subpath
- `<link rel="canonical">` removed, `sitemap.xml` not copied
- `.nojekyll` added so Pages does not run the output through Jekyll

Full rationale: [`site/DEPLOY.md`](../site/DEPLOY.md).

## Removing it

```bash
rm -rf docs
```

Then set **Settings → Pages → Source** back to *None*. Nothing else in the
repository depends on this folder.
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

    # GitHub Pages stores the custom domain as a CNAME file inside the published
    # folder, and the repo settings mirror whatever it finds there. Since this
    # script wipes the directory, an existing CNAME has to be carried across —
    # losing it silently un-sets the custom domain on the next deploy.
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
    (DOCS / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (DOCS / "README.md").write_text(DOCS_README, encoding="utf-8")

    if cname:
        (DOCS / "CNAME").write_text(cname + "\n", encoding="utf-8")

    # Without this, Pages runs the content through Jekyll, which skips files and
    # folders beginning with an underscore.
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    files = [p for p in DOCS.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"docs/  {len(files)} files, {size / 1_048_576:.1f} MB")
    if cname:
        print(f"       CNAME preserved: {cname}")
    for name in sorted(p.name for p in DOCS.iterdir()):
        print(f"       {name}")
    print("\nnot copied (build-time only): tools/, data/, _headers, DEPLOY.md, sitemap.xml")
    print("delete the folder to undo: rm -rf docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
