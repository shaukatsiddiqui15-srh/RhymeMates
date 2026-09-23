# Deploying rhymemates.com

The site is plain static files. There is no build step, no npm install, no server
runtime. Whatever you upload is what gets served.

Publish directory: **`site/`**

---

## Recommended: Cloudflare Pages

1. Push this repo to GitHub (or use `npx wrangler pages deploy site`).
2. Cloudflare dashboard → Workers & Pages → Create → Pages → connect the repo.
3. Build settings:
   - Framework preset: **None**
   - Build command: *(leave empty)*
   - Build output directory: **`site`**
4. Custom domains → add `rhymemates.com` and `www.rhymemates.com`.

If the domain's nameservers already point at Cloudflare, the DNS records are
created for you. Otherwise add these at your registrar:

| Type  | Name  | Value                          |
| ----- | ----- | ------------------------------ |
| CNAME | `@`   | `<your-project>.pages.dev`     |
| CNAME | `www` | `<your-project>.pages.dev`     |

Registrars that reject a CNAME on the apex want an ALIAS/ANAME record instead —
same value. Some need A records; Cloudflare will show the current IPs if so.

## Alternative: Netlify

Same shape — publish directory `site`, no build command. `_headers` is read by
both hosts, so compression, caching and the CSP carry over unchanged.

## Temporary: GitHub Pages, from `docs/`

`docs/` is a generated, disposable copy of the site for a quick preview. It is
**not** the long-term home — see the caveats below.

```bash
python3 site/tools/build_pages.py   # regenerate docs/ from site/
```

Then: repo **Settings → Pages → Source: Deploy from a branch → `main` / `/docs`**.
No workflow file needed; Pages publishes `/docs` directly.

Your preview lands at `https://<username>.github.io/<repo>/`.

To undo, entirely: `rm -rf docs` and set Pages back to None.

### What `build_pages.py` changes, and why

| Change | Reason |
| --- | --- |
| `site.webmanifest` paths made relative, `start_url: "./"` | Pages serves project sites from a subpath; the absolute `/` paths would 404 |
| `<meta http-equiv="Content-Security-Policy">` injected | Pages ignores `_headers`, so the CSP has to travel in the document |
| `frame-ancestors` dropped from that CSP | Meta-delivered CSP cannot express it — there is no workaround |
| `noindex, nofollow` added | This URL 404s once you delete the folder. Indexing it would leave dead results competing with rhymemates.com |
| `<link rel="canonical">` removed | It pointed at rhymemates.com, which is not live yet |
| `robots.txt` replaced, `sitemap.xml` omitted | Crawling stays allowed so the noindex can actually be read; no point advertising a sitemap for a different domain |
| `.nojekyll` added | Stops Pages running the output through Jekyll, which skips underscore-prefixed paths |
| `tools/`, `data/`, `_headers`, `DEPLOY.md` not copied | Build-time only; nothing in the page fetches them at runtime |

### What you give up versus Cloudflare Pages

- **Cache-Control.** Pages sends a flat `max-age=600` on everything. The
  year-long `immutable` policy on `/assets/*` in `_headers` does not apply, so
  repeat visitors revalidate every ten minutes.
- **`X-Content-Type-Options`, `Permissions-Policy`, `frame-ancestors`.** Header-only;
  no meta equivalent exists. The CSP itself survives, which is the one that matters.
- **Custom domain.** Possible (add a `CNAME` file and the apex A records), but if
  you are pointing rhymemates.com at anything, point it at Cloudflare Pages and
  keep the full header set.

Compression is fine — Pages gzips text assets at its CDN, so the performance
numbers hold.

### Verified on the preview

Served from a `/rhymemates/` subpath: Performance 97, Accessibility 100,
Best Practices 100, CLS 0, TBT 0 ms. SEO scores 63 for exactly one reason —
"Page is blocked from indexing" — which is the `noindex` doing its job.

---

## After the first deploy

- Confirm HTTPS is active and HTTP redirects to it (both hosts do this by default).
- Check `https://rhymemates.com/sitemap.xml` and `/robots.txt` resolve.
- Submit the domain to [Google Search Console](https://search.google.com/search-console)
  and add the sitemap. The `VideoObject` JSON-LD makes the page eligible for
  video rich results, which is the main SEO reason this site exists.
- Add the site link to the YouTube channel banner and the About tab.

## Updating after a new upload

```bash
python3 site/tools/refresh_videos.py --report   # pull the catalogue, list what's new
# add a thumbnail master to Images_Videos/thumbnails-16x9/ (or -9x16/)
python3 site/tools/build_assets.py              # derive web renditions
# add an entry to site/data/videos.json
python3 site/tools/render_site.py               # rebuild the cards + JSON-LD
```

Then redeploy. On Cloudflare Pages and Netlify a `git push` is enough.

## A note on the headers

`_headers` sets a strict Content-Security-Policy that allows exactly one external
origin: `youtube-nocookie.com`, and only in a frame. If you ever add analytics, a
font CDN, or an embedded form, the policy must be widened or those resources will
be blocked silently. That is the intended trade-off — it is what keeps the
"no tracking on this site" claim in the For Parents section true.
