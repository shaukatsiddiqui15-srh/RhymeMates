# docs/ — generated, temporary, do not edit

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
