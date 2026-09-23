# Rhyme Mates

Website and asset library for the [Rhyme Mates](https://www.youtube.com/@RhymeMates)
YouTube channel — original nursery rhymes and learning songs for preschoolers,
in English and हिंदी, starring Max & Lily.

- Repository: <https://github.com/shaukatsiddiqui15-srh/RhymeMates> (public — see [COPYRIGHT.md](COPYRIGHT.md))
- Temporary preview: <https://shaukatsiddiqui15-srh.github.io/RhymeMates/> — served from `docs/`, **not** the long-term host
- Intended home: **rhymemates.com** via Cloudflare Pages, see [site/DEPLOY.md](site/DEPLOY.md)

```
RhymeMates/
├── Images_Videos/          master art library (never modified by the build)
│   ├── brand/              logo roundel, model sheet, character cutouts
│   ├── thumbnails-16x9/    video thumbnail masters, 1600×900
│   ├── thumbnails-9x16/    Shorts cover masters, 900×1600
│   ├── scenes/             text-free scene plates
│   ├── _unused/            off-model art + byte-identical duplicates
│   └── MANIFEST.md         original filename → current name, with md5s
├── docs/                   TEMPORARY — generated GitHub Pages copy of site/
│                           every file is generated; see docs/README.md
│                           `rm -rf docs` + Pages → None fully undoes it
└── site/                   the website — the source of truth
    ├── index.html
    ├── css/styles.css
    ├── js/main.js
    ├── data/               videos.json (curated) · catalogue.json · lqip.json
    ├── assets/             generated web renditions — safe to delete & rebuild
    ├── tools/              the five scripts below
    ├── _headers            caching + CSP for Cloudflare Pages / Netlify
    └── DEPLOY.md           how to get this onto rhymemates.com
```

## Running it locally

In VS Code, press **F5** — it serves `site/` on port 8000 and opens Chrome.
The Run and Debug dropdown also offers:

| Configuration | What it is for |
| --- | --- |
| Rhyme Mates — desktop | 1440×950, DevTools open |
| Rhyme Mates — mobile viewport | 414×896 |
| Rhyme Mates — reduced motion | Forces `prefers-reduced-motion`; the page must stay static and fully usable |
| Rhyme Mates — offline | Blocks all non-localhost DNS; the page must render identically |
| GitHub Pages preview | Serves `docs/` at `/docs/` so subpath-relative URLs get exercised |

Tasks (⇧⌘B, or Run Task) cover `build assets`, `render site`, `build pages`,
`refresh videos`, `rebuild everything`, `lighthouse` and the two stop-server
tasks. The server stops automatically when you end the debug session.

Without an editor:

```bash
python3 -m http.server 8000 --directory site
```

No build step, no npm install, no dependencies beyond Pillow for the image
pipeline. The site is plain HTML, CSS and JavaScript with zero libraries and
zero external requests — it renders identically with all non-localhost DNS
blocked.

## The build scripts

| Script | What it does |
| --- | --- |
| `tools/reorganize_images.py` | One-time. Renamed the 37 raw WhatsApp exports into the library above and wrote `MANIFEST.md`. Safe to re-run; it skips anything already in place and deletes nothing. |
| `tools/build_assets.py` | Derives `site/assets/` from the masters: transparent character cutouts, responsive WebP renditions, JPEG fallbacks, and blurred LQIP placeholders. |
| `tools/refresh_videos.py` | Scrapes the channel's Videos and Shorts tabs (no API key) into `data/catalogue.json`. `--report` lists catalogue entries not yet featured on the site. |
| `tools/render_site.py` | Reads `data/videos.json` and writes the video cards, Shorts rail, filter pills and JSON-LD into `index.html` between `<!-- name:start -->` markers. |
| `tools/build_pages.py` | Generates the disposable `docs/` copy for GitHub Pages: relative manifest paths, meta CSP, `noindex`, `.nojekyll`. See `site/DEPLOY.md`. |

### Adding a video to the site

```bash
python3 site/tools/refresh_videos.py --report
# drop a thumbnail master into Images_Videos/thumbnails-16x9/ (or -9x16/)
python3 site/tools/build_assets.py
# add an entry to site/data/videos.json
python3 site/tools/render_site.py
```

`videos.json` is the curated layer — deliberately hand-edited, because the site
only features videos we hold a thumbnail master for. `catalogue.json` is the
full 61-video channel dump and is regenerated, not edited.

## Design decisions worth knowing

**Video embeds are facades.** Cards render as a thumbnail plus a play button;
the `youtube-nocookie.com` iframe is only injected on click. Nothing reaches
Google before a visitor asks for it, which is what makes the "no tracking on
this site" claim in the For Parents section true, and keeps six iframes off the
initial load.

**Cards are real HTML, not client-rendered.** `render_site.py` writes them into
`index.html`, so the page works without JavaScript and search engines see the
content and the `VideoObject` structured data.

**`--pink` is `#d81b60`, not the logo's `#f0327a`.** The logo pink is only
3.86:1 against white, which fails WCAG AA for button labels. `--pink-bright`
holds the original for decoration and large gradient headings, where the 3:1
large-text threshold applies.

**Reveal animations are gated on `@media (scripting: enabled)`** rather than a
`.js` class set by an inline script. That is what lets `script-src` stay at a
strict `'self'` — with no inline script in the document, nothing needs excusing.
A 2.5-second timeout in `main.js` reveals everything
unconditionally if the IntersectionObserver never fires, so a stalled observer
can never leave the page looking blank.

**`style-src` allows `'unsafe-inline'`, deliberately.** The page uses inline
`style` attributes for the per-card LQIP placeholders, the six For Parents accent
colours and the reveal stagger delays. A strict `style-src 'self'` strips all of
them *silently* — no violation event is raised, the page just quietly loses them.
The stricter fix is to emit those values as a generated stylesheet; for a static
page with no user input and no forms, relaxing styles only is the proportionate
trade. `script-src` stays at `'self'`, which is where the real protection is.

**Images set `height: auto` globally.** The `width`/`height` attributes on
`<img>` map to CSS presentational hints, so a constrained width without
`height: auto` leaves the attribute height in place and silently squashes the
image. The hero characters are sized by width for the same reason.

## Copyright

The repository is public so GitHub Pages can serve it. That is not a licence —
see [COPYRIGHT.md](COPYRIGHT.md). The Max & Lily designs, the logo and all
thumbnail masters are proprietary; no open-source licence is applied to the code
either, though you may want to add one.

## Measured results

Lighthouse, against `python3 -m http.server`:

| | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- |
| Desktop | 100 | 100 | 100 | 100 |
| Mobile | 97 | 100 | 100 | 100 |

CLS 0 and TBT 0 ms on both. The mobile Performance gap is render-blocking CSS
over an uncompressed dev server; `_headers` enables compression and caching on
the real host.
