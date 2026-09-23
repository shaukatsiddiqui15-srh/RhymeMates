/* Rhyme Mates — rhymemates.com
   No dependencies. Everything degrades to a working static page without it. */

(() => {
  'use strict';

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------------------------------------------------------------- nav -- */

  const nav = $('.nav');
  if (nav) {
    const toggle = $('.nav__toggle', nav);
    const setStuck = () => nav.dataset.stuck = String(window.scrollY > 12);
    setStuck();
    addEventListener('scroll', setStuck, { passive: true });

    toggle?.addEventListener('click', () => {
      const open = nav.dataset.open === 'true';
      nav.dataset.open = String(!open);
      toggle.setAttribute('aria-expanded', String(!open));
    });

    $$('.nav__links a', nav).forEach(a => a.addEventListener('click', () => {
      nav.dataset.open = 'false';
      toggle?.setAttribute('aria-expanded', 'false');
    }));

    addEventListener('keydown', e => {
      if (e.key === 'Escape' && nav.dataset.open === 'true') {
        nav.dataset.open = 'false';
        toggle?.setAttribute('aria-expanded', 'false');
        toggle?.focus();
      }
    });
  }

  /* ------------------------------------------------------------- reveal -- */

  const revealTargets = $$('[data-reveal]');
  if (revealTargets.length) {
    const revealAll = () => revealTargets.forEach(el => el.classList.add('is-in'));

    if (reduced.matches || !('IntersectionObserver' in window)) {
      revealAll();
    } else {
      const io = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-in');
          obs.unobserve(entry.target);
        });
      }, { rootMargin: '0px 0px -12% 0px', threshold: .12 });
      revealTargets.forEach(el => io.observe(el));

      /* Safety net. The reveal styles hide everything below the hero until the
         observer says otherwise, so if callbacks never arrive — a stalled
         observer, an odd embedded webview, a headless renderer — the page would
         read as blank. After 2.5s, show everything regardless. */
      setTimeout(() => {
        if (!document.querySelector('[data-reveal].is-in')) {
          io.disconnect();
          revealAll();
        }
      }, 2500);
    }
  }

  /* ---------------------------------------------------------------- sky -- */
  /* Purely decorative floating shapes behind the hero. */

  const sky = $('.hero__sky');
  const layers = [];

  if (sky && !reduced.matches) {
    const palette = ['var(--yellow)', 'var(--pink-soft)', 'var(--blue)',
                     'var(--green)', 'var(--purple)', 'var(--red)'];
    const shapes = ['star', 'dot', 'heart', 'note'];
    const rand = (a, b) => a + Math.random() * (b - a);

    /* The headline, buttons and stats live in the middle column. Decorations
       are confined to bands either side of it (and a strip along the top) so
       nothing ever lands on top of text. */
    const narrow = matchMedia('(max-width: 980px)').matches;
    const bands = narrow
      ? [[2, 22, 4, 96], [78, 98, 4, 96], [24, 76, 1, 11]]
      : [[1, 26, 3, 97], [74, 99, 3, 97], [28, 72, 1, 14]];

    for (let i = 0; i < 24; i++) {
      const [x0, x1, y0, y1] = bands[i % bands.length];
      const el = document.createElement('i');
      el.className = shapes[i % shapes.length];
      el.style.setProperty('--s', `${rand(10, 28)}px`);
      el.style.setProperty('--c', palette[i % palette.length]);
      el.style.setProperty('--o', rand(.3, .7).toFixed(2));
      el.style.left = `${rand(x0, x1)}%`;
      el.style.top = `${rand(y0, y1)}%`;
      sky.appendChild(el);
      layers.push({ el, depth: rand(.02, .12), driftX: rand(-1, 1), phase: rand(0, Math.PI * 2), amp: rand(6, 18) });
    }

    /* Clouds stay in the upper corners, well clear of the logo and headline. */
    const clouds = [[-3, 14, 3, 13], [80, 96, 2, 11], [-6, 10, 20, 30], [84, 99, 18, 27]];
    for (const [x0, x1, y0, y1] of clouds) {
      const el = document.createElement('i');
      el.className = 'cloud';
      el.style.setProperty('--w', `${rand(120, 200)}px`);
      el.style.setProperty('--h', `${rand(40, 62)}px`);
      el.style.left = `${rand(x0, x1)}%`;
      el.style.top = `${rand(y0, y1)}%`;
      sky.appendChild(el);
      layers.push({ el, depth: rand(.03, .07), driftX: rand(-1.4, 1.4), phase: rand(0, 6), amp: rand(4, 10) });
    }
  }

  /* ----------------------------------------------------- parallax + tilt -- */

  const mates = $$('.hero__mate');
  let pointerX = 0, pointerY = 0, heroVisible = true, ticking = false;

  const hero = $('.hero');
  if (hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(([e]) => { heroVisible = e.isIntersecting; }, { threshold: 0 })
      .observe(hero);
  }

  if (!reduced.matches && (layers.length || mates.length)) {
    addEventListener('pointermove', e => {
      pointerX = (e.clientX / innerWidth - .5) * 2;
      pointerY = (e.clientY / innerHeight - .5) * 2;
    }, { passive: true });

    const frame = (t) => {
      if (heroVisible) {
        const y = window.scrollY;
        for (const l of layers) {
          const float = Math.sin(t / 1400 + l.phase) * l.amp;
          l.el.style.transform =
            `translate3d(${pointerX * l.depth * 120 + l.driftX * float}px,` +
            `${-y * l.depth + pointerY * l.depth * 90 + float}px,0)`;
        }
        for (const m of mates) {
          const dir = m.classList.contains('hero__mate--lily') ? 1 : -1;
          m.style.transform =
            `translate3d(${pointerX * 14 * dir}px, ${-y * 0.06 + pointerY * 10}px, 0)`;
        }
      }
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }

  /* --------------------------------------------------------- mate tilt --- */

  if (!reduced.matches && matchMedia('(hover: hover)').matches) {
    $$('.mate').forEach(card => {
      let raf = 0;
      const move = e => {
        if (raf) return;
        raf = requestAnimationFrame(() => {
          raf = 0;
          const r = card.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width - .5;
          const y = (e.clientY - r.top) / r.height - .5;
          card.style.transform =
            `perspective(900px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg) translateY(-6px)`;
        });
      };
      card.addEventListener('pointermove', move);
      card.addEventListener('pointerleave', () => {
        if (raf) cancelAnimationFrame(raf), raf = 0;
        card.style.transform = '';
      });
    });
  }

  /* ------------------------------------------------------------ filters -- */

  const filters = $$('.filter');
  const cards = $$('.grid .card');

  if (filters.length && cards.length) {
    filters.forEach(btn => btn.addEventListener('click', () => {
      const key = btn.dataset.filter;
      filters.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));

      cards.forEach(card => {
        const show = key === 'all' || card.dataset.category === key;
        card.hidden = !show;
        if (show && !reduced.matches) {
          card.animate(
            [{ opacity: 0, transform: 'scale(.94) translateY(14px)' }, { opacity: 1, transform: 'none' }],
            { duration: 320, easing: 'cubic-bezier(.34,1.56,.64,1)' }
          );
        }
      });

      const shown = cards.filter(c => !c.hidden).length;
      const status = $('#filter-status');
      if (status) status.textContent = `${shown} video${shown === 1 ? '' : 's'} shown.`;
    }));
  }

  /* ------------------------------------------------------ video facades -- */
  /* Nothing is requested from YouTube until the visitor asks for it. */

  $$('.card__media[data-video-id]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.videoId;
      if (!id || btn.dataset.loaded === 'true') return;
      btn.dataset.loaded = 'true';

      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}` +
                   `?autoplay=1&rel=0&modestbranding=1&playsinline=1`;
      iframe.title = btn.dataset.videoTitle || 'Rhyme Mates video';
      iframe.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture';
      iframe.allowFullscreen = true;
      iframe.loading = 'eager';

      btn.replaceChildren(iframe);
      btn.style.cursor = 'default';
    }, { once: false });
  });

  /* -------------------------------------------------------- shorts rail -- */

  const rail = $('.rail');
  if (rail && !reduced.matches) {
    let drifting = true;
    let last = performance.now();

    const stop = () => {
      drifting = false;
      ['pointerdown', 'wheel', 'touchstart', 'keydown', 'focusin']
        .forEach(ev => rail.removeEventListener(ev, stop));
    };
    ['pointerdown', 'wheel', 'touchstart', 'keydown', 'focusin']
      .forEach(ev => rail.addEventListener(ev, stop, { passive: true }));

    const drift = (now) => {
      const dt = now - last;
      last = now;
      if (drifting && !rail.matches(':hover')) {
        const max = rail.scrollWidth - rail.clientWidth;
        if (max > 0) {
          rail.scrollLeft += dt * 0.012;
          if (rail.scrollLeft >= max - 1) stop();
        }
      }
      if (drifting) requestAnimationFrame(drift);
    };
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([e], obs) => {
        if (!e.isIntersecting) return;
        obs.disconnect();
        last = performance.now();
        requestAnimationFrame(drift);
      }, { threshold: .4 }).observe(rail);
    }
  }

  /* -------------------------------------------------------- footer year -- */

  const year = $('#year');
  if (year) year.textContent = String(new Date().getFullYear());
})();
