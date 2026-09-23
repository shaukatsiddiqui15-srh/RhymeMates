# docs/ — generated, do not edit

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
