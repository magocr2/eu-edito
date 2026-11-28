/**
 * Eu Edito — Synchronized Live Visual Library Preview, Vector SVG Effects & Cinematic Highlight Engine
 * Matches backend/library_catalog.py, backend/compositor.py & backend/processor.py 1-to-1.
 */
(function (global) {
  const EXAMPLES = {
    'classic': '<small>só que eu</small><strong>FARIA DIFERENTE</strong>',
    'clean-9': '<small>leitura limpa e</small><strong>fluida</strong>',
    'clean-10': '<small>se eu fosse</small><strong>começar</strong>',
    'clean-11': '<small>elegância e</small><strong>sofisticação</strong>',
    'clean-15': '<small>uma forma de</small><strong>imaginar</strong>',
    'clean-lavish': '<small>Essa</small><strong>CAMPANHA</strong>',
    'clean': '<small>composição</small><strong>seguidores</strong>',
    'big-word': '<small>o segredo que muda</small><strong>TUDO</strong><small>na edição</small>',
    'editorial-serif': '<small>deixar cada vídeo</small><strong>PERFEITO</strong><small>acima do rosto</small>',
    'layered-type': '<small>a maioria</small><strong>COMPARAM</strong><small>apenas o preço</small>',
    'pink-highlight': '<small>mas a</small><strong>verdade</strong><small>não é essa</small>',
    'clean-dynamic': '<small>explicação clara e</small><strong>direta</strong><small>na tela</small>',
    'clean-12': '<small>ritmo</small><strong>EM MOVIMENTO</strong>',
    'clean-13': '<small>deslize</small><strong>POR CURIOSIDADE</strong>',
    'highlight-words': '<small>só que eu</small><strong>FARIA DIFERENTE</strong><small>agora mesmo</small>',
    'model-07': '<small>disputar a</small><strong>ATENÇÃO</strong>',
    'clean-14': '<small>Você</small><strong>comemorou</strong>',
  };

  const STYLE_DEFAULTS = {
    'classic': { fx: 'none', animIn: 'slide-up', accent: '#FFFFFF', posY: 74, upper: true },
    'clean-9': { fx: 'none', animIn: 'fade-in', accent: '#FFFFFF', posY: 74, upper: false },
    'clean-10': { fx: 'none', animIn: 'slide-up', accent: '#A375FA', posY: 76, upper: false },
    'clean-11': { fx: 'none', animIn: 'none', accent: '#FFFFFF', posY: 74, upper: false },
    'clean-15': { fx: 'none', animIn: 'slide-up', accent: '#FFFFFF', posY: 74, upper: false },
    'clean-lavish': { fx: 'none', animIn: 'slide-left', accent: '#FFFFFF', posY: 74, upper: true },
    'clean': { fx: 'none', animIn: 'slide-left', accent: '#FFFFFF', posY: 74, upper: false },
    'big-word': { fx: 'none', animIn: 'scale-in', accent: '#FACC15', posY: 32, upper: true },
    'editorial-serif': { fx: 'underline', animIn: 'reveal', accent: '#FFFFFF', posY: 24, upper: true },
    'layered-type': { fx: 'none', animIn: 'stagger', accent: '#FFD66C', posY: 54, upper: true },
    'pink-highlight': { fx: 'pill', animIn: 'slide-right', accent: '#F472B6', posY: 72, upper: false },
    'clean-dynamic': { fx: 'none', animIn: 'fade-in', accent: '#22C55E', posY: 74, upper: false },
    'clean-12': { fx: 'none', animIn: 'pop', accent: '#FFFFFF', posY: 74, upper: true },
    'clean-13': { fx: 'none', animIn: 'slide-left', accent: '#FFFFFF', posY: 74, upper: true },
    'highlight-words': { fx: 'none', animIn: 'pop', accent: '#FACC15', posY: 74, upper: true },
    'model-07': { fx: 'none', animIn: 'pop', accent: '#FFD66C', posY: 74, upper: true },
    'clean-14': { fx: 'none', animIn: 'pop', accent: '#FFDFC4', posY: 74, upper: false },
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
      duration: dMs, delay: delayMs, fill: 'both', easing: 'cubic-bezier(.16,1,.3,1)',
    });
    if (previewExit && animOut && animOut !== 'none') {
      a1.onfinish = () => {
        setTimeout(() => {
          el.animate(keyFramesForAnim(animOut, 'out', intensity), {
            duration: Math.max(140, Math.round(dMs * 0.85)), fill: 'forwards', easing: 'ease-in',
          }).onfinish = () => {
            setTimeout(() => animateElementInOut(el, animIn, animOut, durSec, intensity, false, 0), 160);
          };
        }, 550);
      };
    }
  }

  function triggerCinematicDim(dimEl, spotNodes, cineCfg, durMs = 1100) {
    if (!dimEl) return;
    dimEl.getAnimations?.().forEach((a) => a.cancel());
    const intensity = Math.max(0.15, Math.min(0.80, (Number(cineCfg?.intensity) || 45) / 100));
    const trMs = Math.max(120, Math.min(600, Math.round((Number(cineCfg?.trans_dur) || 0.26) * 1000)));
    const total = Math.max(trMs * 2 + 250, durMs + (Number(cineCfg?.hold_pad) || 0.12) * 1000);
    const inOff = Math.min(0.35, trMs / total);
    const outOff = Math.max(inOff + 0.1, 1 - inOff);
    dimEl.hidden = false;
    dimEl.animate([
      { opacity: 0 },
      { opacity: intensity, offset: inOff },
      { opacity: intensity, offset: outOff },
      { opacity: 0 },
    ], { duration: total, fill: 'forwards', easing: 'ease-in-out' });

    spotNodes.forEach((node) => {
      if (!node) return;
      node.classList.add('is-cine-spot');
      const sc = Math.max(1.0, Math.min(1.45, (Number(cineCfg?.scale) || 116) / 100));
      if (cineCfg?.color) node.style.color = cineCfg.color;
      if (cineCfg?.glow) node.style.textShadow = `0 0 18px ${cineCfg.color || '#ffffff'}, 0 0 30px ${cineCfg.color || '#ffffff'}`;
      node.animate([
        { transform: 'scale(1)' },
        { transform: `scale(${sc.toFixed(2)})`, offset: inOff },
        { transform: `scale(${sc.toFixed(2)})`, offset: outOff },
        { transform: 'scale(1)' },
      ], { duration: total, fill: 'forwards', easing: 'cubic-bezier(.16,1,.3,1)' });
    });
  }

  function injectGraphicEffect(mainNode, fxKind, gfxCfg, fallbackAccent) {
    if (!mainNode || !fxKind || fxKind === 'none') return;
    const cfg = gfxCfg || {};
    const col = cfg.color || fallbackAccent || '#FACC15';
    const thick = Math.max(1.8, Math.min(8, Number(cfg.thickness) || 3.5));
    const lenPct = Math.max(55, Math.min(140, Number(cfg.length_pct || cfg.size_pct || 100)));
    const durMs = Math.max(160, Math.min(900, Math.round((Number(cfg.dur) || 0.36) * 1000)));
    const dy = Math.round((Number(cfg.pos_offset_y) || 0) * 0.45);
    const svgNS = 'http://www.w3.org/2000/svg';

    if (fxKind === 'pill' || fxKind === 'bar' || fxKind === 'hand-mark') {
      const bg = document.createElement('span');
      bg.className = 'hl-bar-bg' + (fxKind === 'hand-mark' ? ' is-hand' : '');
      bg.style.background = col;
      bg.style.animationDuration = durMs + 'ms';
      if (dy) bg.style.transform = `translateY(${dy}px)`;
      mainNode.appendChild(bg);
      return;
    }

    if (fxKind === 'underline' || fxKind === 'underline-double' || fxKind === 'top-bar-line' || fxKind === 'hand-underline') {
      if (fxKind === 'hand-underline') {
        const svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('class', 'hl-svg-underline');
        svg.setAttribute('viewBox', '0 0 120 14');
        svg.setAttribute('preserveAspectRatio', 'none');
        svg.style.width = lenPct + '%';
        svg.style.left = ((100 - lenPct) / 2) + '%';
        svg.style.bottom = (-4 - dy) + 'px';
        const p = document.createElementNS(svgNS, 'path');
        p.setAttribute('d', 'M 2 9 C 35 2, 70 12, 118 5');
        p.style.stroke = col; p.style.strokeWidth = String(Math.max(2, thick * 0.85));
        p.style.animationDuration = durMs + 'ms';
        svg.appendChild(p); mainNode.appendChild(svg);
        return;
      }
      const mkLine = (extraBottom) => {
        const ln = document.createElement('span');
        ln.className = 'hl-underline-line';
        ln.style.height = Math.max(2, Math.round(thick * 0.75)) + 'px';
        ln.style.width = lenPct + '%';
        ln.style.left = ((100 - lenPct) / 2) + '%';
        if (fxKind === 'top-bar-line') ln.style.top = (-3 + dy) + 'px', ln.style.bottom = 'auto';
        else ln.style.bottom = (extraBottom - dy) + 'px';
        ln.style.background = col;
        ln.style.boxShadow = `0 0 8px ${col}`;
        ln.style.transformOrigin = (cfg.direction === 'rtl' ? 'right center' : 'left center');
        ln.style.animationDuration = durMs + 'ms';
        mainNode.appendChild(ln);
      };
      mkLine(-2);
      if (fxKind === 'underline-double') mkLine(-7);
      return;
    }

    if (fxKind === 'strike' || fxKind === 'strike-diag') {
      const ln = document.createElement('span');
      ln.className = 'hl-strike-line' + (fxKind === 'strike-diag' ? ' is-diagonal' : '');
      ln.style.height = Math.max(2, Math.round(thick * 0.8)) + 'px';
      ln.style.width = lenPct + '%';
      ln.style.left = ((100 - lenPct) / 2) + '%';
      ln.style.marginTop = dy + 'px';
      ln.style.background = col;
      ln.style.boxShadow = `0 0 8px ${col}`;
      ln.style.animationDuration = durMs + 'ms';
      mainNode.appendChild(ln);
      return;
    }

    if (fxKind === 'circle' || fxKind === 'circle-open' || fxKind === 'circle-ring' || fxKind === 'hand-circle') {
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('class', 'hl-svg-circle');
      svg.style.transform = `translateY(${dy}px) scale(${(lenPct / 100).toFixed(2)})`;
      svg.setAttribute('viewBox', '0 0 120 56');
      svg.setAttribute('preserveAspectRatio', 'none');
      if (fxKind === 'circle-open') {
        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('d', 'M 18 48 C 2 38, 2 10, 60 5 C 110 3, 118 28, 108 44 C 98 54, 72 54, 52 52');
        path.style.stroke = col; path.style.strokeWidth = String(Math.max(1.8, thick * 0.72));
        path.style.animationDuration = durMs + 'ms';
        svg.appendChild(path);
      } else if (fxKind === 'hand-circle') {
        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('d', 'M 26 6 C 72 1, 118 8, 116 29 C 114 49, 76 54, 48 52 C 12 50, 2 41, 4 27 C 6 12, 34 3, 68 9');
        path.style.stroke = col; path.style.strokeWidth = String(Math.max(1.8, thick * 0.75));
        path.style.animationDuration = durMs + 'ms';
        svg.appendChild(path);
      } else {
        const el = document.createElementNS(svgNS, 'ellipse');
        el.setAttribute('cx', '60'); el.setAttribute('cy', '28');
        el.setAttribute('rx', '56'); el.setAttribute('ry', '24');
        el.style.stroke = col; el.style.strokeWidth = String(Math.max(1.8, thick * 0.72));
        el.style.animationDuration = durMs + 'ms';
        svg.appendChild(el);
        if (fxKind === 'circle-ring') {
          const el2 = document.createElementNS(svgNS, 'ellipse');
          el2.setAttribute('cx', '60'); el2.setAttribute('cy', '28');
          el2.setAttribute('rx', '62'); el2.setAttribute('ry', '28');
          el2.style.stroke = col; el2.style.opacity = '0.55';
          el2.style.strokeWidth = String(Math.max(1.2, thick * 0.45));
          el2.style.animationDuration = (durMs + 90) + 'ms';
          svg.appendChild(el2);
        }
      }
      mainNode.appendChild(svg);
      return;
    }

    if (fxKind.startsWith('arrow')) {
      const dir = cfg.direction || 'left';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('class', `hl-svg-arrow dir-${dir}`);
      svg.setAttribute('viewBox', '0 0 60 40');
      svg.style.marginTop = dy + 'px';
      svg.style.transform = (dir === 'right' ? 'scaleX(-1) ' : '') + `scale(${(lenPct / 100).toFixed(2)})`;
      const p = document.createElementNS(svgNS, 'path');
      let d = 'M 3 4 C 12 30, 32 30, 54 29 L 44 22 M 54 29 L 44 36';
      if (fxKind === 'arrow-straight') d = 'M 3 20 L 54 20 L 43 12 M 54 20 L 43 28';
      else if (fxKind === 'arrow-angled') d = 'M 3 4 L 28 28 L 54 28 L 43 20 M 54 28 L 43 36';
      p.setAttribute('d', d);
      p.style.stroke = col; p.style.strokeWidth = String(Math.max(2, thick * 0.75));
      p.style.animationDuration = durMs + 'ms';
      svg.appendChild(p);
      mainNode.appendChild(svg);
    }
  }

  function buildCaptionHtmlFromData(cap, fallbackStyle, defaultUpper) {
    if (!cap || !cap.text) return EXAMPLES[fallbackStyle] || EXAMPLES.classic;
    const raw = cap.text.trim();
    const mSet = new Set(Array.isArray(cap.main_indices) && cap.main_indices.length ? cap.main_indices : [Number(cap.main_idx ?? 0)]);
    const cSet = new Set(Array.isArray(cap.cine_indices) ? cap.cine_indices : (cap.cine_idx != null ? [Number(cap.cine_idx)] : []));
    const buildToks = (str, startIdx) => str.split(/\s+/).filter(Boolean).map((w, i) => {
      const absI = startIdx + i;
      const esc = w.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const cineCls = cSet.has(absI) ? ' data-cine="1"' : '';
      return mSet.has(absI)
        ? `<strong${cineCls}>${defaultUpper ? esc.toUpperCase() : esc}</strong>`
        : `<small${cineCls}>${esc}</small>`;
    }).join(' ');
    if (raw.includes('|') || raw.includes('\n')) {
      let cursor = 0;
      return raw.split(/[|\n]+/).map((p) => p.trim()).filter(Boolean).map((p) => {
        const html = buildToks(p, cursor);
        cursor += p.split(/\s+/).filter(Boolean).length;
        return `<div class="row-wrap">${html}</div>`;
      }).join('');
    }
    return buildToks(raw, 0);
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
      splitStage.style.setProperty('--split-gap', (Number(comp.gap) ?? 10) + 'px');
      splitStage.style.setProperty('--split-radius', (Number(comp.radius) ?? 18) + 'px');
      splitStage.style.setProperty('--split-accent', comp.accent_color || '#22C55E');
      splitStage.dataset.highlight = comp.highlight_pane || 'a';
      [0, 1].forEach((pi) => {
        const pane = splitStage.querySelector(pi === 0 ? '.pv-split-a' : '.pv-split-b');
        if (!pane) return;
        pane.replaceChildren();
        const m = media[pi];
        if (m && m.previewUrl) {
          const el = document.createElement(m.isImage ? 'img' : 'video');
          el.src = m.previewUrl;
          if (!m.isImage) { el.muted = true; el.loop = true; el.autoplay = true; el.playsInline = true; el.play?.().catch(() => {}); }
          pane.appendChild(el);
        } else pane.innerHTML = `<span class="pv-split-ph">${pi === 0 ? 'Área A' : 'Área B'}</span>`;
      });
      animateElementInOut(splitStage, comp.anim_in || 'reveal', comp.anim_out || 'fade-out', dur, inten);
      return;
    }

    if (type === 'floating-media' && brollLayer) {
      const m0 = media[0];
      if (!m0 || !m0.previewUrl) return;
      const box = computeBoxCss(wrap, comp);
      brollLayer.dataset.layout = 'custom-floating';
      brollLayer.style.cssText = '';
      brollLayer.style.left = box.leftPct.toFixed(2) + '%';
      brollLayer.style.top = box.topPct.toFixed(2) + '%';
      brollLayer.style.width = box.widthPct + '%';
      brollLayer.style.aspectRatio = box.aspectCss;
      brollLayer.style.borderRadius = (Number(comp.radius) ?? 22) + 'px';
      brollLayer.style.transform = Math.abs(box.rotDeg) > 0.25 ? `rotate(${box.rotDeg}deg)` : '';
      const sh = (Number(comp.shadow) ?? 60) / 100;
      brollLayer.style.boxShadow = `0 12px 28px rgba(0,0,0,${(0.75 * sh).toFixed(2)})`;
      brollLayer.hidden = false;
      if (m0.isImage) { brollVid.hidden = true; brollVid.pause?.(); brollImg.src = m0.previewUrl; brollImg.hidden = false; }
      else { brollImg.hidden = true; brollVid.src = m0.previewUrl; brollVid.hidden = false; brollVid.currentTime = 0; brollVid.play?.().catch(() => {}); }
      animateElementInOut(brollLayer, comp.anim_in || 'scale-in', comp.anim_out || 'fade-out', dur, inten);
      return;
    }

    if (cardStage) {
      cardStage.hidden = false;
      cardStage.className = `pv-card-stage comp-${type}`;
      cardStage.style.cssText = '';
      const box = computeBoxCss(wrap, comp, type === 'editorial-card' ? 0.52 : 0.72);
      cardStage.style.left = (type === 'editorial-card' ? box.leftPct : (Number(comp.x) ?? 8)).toFixed(2) + '%';
      cardStage.style.top = (type === 'editorial-card' ? box.topPct : (Number(comp.y) ?? 15)).toFixed(2) + '%';
      cardStage.style.width = (type === 'editorial-card' ? Math.min(88, Number(comp.scale) || 74) : 84) + '%';
      const rotC = Math.max(-30, Math.min(30, Number(comp.rotation) || 0));
      if (type === 'editorial-card' && Math.abs(rotC) > 0.25) cardStage.style.transform = `rotate(${rotC}deg)`;

      const maxCnt = type === 'stacked-cards' ? Math.max(2, Math.min(4, Number(comp.stack_count) || media.length || 3)) : 3;
      const items = (type === 'editorial-card') ? [media[0] || {}] : (media.length ? media.slice(0, maxCnt) : [{}, {}]);
      const labels = Array.isArray(comp.labels) ? comp.labels : [];
      items.forEach((mItem, idx) => {
        const boxEl = document.createElement('div');
        boxEl.className = 'pv-ed-card' + (type === 'stacked-cards' ? ` stack-${idx}` : (type === 'visual-storytelling' ? ` story-${idx}` : ''));
        if (type === 'stacked-cards' && idx > 0) {
          const gapV = Math.max(4, Math.min(24, Number(comp.stack_gap) || 14));
          boxEl.style.marginLeft = Math.min(40, idx * (gapV * 0.9)) + '%';
          boxEl.style.marginTop = (-16 + Math.round(gapV * 0.4)) + 'px';
        }
        boxEl.style.background = comp.bg_color || '#FFFFFF';
        boxEl.style.color = comp.text_color || '#111827';
        boxEl.style.borderRadius = (Number(comp.radius) ?? 20) + 'px';
        const sh = (Number(comp.shadow) ?? 55) / 100;
        boxEl.style.boxShadow = `0 12px 28px rgba(0,0,0,${(0.58 * sh).toFixed(2)})`;
        if (idx === 0 && comp.tag) {
          const tg = document.createElement('span'); tg.className = 'pv-ed-tag'; tg.style.background = comp.accent_color || '#F472B6'; tg.textContent = comp.tag; boxEl.appendChild(tg);
        } else if (idx > 0 && labels[idx]) {
          const tg = document.createElement('span'); tg.className = 'pv-ed-tag'; tg.style.background = comp.accent_color || '#38BDF8'; tg.textContent = labels[idx]; boxEl.appendChild(tg);
        }
        if (idx === 0 && comp.title) { const h = document.createElement('strong'); h.className = 'pv-ed-title'; h.textContent = comp.title; boxEl.appendChild(h); }
        if (mItem && mItem.previewUrl) {
          const im = document.createElement('img'); im.src = mItem.previewUrl; im.className = 'pv-ed-media';
          im.style.borderRadius = Math.max(8, Math.round((Number(comp.radius) ?? 20) * 0.6)) + 'px';
          boxEl.appendChild(im);
        }
        if (idx === 0 && comp.subtitle) { const p = document.createElement('small'); p.className = 'pv-ed-sub'; p.textContent = comp.subtitle; boxEl.appendChild(p); }
        cardStage.appendChild(boxEl);
        const delayMs = (comp.anim_in === 'stagger' || type !== 'editorial-card') ? idx * 140 : 0;
        animateElementInOut(boxEl, comp.anim_in || 'slide-up', comp.anim_out || 'fade-out', dur, inten, false, delayMs);
      });
    }
  }

  function aspectHRatio(aspect) {
    const a = String(aspect || '16/9').toLowerCase();
    if (a === '4/3') return 0.75;
    if (a === '1/1' || a === 'square') return 1.0;
    if (a === '9/16' || a === 'vertical') return 16 / 9;
    if (a === 'portrait') return 1.45;
    return 9 / 16;
  }

  function aspectRatioCSS(aspect) {
    const a = String(aspect || '16/9').toLowerCase();
    if (a === '4/3') return '4 / 3';
    if (a === '1/1' || a === 'square') return '1 / 1';
    if (a === '9/16' || a === 'vertical') return '9 / 16';
    if (a === 'portrait') return '2 / 3';
    return '16 / 9';
  }

  function computeBoxCss(wrapEl, item, intrinsicHRatio) {
    const wrapW = Math.max(120, wrapEl?.clientWidth || 208);
    const wrapH = Math.max(160, wrapEl?.clientHeight || 370);
    const wPct = Math.max(16, Math.min(92, Number(item?.scale ?? 42)));
    const hRatio = Number.isFinite(intrinsicHRatio) && intrinsicHRatio > 0 ? intrinsicHRatio : aspectHRatio(item?.aspect);
    const hPct = Math.min(90, wPct * hRatio * (wrapW / wrapH));
    const marginPct = Math.max(0, Math.min(18, Number(item?.margin ?? 4)));
    const xPct = Math.max(0, Math.min(100, Number(item?.x ?? 8)));
    const yPct = Math.max(0, Math.min(100, Number(item?.y ?? 10)));
    const rotDeg = Math.max(-30, Math.min(30, Number(item?.rotation ?? 0)));
    const leftPct = marginPct + Math.max(0, 100 - wPct - 2 * marginPct) * (xPct / 100);
    const topPct = marginPct + Math.max(0, 100 - hPct - 2 * marginPct) * (yPct / 100);
    return { leftPct, topPct, widthPct: wPct, heightPct: hPct, marginPct, aspectCss: aspectRatioCSS(item?.aspect), rotDeg };
  }

  async function detectVideoFaceZone(videoEl) {
    const fallback = { x: 24, y: 12, w: 52, h: 42, detected: false };
    if (!videoEl || videoEl.hidden || videoEl.readyState < 2 || !videoEl.videoWidth) return fallback;
    try {
      if (typeof window.FaceDetector === 'function') {
        const det = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 2 });
        const faces = await det.detect(videoEl);
        if (faces && faces.length) {
          const b = faces[0].boundingBox;
          const vw = videoEl.videoWidth, vh = videoEl.videoHeight;
          const padX = b.width * 0.28, padY = b.height * 0.28;
          return {
            x: Math.max(0, ((b.x - padX) / vw) * 100),
            y: Math.max(0, ((b.y - padY) / vh) * 100),
            w: Math.min(92, ((b.width + padX * 2) / vw) * 100),
            h: Math.min(72, ((b.height + padY * 2) / vh) * 100),
            detected: true,
          };
        }
      }
      const cv = document.createElement('canvas');
      cv.width = 64; cv.height = 64;
      const ctx = cv.getContext('2d', { willReadFrequently: true });
      if (!ctx) return fallback;
      ctx.drawImage(videoEl, 0, 0, 64, 64);
      const data = ctx.getImageData(0, 0, 64, 64).data;
      let minX = 64, maxX = 0, minY = 64, maxY = 0, hits = 0;
      for (let py = 4; py < 44; py++) {
        for (let px = 12; px < 52; px++) {
          const i = (py * 64 + px) * 4;
          const r = data[i], g = data[i + 1], b = data[i + 2];
          const isSkin = r > 75 && g > 45 && b > 25 && r > g && r > b && (r - Math.min(g, b)) > 16 && (r - g) > 8;
          if (isSkin) {
            hits++;
            if (px < minX) minX = px;
            if (px > maxX) maxX = px;
            if (py < minY) minY = py;
            if (py > maxY) maxY = py;
          }
        }
      }
      if (hits >= 18) {
        const fx = Math.max(4, (minX / 64) * 100 - 8);
        const fy = Math.max(4, (minY / 64) * 100 - 8);
        const fw = Math.min(82, ((maxX - minX + 1) / 64) * 100 + 16);
        const fh = Math.min(62, ((maxY - minY + 1) / 64) * 100 + 16);
        return { x: fx, y: fy, w: Math.max(28, fw), h: Math.max(24, fh), detected: true };
      }
    } catch {}
    return fallback;
  }

  function boxesOverlap(a, b) {
    return a.x < (b.x + b.w) && (a.x + a.w) > b.x && a.y < (b.y + b.h) && (a.y + a.h) > b.y;
  }

  function computeOverlapWarnings(itemBox, faceBox, capPosY) {
    const capBand = { x: 10, y: Math.max(0, Number(capPosY || 74) - 9), w: 80, h: 18 };
    const faceHit = !!(faceBox && boxesOverlap(itemBox, faceBox));
    const capHit = boxesOverlap(itemBox, capBand);
    const parts = [];
    if (faceHit) parts.push('cobrindo o rosto');
    if (capHit) parts.push('sobrepondo a legenda');
    return {
      faceOverlap: faceHit,
      capOverlap: capHit,
      hasOverlap: faceHit || capHit,
      message: parts.length ? `⚠️ Atenção: este elemento está ${parts.join(' e ')}.` : '',
    };
  }

  function pickSmartSafeSlot(wrapEl, existingBoxes, faceBox, capPosY, itemCfg) {
    const candidates = [
      [100, 0], [0, 0], [100, 46], [0, 46], [100, 100], [0, 100], [50, 0], [50, 100],
    ];
    let best = { x: 100, y: 0, score: 9999 };
    for (const [cx, cy] of candidates) {
      const css = computeBoxCss(wrapEl, { ...itemCfg, x: cx, y: cy });
      const b = { x: css.leftPct, y: css.topPct, w: css.widthPct, h: css.heightPct };
      const w = computeOverlapWarnings(b, faceBox, capPosY);
      let score = (w.faceOverlap ? 100 : 0) + (w.capOverlap ? 60 : 0);
      for (const ex of (existingBoxes || [])) {
        if (boxesOverlap(b, ex)) score += 35;
      }
      if (score === 0) return { x: cx, y: cy };
      if (score < best.score) best = { x: cx, y: cy, score };
    }
    return { x: best.x, y: best.y };
  }

  global.EuEditoPreview = {
    EXAMPLES, STYLE_DEFAULTS, FONT_CSS_MAP,
    animateElementInOut, triggerCinematicDim, injectGraphicEffect,
    buildCaptionHtmlFromData, renderCompositionStage,
    computeBoxCss, aspectRatioCSS, detectVideoFaceZone, computeOverlapWarnings, pickSmartSafeSlot,
  };
})(window);
