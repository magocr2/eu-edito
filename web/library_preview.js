/**
 * Eu Edito — Live Visual Library Preview & Animation Engine
 * Mirrors backend/library_catalog.py & backend/compositor.py 1-to-1 in the browser.
 */
(function (global) {
  const EXAMPLES = {
    'big-word': '<small>o segredo que muda</small><strong>TUDO</strong><small>na edição</small>',
    'editorial-serif': '<small>tenta deixar o vídeo</small><strong>PERFEITO</strong><small>em cada detalhe</small>',
    'layered-type': '<small>a maioria</small><strong>COMPARAM</strong><small>apenas o preço</small>',
    'pink-highlight': '<small>mas a</small><strong>verdade</strong><small>não é essa</small>',
    'clean-dynamic': '<small>explicação clara e</small><strong>direta</strong><small>na tela</small>',
    'highlight-words': '<small>só que eu</small><strong>FARIA DIFERENTE</strong><small>agora mesmo</small>',
  };

  const STYLE_DEFAULTS = {
    'big-word': { fx: 'none', animIn: 'scale-in', accent: '#FACC15', posY: 32 },
    'editorial-serif': { fx: 'underline', animIn: 'reveal', accent: '#FFFFFF', posY: 24 },
    'layered-type': { fx: 'none', animIn: 'stagger', accent: '#FFD66C', posY: 54 },
    'pink-highlight': { fx: 'pill', animIn: 'slide-right', accent: '#F472B6', posY: 72 },
    'clean-dynamic': { fx: 'none', animIn: 'fade-in', accent: '#22C55E', posY: 74 },
    'highlight-words': { fx: 'none', animIn: 'pop', accent: '#FACC15', posY: 74 },
  };

  const FONT_CSS_MAP = {
    'bebas': ["'BebasNeue', sans-serif", 'normal', '400'],
    'coolvetica': ["'Coolvetica', sans-serif", 'normal', '400'],
    'lucette': ["'Lucette', Georgia, serif", 'normal', '400'],
    'creato-bold-italic': ["'CreatoBoldItalic', 'CreatoDisplay', sans-serif", 'italic', '700'],
    'creato-extrabold-italic': ["'CreatoExtraBoldItalic', 'CreatoDisplay', sans-serif", 'italic', '800'],
    'creato-extrabold': ["'CreatoExtraBold', 'CreatoDisplay', sans-serif", 'normal', '800'],
    'apple-garamond': ["'AppleGaramond', Georgia, serif", 'italic', '400'],
    'apple-garamond-bold': ["'AppleGaramondBold', 'AppleGaramond', Georgia, serif", 'italic', '700'],
    'apple-garamond-light': ["'AppleGaramondLight', 'AppleGaramond', Georgia, serif", 'italic', '300'],
    'lavish': ["'Lavish', Georgia, serif", 'normal', '400'],
    'geist': ["'Geist', sans-serif", 'normal', '700'],
    'dm-sans': ["'DMSans', sans-serif", 'normal', '800'],
    'creato-regular': ["'CreatoDisplay', sans-serif", 'normal', '400'],
    'creato-light': ["'CreatoLight', 'CreatoDisplay', sans-serif", 'normal', '300'],
    'creato-medium': ["'CreatoMedium', 'CreatoDisplay', sans-serif", 'normal', '500'],
  };

  function keyFramesForAnim(kind, dir, intensity) {
    const k = (kind || 'fade-in').toLowerCase();
    const s = Math.max(0.35, Math.min(1.6, Number(intensity) || 1.0));
    const px = Math.round(28 * s);
    if (k === 'none') return [{ opacity: 1 }, { opacity: 1 }];
    if (dir === 'out') {
      if (k === 'scale-in') return [{ opacity: 1, transform: 'scale(1)' }, { opacity: 0, transform: `scale(${Math.max(0.6, 1 - 0.18 * s).toFixed(2)})` }];
      if (k === 'slide-up') return [{ opacity: 1, transform: 'translateY(0)' }, { opacity: 0, transform: `translateY(-${px}px)` }];
      if (k === 'slide-down') return [{ opacity: 1, transform: 'translateY(0)' }, { opacity: 0, transform: `translateY(${px}px)` }];
      if (k === 'slide-left') return [{ opacity: 1, transform: 'translateX(0)' }, { opacity: 0, transform: `translateX(-${px}px)` }];
      if (k === 'slide-right') return [{ opacity: 1, transform: 'translateX(0)' }, { opacity: 0, transform: `translateX(${px}px)` }];
      if (k === 'reveal') return [{ clipPath: 'inset(0 0% 0 0)', opacity: 1 }, { clipPath: 'inset(0 0 0 100%)', opacity: 0 }];
      return [{ opacity: 1 }, { opacity: 0 }];
    }
    if (k === 'scale-in') return [{ opacity: 0, transform: `scale(${Math.max(0.55, 1 - 0.25 * s).toFixed(2)})` }, { opacity: 1, transform: 'scale(1)' }];
    if (k === 'slide-up') return [{ opacity: 0, transform: `translateY(${px}px)` }, { opacity: 1, transform: 'translateY(0)' }];
    if (k === 'slide-down') return [{ opacity: 0, transform: `translateY(-${px}px)` }, { opacity: 1, transform: 'translateY(0)' }];
    if (k === 'slide-left') return [{ opacity: 0, transform: `translateX(${Math.round(px * 1.4)}px)` }, { opacity: 1, transform: 'translateX(0)' }];
    if (k === 'slide-right') return [{ opacity: 0, transform: `translateX(-${Math.round(px * 1.4)}px)` }, { opacity: 1, transform: 'translateX(0)' }];
    if (k === 'pop') return [
      { opacity: 0, transform: `scale(${Math.max(0.5, 1 - 0.26 * s).toFixed(2)})` },
      { opacity: 1, transform: `scale(${(1 + 0.06 * s).toFixed(2)})`, offset: 0.65 },
      { opacity: 1, transform: 'scale(1)' },
    ];
    if (k === 'reveal') return [{ clipPath: 'inset(0 100% 0 0)', opacity: 0.4 }, { clipPath: 'inset(0 0% 0 0)', opacity: 1 }];
    if (k === 'draw') return [{ opacity: 0.2, filter: 'blur(3px)' }, { opacity: 1, filter: 'blur(0)' }];
    if (k === 'stagger') return [{ opacity: 0, transform: `translateY(${Math.round(px * 0.6)}px)` }, { opacity: 1, transform: 'translateY(0)' }];
    return [{ opacity: 0 }, { opacity: 1 }];
  }

  function animateElementInOut(el, animIn, animOut, durSec, intensity, previewExit = false, delayMs = 0) {
    if (!el || typeof el.animate !== 'function') return;
    el.getAnimations?.().forEach((a) => a.cancel());
    const dMs = Math.max(120, Math.min(850, Math.round((Number(durSec) || 0.28) * 1000)));
    const a1 = el.animate(keyFramesForAnim(animIn, 'in', intensity), {
      duration: dMs,
      delay: delayMs,
      fill: 'both',
      easing: 'cubic-bezier(.16,1,.3,1)',
    });
    if (previewExit && animOut && animOut !== 'none') {
      a1.onfinish = () => {
        setTimeout(() => {
          el.animate(keyFramesForAnim(animOut, 'out', intensity), {
            duration: Math.max(140, Math.round(dMs * 0.85)),
            fill: 'forwards',
            easing: 'ease-in',
          }).onfinish = () => {
            setTimeout(() => animateElementInOut(el, animIn, animOut, durSec, intensity, false, 0), 160);
          };
        }, 550);
      };
    }
  }

  function injectGraphicEffect(mainNode, fxKind, gfxCfg, fallbackAccent) {
    if (!mainNode || !fxKind || fxKind === 'none') return;
    const cfg = gfxCfg || {};
    const col = cfg.color || fallbackAccent || '#FACC15';
    const thick = Math.max(1.8, Math.min(8, Number(cfg.thickness) || 3.5));
    const lenPct = Math.max(55, Math.min(140, Number(cfg.length_pct || cfg.size_pct || 100)));
    const durMs = Math.max(160, Math.min(900, Math.round((Number(cfg.dur) || 0.36) * 1000)));
    const svgNS = 'http://www.w3.org/2000/svg';

    if (fxKind === 'pill' || fxKind === 'bar') {
      const bg = document.createElement('span');
      bg.className = 'hl-bar-bg';
      bg.style.background = col;
      bg.style.animationDuration = durMs + 'ms';
      mainNode.appendChild(bg);
      return;
    }

    if (fxKind === 'underline') {
      const ln = document.createElement('span');
      ln.className = 'hl-underline-line';
      ln.style.height = Math.max(2, Math.round(thick * 0.8)) + 'px';
      ln.style.width = lenPct + '%';
      ln.style.left = ((100 - lenPct) / 2) + '%';
      ln.style.background = col;
      ln.style.boxShadow = `0 0 8px ${col}`;
      ln.style.transformOrigin = (cfg.direction === 'rtl' ? 'right center' : 'left center');
      ln.style.animationDuration = durMs + 'ms';
      mainNode.appendChild(ln);
      return;
    }

    if (fxKind === 'strike') {
      const ln = document.createElement('span');
      ln.className = 'hl-strike-line';
      ln.style.height = Math.max(2, Math.round(thick * 0.8)) + 'px';
      ln.style.background = col;
      ln.style.boxShadow = `0 0 8px ${col}`;
      ln.style.animationDuration = durMs + 'ms';
      if (cfg.angle === 'diagonal') ln.classList.add('is-diagonal');
      mainNode.appendChild(ln);
      return;
    }

    if (fxKind === 'circle') {
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('class', 'hl-svg-circle');
      const sc = lenPct / 100;
      svg.style.transform = `scale(${sc.toFixed(2)})`;
      svg.setAttribute('viewBox', '0 0 120 56');
      svg.setAttribute('preserveAspectRatio', 'none');
      const complete = cfg.complete !== false;
      if (complete) {
        const el = document.createElementNS(svgNS, 'ellipse');
        el.setAttribute('cx', '60'); el.setAttribute('cy', '28');
        el.setAttribute('rx', '56'); el.setAttribute('ry', '24');
        el.style.stroke = col;
        el.style.strokeWidth = String(Math.max(1.8, thick * 0.72));
        el.style.animationDuration = durMs + 'ms';
        svg.appendChild(el);
      } else {
        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('d', 'M 18 48 C 2 38, 2 10, 60 5 C 110 3, 118 28, 108 44 C 98 54, 72 54, 52 52');
        path.style.stroke = col;
        path.style.strokeWidth = String(Math.max(1.8, thick * 0.72));
        path.style.animationDuration = durMs + 'ms';
        svg.appendChild(path);
      }
      mainNode.appendChild(svg);
      return;
    }

    if (fxKind === 'arrow') {
      const dir = cfg.direction || 'left';
      const shape = cfg.shape || 'curved';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('class', `hl-svg-arrow dir-${dir}`);
      svg.setAttribute('viewBox', '0 0 60 40');
      const p = document.createElementNS(svgNS, 'path');
      let d = 'M 3 4 C 12 30, 32 30, 54 29 L 44 22 M 54 29 L 44 36';
      if (shape === 'straight') d = 'M 3 20 L 54 20 L 43 12 M 54 20 L 43 28';
      else if (shape === 'angled') d = 'M 3 4 L 28 28 L 54 28 L 43 20 M 54 28 L 43 36';
      p.setAttribute('d', d);
      p.style.stroke = col;
      p.style.strokeWidth = String(Math.max(2, thick * 0.75));
      p.style.animationDuration = durMs + 'ms';
      svg.appendChild(p);
      mainNode.appendChild(svg);
    }
  }

  function buildCaptionHtmlFromData(cap, fallbackStyle, defaultUpper) {
    if (!cap || !cap.text) return EXAMPLES[fallbackStyle] || EXAMPLES['highlight-words'];
    const raw = cap.text.trim();
    const mSet = new Set(Array.isArray(cap.main_indices) && cap.main_indices.length
      ? cap.main_indices
      : [Number(cap.main_idx ?? 0)]);

    const buildToks = (str, startIdx) => str.split(/\s+/).filter(Boolean).map((w, i) => {
      const absI = startIdx + i;
      const esc = w.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return mSet.has(absI)
        ? `<strong>${defaultUpper ? esc.toUpperCase() : esc}</strong>`
        : `<small>${esc}</small>`;
    }).join(' ');

    if (raw.includes('|') || raw.includes('\n')) {
      const parts = raw.split(/[|\n]+/).map((p) => p.trim()).filter(Boolean);
      let cursor = 0;
      return parts.map((p) => {
        const html = buildToks(p, cursor);
        cursor += p.split(/\s+/).filter(Boolean).length;
        return `<div class="row-wrap">${html}</div>`;
      }).join('');
    }
    const toks = raw.split(/\s+/).filter(Boolean);
    return toks.map((w, i) => {
      const esc = w.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return mSet.has(i) ? `<strong>${defaultUpper ? esc.toUpperCase() : esc}</strong>` : `<small>${esc}</small>`;
    }).join('');
  }

  function renderCompositionStage(comp, refs) {
    const { wrap, brollLayer, brollImg, brollVid, splitStage, cardStage } = refs;
    if (!comp || !wrap) return;
    if (brollLayer) brollLayer.hidden = true;
    if (splitStage) splitStage.hidden = true;
    if (cardStage) { cardStage.hidden = true; cardStage.replaceChildren(); }
    wrap.classList.remove('split-top', 'split-bottom');

    const type = (comp.type || 'floating-media').toLowerCase();
    const media = comp.media || [];
    const dur = Number(comp.anim_dur) || 0.34;
    const inten = Number(comp.anim_intensity) || 1.0;

    if (type === 'split-composition' && splitStage) {
      splitStage.hidden = false;
      splitStage.dataset.orient = comp.orientation || 'vertical';
      const ratio = Math.max(30, Math.min(70, Number(comp.split_ratio) || 50));
      splitStage.style.setProperty('--split-a', ratio + '%');
      splitStage.style.setProperty('--split-b', (100 - ratio) + '%');
      splitStage.style.setProperty('--split-gap', (Number(comp.gap) ?? 10) + 'px');
      splitStage.style.setProperty('--split-radius', (Number(comp.radius) ?? 18) + 'px');
      splitStage.style.setProperty('--split-accent', comp.accent_color || '#22C55E');
      splitStage.dataset.highlight = comp.highlight_pane || 'a';
      const paneA = splitStage.querySelector('.pv-split-a');
      const paneB = splitStage.querySelector('.pv-split-b');
      if (paneA) {
        paneA.replaceChildren();
        const m0 = media[0];
        if (m0 && m0.previewUrl) {
          const el = document.createElement(m0.isImage ? 'img' : 'video');
          el.src = m0.previewUrl;
          if (!m0.isImage) { el.muted = true; el.loop = true; el.autoplay = true; el.playsInline = true; el.play?.().catch(() => {}); }
          paneA.appendChild(el);
        } else {
          paneA.innerHTML = '<span class="pv-split-ph">Área A (Mídia)</span>';
        }
      }
      if (paneB) {
        paneB.replaceChildren();
        const m1 = media[1];
        if (m1 && m1.previewUrl) {
          const el = document.createElement(m1.isImage ? 'img' : 'video');
          el.src = m1.previewUrl;
          if (!m1.isImage) { el.muted = true; el.loop = true; el.autoplay = true; el.playsInline = true; el.play?.().catch(() => {}); }
          paneB.appendChild(el);
        } else {
          paneB.innerHTML = '<span class="pv-split-ph">Área B (Principal)</span>';
        }
      }
      animateElementInOut(splitStage, comp.anim_in || 'reveal', comp.anim_out || 'fade-out', dur, inten);
      return;
    }

    if (type === 'floating-media' && brollLayer) {
      const m0 = media[0];
      if (!m0 || !m0.previewUrl) return;
      brollLayer.dataset.layout = 'custom-floating';
      brollLayer.style.left = (Number(comp.x) ?? 8) + '%';
      brollLayer.style.top = (Number(comp.y) ?? 9) + '%';
      brollLayer.style.width = (Number(comp.scale) || 40) + '%';
      brollLayer.style.height = Math.round((Number(comp.scale) || 40) * 0.62) + '%';
      brollLayer.style.borderRadius = (Number(comp.radius) ?? 22) + 'px';
      const sh = (Number(comp.shadow) ?? 60) / 100;
      brollLayer.style.boxShadow = `0 12px 28px rgba(0,0,0,${(0.75 * sh).toFixed(2)})`;
      brollLayer.hidden = false;
      if (m0.isImage) {
        brollVid.hidden = true; brollVid.pause?.();
        brollImg.src = m0.previewUrl; brollImg.hidden = false;
      } else {
        brollImg.hidden = true;
        brollVid.src = m0.previewUrl; brollVid.hidden = false;
        brollVid.currentTime = 0; brollVid.play?.().catch(() => {});
      }
      animateElementInOut(brollLayer, comp.anim_in || 'scale-in', comp.anim_out || 'fade-out', dur, inten);
      return;
    }

    if (cardStage) {
      cardStage.hidden = false;
      cardStage.className = `pv-card-stage comp-${type}`;
      cardStage.style.left = type === 'editorial-card' ? ((100 - Math.min(88, Number(comp.scale) || 74)) / 2) + '%' : (Number(comp.x) ?? 8) + '%';
      cardStage.style.top = (Number(comp.y) ?? 15) + '%';
      cardStage.style.width = type === 'editorial-card' ? Math.min(88, Number(comp.scale) || 74) + '%' : '84%';

      const items = (type === 'editorial-card') ? [media[0] || {}] : (media.length ? media.slice(0, 3) : [{}, {}]);
      const labels = Array.isArray(comp.labels) ? comp.labels : [];
      items.forEach((mItem, idx) => {
        const box = document.createElement('div');
        box.className = 'pv-ed-card' + (type === 'stacked-cards' ? ` stack-${idx}` : (type === 'visual-storytelling' ? ` story-${idx}` : ''));
        box.style.background = comp.bg_color || '#FFFFFF';
        box.style.color = comp.text_color || '#111827';
        box.style.borderRadius = (Number(comp.radius) ?? 20) + 'px';
        const sh = (Number(comp.shadow) ?? 55) / 100;
        box.style.boxShadow = `0 12px 28px rgba(0,0,0,${(0.58 * sh).toFixed(2)})`;

        if (idx === 0 && comp.tag) {
          const tg = document.createElement('span');
          tg.className = 'pv-ed-tag';
          tg.style.background = comp.accent_color || '#F472B6';
          tg.textContent = comp.tag;
          box.appendChild(tg);
        } else if (idx > 0 && labels[idx]) {
          const tg = document.createElement('span');
          tg.className = 'pv-ed-tag';
          tg.style.background = comp.accent_color || '#38BDF8';
          tg.textContent = labels[idx];
          box.appendChild(tg);
        }

        if ((idx === 0 && comp.title) || (idx > 0 && !labels[idx] && comp.labels?.[idx])) {
          const h = document.createElement('strong');
          h.className = 'pv-ed-title';
          h.textContent = idx === 0 ? comp.title : comp.labels[idx];
          box.appendChild(h);
        }

        if (mItem && mItem.previewUrl) {
          const im = document.createElement('img');
          im.src = mItem.previewUrl;
          im.className = 'pv-ed-media';
          im.style.borderRadius = Math.max(8, Math.round((Number(comp.radius) ?? 20) * 0.6)) + 'px';
          box.appendChild(im);
        }

        if (idx === 0 && comp.subtitle) {
          const p = document.createElement('small');
          p.className = 'pv-ed-sub';
          p.textContent = comp.subtitle;
          box.appendChild(p);
        }
        cardStage.appendChild(box);
        const delayMs = (comp.anim_in === 'stagger' || type !== 'editorial-card') ? idx * 140 : 0;
        animateElementInOut(box, comp.anim_in || 'slide-up', comp.anim_out || 'fade-out', dur, inten, false, delayMs);
      });
    }
  }

  global.EuEditoPreview = {
    EXAMPLES,
    STYLE_DEFAULTS,
    FONT_CSS_MAP,
    animateElementInOut,
    injectGraphicEffect,
    buildCaptionHtmlFromData,
    renderCompositionStage,
  };
})(window);
