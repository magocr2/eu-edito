/* Eu Edito — Motion Director v3 Frontend Module (Face-Safe, Script-Driven, Frameless) */
(function () {
  const $ = (id) => document.getElementById(id);

  let catalog = { categories: [], templates: [] };
  let suggestions = [];
  let layers = [];
  let activeEditIdx = -1;

  function loadCatalog() {
    return fetch('/api/motion/catalog')
      .then((r) => r.json())
      .then((data) => {
        if (data && Array.isArray(data.templates)) catalog = data;
      })
      .catch(() => {});
  }
  loadCatalog();

  function ease(t, mode) {
    const u = Math.max(0, Math.min(1, t));
    if (mode === 'spring') {
      if (u < 0.68) {
        const s = u / 0.68;
        return 1.08 * (1 - Math.pow(1 - s, 3));
      }
      const s = (u - 0.68) / 0.32;
      return 1.08 - 0.08 * (s * s * (3 - 2 * s));
    }
    if (mode === 'smooth') return u * u * (3 - 2 * u);
    return 1 - Math.pow(1 - u, 3);
  }

  function roundRect(ctx, x, y, w, h, r) {
    const ww = Math.max(2, w);
    const hh = Math.max(2, h);
    ctx.beginPath();
    ctx.roundRect(x, y, ww, hh, Math.min(r, ww / 2, hh / 2));
  }

  function hexRgba(hex, a) {
    const clean = String(hex || '#22C55E').replace('#', '');
    if (clean.length !== 6) return `rgba(34,197,94,${a})`;
    const r = parseInt(clean.slice(0, 2), 16) || 34;
    const g = parseInt(clean.slice(2, 4), 16) || 197;
    const b = parseInt(clean.slice(4, 6), 16) || 94;
    return `rgba(${r},${g},${b},${a})`;
  }

  function drawGlassPill(ctx, x, y, w, h, r, accent, glow = true, tint = null) {
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,0.55)';
    ctx.shadowBlur = 10;
    ctx.shadowOffsetY = 3;
    roundRect(ctx, x, y, w, h, r);
    ctx.fillStyle = tint || 'rgba(12, 18, 28, 0.78)';
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = glow ? hexRgba(accent, 0.78) : 'rgba(255,255,255,0.20)';
    ctx.lineWidth = glow ? 1.4 : 1;
    ctx.stroke();
    ctx.restore();
  }

  function drawMixedHeadline(ctx, x, y, title, accentText, accent, sc, centered = false) {
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 8;
    ctx.fillStyle = '#ffffff';
    const fMain = `800 ${Math.max(10, Math.round(17 * sc))}px 'CreatoDisplay', sans-serif`;
    const fItal = `italic 700 ${Math.max(10, Math.round(17.5 * sc))}px 'AppleGaramond', Georgia, serif`;
    ctx.font = fMain;
    ctx.textAlign = centered ? 'center' : 'left';
    ctx.fillText(String(title || '').slice(0, 26), x, y);
    if (accentText) {
      ctx.font = fItal;
      ctx.fillStyle = accent;
      if (centered) {
        ctx.fillText(String(accentText).slice(0, 22), x, y + Math.round(15 * sc));
      } else {
        ctx.font = fMain;
        const tw = ctx.measureText(String(title || '').slice(0, 26)).width;
        ctx.font = fItal;
        const ax = x + tw + 6 * sc;
        if (ax < ctx.canvas.width * 0.76) {
          ctx.fillText(String(accentText).slice(0, 20), ax, y);
        } else {
          ctx.fillText(String(accentText).slice(0, 24), x, y + Math.round(14 * sc));
        }
      }
    }
    ctx.restore();
  }

  function drawVectorIcon(ctx, iconId, cx, cy, r, accent, animP, tSec) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = hexRgba(accent, 0.22);
    ctx.fill();
    ctx.strokeStyle = accent;
    ctx.lineWidth = 1.6;
    ctx.stroke();

    ctx.strokeStyle = '#ffffff';
    ctx.fillStyle = '#ffffff';
    ctx.lineWidth = 2;
    if (iconId === 'clock') {
      ctx.beginPath(); ctx.arc(cx, cy, r * 0.54, 0, Math.PI * 2); ctx.stroke();
      const ang = -Math.PI / 2 + Math.PI * 2 * ((animP + tSec * 0.3) % 1);
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(ang) * r * 0.36, cy + Math.sin(ang) * r * 0.36); ctx.stroke();
    } else if (iconId === 'check') {
      ctx.beginPath(); ctx.moveTo(cx - r * 0.34, cy); ctx.lineTo(cx - r * 0.08, cy + r * 0.28); ctx.lineTo(cx + r * 0.36, cy - r * 0.26); ctx.stroke();
    } else if (iconId === 'pen') {
      ctx.beginPath();
      ctx.moveTo(cx - r * 0.32, cy + r * 0.28);
      ctx.lineTo(cx + r * 0.30, cy - r * 0.34);
      ctx.stroke();
      ctx.beginPath(); ctx.arc(cx - r * 0.32, cy + r * 0.28, 2.5, 0, Math.PI * 2); ctx.fillStyle = accent; ctx.fill();
    } else if (iconId === 'bolt') {
      ctx.beginPath();
      ctx.moveTo(cx + r * 0.1, cy - r * 0.45);
      ctx.lineTo(cx - r * 0.25, cy + r * 0.04);
      ctx.lineTo(cx + r * 0.04, cy + r * 0.04);
      ctx.lineTo(cx - r * 0.1, cy + r * 0.45);
      ctx.closePath();
      ctx.fillStyle = accent; ctx.fill();
    } else if (iconId === 'rocket') {
      ctx.beginPath();
      ctx.moveTo(cx + r * 0.35, cy - r * 0.35);
      ctx.lineTo(cx - r * 0.2, cy + r * 0.25);
      ctx.lineTo(cx - r * 0.32, cy + r * 0.08);
      ctx.closePath();
      ctx.fill();
    } else {
      // Sparkle star
      ctx.beginPath();
      ctx.moveTo(cx, cy - r * 0.48); ctx.lineTo(cx + r * 0.14, cy - r * 0.14);
      ctx.lineTo(cx + r * 0.48, cy); ctx.lineTo(cx + r * 0.14, cy + r * 0.14);
      ctx.lineTo(cx, cy + r * 0.48); ctx.lineTo(cx - r * 0.14, cy + r * 0.14);
      ctx.lineTo(cx - r * 0.48, cy); ctx.lineTo(cx - r * 0.14, cy - r * 0.14);
      ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }

  function drawMotionCanvas(canvas, tplId, params, prog, tSec) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const p = params || {};
    const accent = p.accent_color || '#22C55E';
    const easingMode = p.easing || 'spring';
    const enterP = ease(Math.min(1, prog / 0.18), easingMode);
    const exitP = ease(Math.min(1, (1 - prog) / 0.14), 'smooth');
    const alphaEnv = Math.max(0, Math.min(1, Math.min(enterP, exitP)));
    const animP = ease(Math.max(0, Math.min(1, (prog - 0.04) / 0.68)), easingMode);
    const sc = w / 400;
    const dy = (1 - enterP) * 14 * sc + Math.sin(tSec * 2.6) * 2.2 * sc;

    ctx.save();
    ctx.globalAlpha = alphaEnv;

    // Soft radial backdrop cushion ONLY (no ugly boxy rectangle border!)
    const rg = ctx.createRadialGradient(w * 0.5, h * 0.52 + dy, w * 0.06, w * 0.5, h * 0.52 + dy, w * 0.48);
    rg.addColorStop(0, 'rgba(6, 10, 16, 0.72)');
    rg.addColorStop(0.75, 'rgba(6, 10, 16, 0.28)');
    rg.addColorStop(1, 'rgba(6, 10, 16, 0)');
    ctx.fillStyle = rg;
    ctx.fillRect(0, 0, w, h);

    const title = String(p.title || 'Destaque da Fala');
    const accentText = String(p.accent_text || '');
    const metric = String(p.metric || '');
    const iconId = String(p.icon || 'spark');
    const labels = Array.isArray(p.labels) && p.labels.length ? p.labels : ['Item 1', 'Item 2', 'Item 3'];
    const vals = Array.isArray(p.values) && p.values.length ? p.values.map(Number) : [28, 64, 96];
    const points = Array.isArray(p.points) ? p.points : [];

    if (tplId === 'sketch_calligraphy') {
      // Paper sheet on left + animated cursive pen wave
      drawGlassPill(ctx, 16 * sc, 20 * sc + dy, 105 * sc, h - 42 * sc, 10 * sc, accent, true, 'rgba(245,247,252,0.92)');
      ctx.strokeStyle = 'rgba(140,165,195,0.45)'; ctx.lineWidth = 1;
      for (let ln = 0; ln < 3; ln++) {
        const ly = (44 + ln * 24) * sc + dy;
        ctx.beginPath(); ctx.moveTo(26 * sc, ly); ctx.lineTo(110 * sc, ly); ctx.stroke();
      }
      ctx.beginPath();
      const steps = 28;
      const nDraw = Math.max(2, Math.floor(steps * animP));
      for (let i = 0; i < nDraw; i++) {
        const u = i / (steps - 1);
        const cxw = (28 + 78 * u) * sc;
        const cyw = (68 * sc + dy) - Math.sin(u * Math.PI * 3) * 14 * sc;
        i === 0 ? ctx.moveTo(cxw, cyw) : ctx.lineTo(cxw, cyw);
      }
      ctx.strokeStyle = accent; ctx.lineWidth = 2.6 * sc; ctx.stroke();

      const rx = 136 * sc;
      drawMixedHeadline(ctx, rx, 44 * sc + dy, title, accentText, accent, sc);
      labels.slice(0, 3).forEach((lbl, idx) => {
        if (animP < idx * 0.2) return;
        const px = rx + idx * 78 * sc;
        const py = 74 * sc + dy;
        drawGlassPill(ctx, px, py, 72 * sc, 24 * sc, 12 * sc, accent, true);
        ctx.fillStyle = '#fff'; ctx.font = `700 ${Math.max(8, Math.round(9.5 * sc))}px sans-serif`; ctx.textAlign = 'center';
        ctx.fillText(String(lbl).slice(0, 10), px + 36 * sc, py + 15 * sc);
      });
      ctx.textAlign = 'left';
      if (points[0]) {
        drawGlassPill(ctx, rx, 112 * sc + dy, w - rx - 16 * sc, 28 * sc, 10 * sc, accent, false);
        ctx.fillStyle = '#e2e8f0'; ctx.font = `600 ${Math.max(8, Math.round(10 * sc))}px sans-serif`;
        ctx.fillText(String(points[0]).slice(0, 32), rx + 10 * sc, 130 * sc + dy);
      }
    } else if (tplId === 'kinetic_timer') {
      const cx = 74 * sc, cy = h * 0.5 + dy, r = 44 * sc;
      drawGlassPill(ctx, cx - r, cy - r, r * 2, r * 2, r, accent, false);
      ctx.beginPath(); ctx.arc(cx, cy, r - 6 * sc, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * animP);
      ctx.strokeStyle = accent; ctx.lineWidth = 5 * sc; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = `800 ${Math.round(13 * sc)}px sans-serif`; ctx.textAlign = 'center';
      ctx.fillText(metric.slice(0, 8), cx, cy + 4 * sc);
      ctx.textAlign = 'left';

      const rx = 136 * sc;
      drawMixedHeadline(ctx, rx, 46 * sc + dy, title, accentText, accent, sc);
      labels.slice(0, 5).forEach((lbl, idx) => {
        const lit = animP >= idx / 5;
        const px = rx + idx * 48 * sc, py = 78 * sc + dy;
        drawGlassPill(ctx, px, py, 42 * sc, 28 * sc, 9 * sc, accent, lit, lit ? accent : null);
        ctx.fillStyle = lit ? '#0b1220' : '#cbd5e1';
        ctx.font = `800 ${Math.max(8, Math.round(9 * sc))}px sans-serif`; ctx.textAlign = 'center';
        ctx.fillText(String(lbl).slice(0, 5), px + 21 * sc, py + 17 * sc);
      });
      ctx.textAlign = 'left';
    } else if (tplId === 'revenue_growth' || tplId === 'rocket_boost') {
      drawMixedHeadline(ctx, 22 * sc, 30 * sc + dy, title, accentText, accent, sc);
      if (metric) {
        drawGlassPill(ctx, w - 96 * sc, 14 * sc + dy, 80 * sc, 26 * sc, 13 * sc, accent, true);
        ctx.fillStyle = accent; ctx.font = `900 ${Math.round(12 * sc)}px sans-serif`; ctx.textAlign = 'center';
        ctx.fillText(metric.slice(0, 10), w - 56 * sc, 31 * sc + dy);
        ctx.textAlign = 'left';
      }
      const gx = 32 * sc, gy = 62 * sc + dy, gw = w - 64 * sc, gh = h - 98 * sc;
      const cvals = vals.slice(0, 4);
      while (cvals.length < 3) cvals.unshift(Math.max(5, cvals[0] * 0.45));
      const vmax = Math.max(...cvals, 1);
      const pts = cvals.map((v, i) => [gx + (gw * i) / (cvals.length - 1), gy + gh - gh * 0.85 * (v / vmax) * animP]);
      const grad = ctx.createLinearGradient(0, gy, 0, gy + gh);
      grad.addColorStop(0, hexRgba(accent, 0.45)); grad.addColorStop(1, hexRgba(accent, 0));
      ctx.beginPath(); ctx.moveTo(pts[0][0], gy + gh);
      pts.forEach(([px, py]) => ctx.lineTo(px, py));
      ctx.lineTo(pts[pts.length - 1][0], gy + gh); ctx.closePath();
      ctx.fillStyle = grad; ctx.fill();
      ctx.beginPath();
      pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
      ctx.strokeStyle = accent; ctx.lineWidth = 3 * sc; ctx.stroke();
      pts.forEach(([px, py]) => {
        ctx.beginPath(); ctx.arc(px, py, 4 * sc, 0, Math.PI * 2);
        ctx.fillStyle = '#fff'; ctx.fill();
      });
    } else if (tplId === 'vs_split_card' || tplId === 'before_after_meter') {
      drawMixedHeadline(ctx, w / 2, 26 * sc + dy, title, accentText, accent, sc, true);
      const colW = (w - 64 * sc) / 2;
      drawGlassPill(ctx, 20 * sc, 56 * sc + dy, colW, h - 82 * sc, 14 * sc, '#F43F5E', true, 'rgba(42, 16, 24, 0.82)');
      drawGlassPill(ctx, w / 2 + 12 * sc, 56 * sc + dy, colW, h - 82 * sc, 14 * sc, accent, true, 'rgba(12, 36, 24, 0.82)');
      ctx.textAlign = 'center';
      ctx.fillStyle = '#fecdd3'; ctx.font = `700 ${Math.round(11 * sc)}px sans-serif`;
      ctx.fillText(String(labels[0] || 'Antes').slice(0, 18), 20 * sc + colW / 2, 102 * sc + dy);
      ctx.fillStyle = '#bbf7d0';
      ctx.fillText(String(labels[1] || 'Agora').slice(0, 18), w / 2 + 12 * sc + colW / 2, 102 * sc + dy);
      drawVectorIcon(ctx, 'bolt', w / 2, 102 * sc + dy, 16 * sc, accent, animP, tSec);
      ctx.textAlign = 'left';
    } else if (tplId === 'multi_city_map' || tplId === 'route_path') {
      drawMixedHeadline(ctx, 22 * sc, 28 * sc + dy, title, accentText, accent, sc);
      const pts = labels.slice(0, 3).map((_, i) => [56 * sc + (w - 112 * sc) * (i / Math.max(1, Math.min(3, labels.length) - 1)), (i % 2 === 0 ? 115 : 74) * sc + dy]);
      ctx.strokeStyle = accent; ctx.lineWidth = 2.4 * sc;
      for (let i = 0; i < pts.length - 1; i++) {
        const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
        ctx.beginPath(); ctx.moveTo(x0, y0);
        ctx.quadraticCurveTo((x0 + x1) / 2, Math.min(y0, y1) - 24 * sc, x0 + (x1 - x0) * animP, y0 + (y1 - y0) * animP);
        ctx.stroke();
      }
      pts.forEach(([px, py], i) => {
        ctx.beginPath(); ctx.arc(px, py, 5 * sc, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.fill();
        drawGlassPill(ctx, px - 36 * sc, py + 10 * sc, 72 * sc, 20 * sc, 10 * sc, accent, true);
        ctx.fillStyle = '#fff'; ctx.font = `700 ${Math.round(9 * sc)}px sans-serif`; ctx.textAlign = 'center';
        ctx.fillText(String(labels[i] || '').slice(0, 11), px, py + 23 * sc);
      });
      ctx.textAlign = 'left';
    } else if (tplId === 'flow_diagram' || tplId === 'timeline_steps' || tplId === 'checklist_reveal') {
      drawMixedHeadline(ctx, 22 * sc, 28 * sc + dy, title, accentText, accent, sc);
      const items = labels.slice(0, 3);
      items.forEach((lbl, i) => {
        if (animP < i * 0.25) return;
        const iy = (54 + i * 42) * sc + dy;
        drawGlassPill(ctx, 22 * sc, iy, w - 44 * sc, 34 * sc, 12 * sc, accent, true);
        drawVectorIcon(ctx, tplId === 'checklist_reveal' ? 'check' : 'spark', 42 * sc, iy + 17 * sc, 11 * sc, accent, animP, tSec);
        ctx.fillStyle = '#f8fafc'; ctx.font = `700 ${Math.round(11 * sc)}px sans-serif`;
        ctx.fillText(String(lbl).slice(0, 30), 62 * sc, iy + 21 * sc);
      });
    } else {
      // Frameless Hero Vector Icon + Mixed Creator Typography + Highlight Pill
      drawVectorIcon(ctx, iconId, 66 * sc, h * 0.5 + dy, 36 * sc, accent, animP, tSec);
      const rx = 118 * sc;
      drawMixedHeadline(ctx, rx, 56 * sc + dy, title, accentText, accent, sc);
      if (points[0]) {
        const pw = Math.max(40, (w - rx - 20 * sc) * animP);
        drawGlassPill(ctx, rx, 78 * sc + dy, pw, 32 * sc, 11 * sc, accent, true);
        if (animP > 0.35) {
          ctx.fillStyle = '#f8fafc'; ctx.font = `700 ${Math.round(10.5 * sc)}px sans-serif`;
          ctx.fillText(String(points[0]).slice(0, 30), rx + 10 * sc, 98 * sc + dy);
        }
      }
      labels.slice(0, 3).forEach((lbl, ci) => {
        const px = rx + ci * 86 * sc;
        if (px + 78 * sc <= w && animP >= ci * 0.2) {
          drawGlassPill(ctx, px, 122 * sc + dy, 78 * sc, 22 * sc, 11 * sc, accent, false);
          ctx.fillStyle = '#cbd5e1'; ctx.font = `700 ${Math.round(9 * sc)}px sans-serif`; ctx.textAlign = 'center';
          ctx.fillText(String(lbl).slice(0, 10), px + 39 * sc, 136 * sc + dy);
        }
      });
      ctx.textAlign = 'left';
    }
    ctx.restore();
  }

  function tickPreviewLoop(nowMs) {
    const cv = $('motionPreviewCanvas');
    const vid = $('previewVideo');
    const liveOverlay = $('liveOverlay');
    const vidLoaded = Boolean(vid && !vid.hidden);

    if (cv && layers.length) {
      const tNow = (vidLoaded && !vid.paused)
        ? vid.currentTime
        : (vidLoaded && !isNaN(vid.currentTime) ? vid.currentTime : ((nowMs / 1000) % 12));
      let active = layers.find((l) => !vidLoaded ? true : (tNow >= l.start && tNow <= l.end));
      if (!active && vidLoaded && vid.paused && activeEditIdx >= 0 && layers[activeEditIdx]) {
        active = layers[activeEditIdx];
      }
      if (active) {
        cv.hidden = false;
        const pos = active.position || (active.params && active.params.position) || 'bottom-card';
        cv.dataset.pos = pos;
        const sc = Math.max(0.55, Math.min(1.35, Number(active.scale || 100) / 100));
        if (pos === 'center') {
          cv.style.transform = `translate(-50%, -50%) scale(${sc})`;
        } else if (pos === 'top-center' || pos === 'bottom-card') {
          cv.style.transform = `translateX(-50%) scale(${sc})`;
        } else {
          cv.style.transform = `scale(${sc})`;
        }
        const dur = Math.max(1.2, (active.end - active.start) || 3.2);
        const prog = (vidLoaded && !vid.paused)
          ? Math.max(0, Math.min(1, (tNow - active.start) / dur))
          : ((nowMs / 1000) % dur) / dur;
        drawMotionCanvas(cv, active.template_id, active.params || {}, prog, nowMs / 1000);
        if (vidLoaded && liveOverlay) {
          liveOverlay.hidden = active.replace_captions !== false;
        }
      } else {
        cv.hidden = true;
        if (vidLoaded && liveOverlay) liveOverlay.hidden = false;
      }
    } else {
      if (cv) cv.hidden = true;
      if (vidLoaded && liveOverlay) liveOverlay.hidden = false;
    }

    document.querySelectorAll('canvas[data-mg-thumb]').forEach((c) => {
      const idx = Number(c.dataset.mgThumb);
      const s = suggestions[idx];
      if (!s) return;
      const p = ((nowMs / 1000) % 2.8) / 2.8;
      drawMotionCanvas(c, s.template_id, s.params || {}, 0.25 + 0.7 * p, nowMs / 1000);
    });
    requestAnimationFrame(tickPreviewLoop);
  }
  requestAnimationFrame(tickPreviewLoop);

  function renderSuggestions() {
    const box = $('motionSuggestionsList');
    const applyAllBtn = $('applyAllMotionBtn');
    if (!box) return;
    box.replaceChildren();
    if (applyAllBtn) applyAllBtn.hidden = !suggestions.length;

    suggestions.forEach((sug, idx) => {
      const card = document.createElement('div');
      card.className = 'mg-sug-card' + (sug.inserted ? ' is-inserted' : '');

      const top = document.createElement('div');
      top.className = 'mg-sug-top';
      const cv = document.createElement('canvas');
      cv.width = 240; cv.height = 124;
      cv.className = 'mg-thumb-cv';
      cv.dataset.mgThumb = String(idx);

      const meta = document.createElement('div');
      meta.className = 'mg-sug-meta';
      const scriptHeadline = (sug.params && sug.params.title) || sug.subject || sug.template_name;
      const promptTxt = sug.prompt || (sug.params && sug.params.visual_prompt) || '';
      const repBadge = sug.replace_captions !== false
        ? '<span class="mg-pill" style="background:rgba(34,197,94,0.16);color:#86efac;">Substitui legenda</span>'
        : '';
      meta.innerHTML = `
        <div class="mg-badges">
          <span class="mg-pill">${sug.template_name || sug.template_id}</span>
          ${repBadge}
          <span class="mg-time">${Number(sug.start).toFixed(1)}s – ${Number(sug.end).toFixed(1)}s</span>
        </div>
        <strong>${scriptHeadline}</strong>
        <p class="mg-excerpt">"${sug.excerpt || ''}"</p>
        ${promptTxt ? `<div class="mg-prompt-tag" style="font-size:11px;color:#cbd5e1;background:rgba(255,255,255,0.04);padding:4px 7px;border-radius:6px;margin:4px 0;">💬 <em>${promptTxt}</em></div>` : ''}
        <small class="mg-reason">${sug.reason || ''}</small>
      `;
      top.append(cv, meta);

      const actions = document.createElement('div');
      actions.className = 'mg-actions';

      const insBtn = document.createElement('button');
      insBtn.type = 'button';
      insBtn.className = 'mg-btn primary';
      insBtn.textContent = sug.inserted ? '✓ Na timeline' : '➕ Inserir na timeline';
      insBtn.addEventListener('click', () => {
        insertSuggestion(idx);
      });

      const swapSel = document.createElement('select');
      swapSel.className = 'media-sel';
      catalog.templates.forEach((t) => {
        const o = document.createElement('option');
        o.value = t.id; o.textContent = `🔄 ${t.name}`;
        if (t.id === sug.template_id) o.selected = true;
        swapSel.append(o);
      });
      swapSel.addEventListener('change', async () => {
        const t = catalog.templates.find((x) => x.id === swapSel.value);
        if (!t) return;
        sug.template_id = t.id;
        sug.template_name = t.name;
        sug.category = t.category;
        if (sug.excerpt || sug.prompt) {
          try {
            const res = await fetch('/api/motion/from_prompt', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ prompt: sug.excerpt || sug.prompt, template_id: t.id }),
            });
            const d = await res.json();
            if (d && d.ok && d.params) {
              sug.params = d.params;
              sug.prompt = d.params.visual_prompt || sug.prompt;
            }
          } catch {}
        }
        renderSuggestions();
      });

      const editBtn = document.createElement('button');
      editBtn.type = 'button'; editBtn.className = 'mg-btn'; editBtn.textContent = '⚙️ Editar';
      editBtn.addEventListener('click', () => {
        if (!sug.inserted) insertSuggestion(idx);
        const li = layers.findIndex((l) => l.sug_id === sug.id);
        activeEditIdx = li;
        renderTimelineLayers();
      });

      const ignBtn = document.createElement('button');
      ignBtn.type = 'button'; ignBtn.className = 'mg-btn danger'; ignBtn.textContent = '✕ Ignorar';
      ignBtn.addEventListener('click', () => {
        suggestions.splice(idx, 1);
        renderSuggestions();
      });

      actions.append(insBtn, swapSel, editBtn, ignBtn);
      card.append(top, actions);
      box.append(card);
    });
  }

  function insertSuggestion(idx) {
    const sug = suggestions[idx];
    if (!sug) return;
    if (layers.some((l) => l.sug_id === sug.id)) return;
    layers.push({
      id: 'layer_' + Date.now() + '_' + idx,
      sug_id: sug.id,
      template_id: sug.template_id,
      template_name: sug.template_name,
      category: sug.category,
      start: Number(sug.start),
      end: Number(sug.end),
      position: sug.position || (sug.params && sug.params.position) || 'bottom-card',
      scale: Number((sug.params && sug.params.scale) || 100),
      replace_captions: sug.replace_captions !== false,
      prompt: sug.prompt || (sug.params && sug.params.visual_prompt) || sug.excerpt || '',
      params: JSON.parse(JSON.stringify(sug.params || {})),
      render_status: 'pending',
      asset_id: '',
      task_id: '',
    });
    sug.inserted = true;
    renderSuggestions();
    renderTimelineLayers();
    if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
  }

  function addManualLayer(templateId) {
    const t = catalog.templates.find((x) => x.id === templateId) || catalog.templates[0];
    if (!t) return;
    const vid = $('previewVideo');
    const curT = (vid && !vid.hidden && !isNaN(vid.currentTime)) ? Number(vid.currentTime.toFixed(1)) : 1.0;
    const defParams = JSON.parse(JSON.stringify(t.default_params || {}));
    defParams.position = 'bottom-card';
    layers.push({
      id: 'layer_' + Date.now(),
      template_id: t.id,
      template_name: t.name,
      category: t.category,
      start: curT,
      end: Number((curT + 3.5).toFixed(1)),
      position: 'bottom-card',
      scale: 100,
      replace_captions: true,
      prompt: defParams.visual_prompt || '',
      params: defParams,
      render_status: 'pending',
      asset_id: '',
      task_id: '',
    });
    activeEditIdx = layers.length - 1;
    renderTimelineLayers();
    if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
  }

  async function preRenderLayer(idx) {
    const l = layers[idx];
    if (!l) return;
    l.render_status = 'rendering';
    l.render_pct = 5;
    renderTimelineLayers();
    try {
      const res = await fetch('/api/motion/render_layer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: l.template_id,
          params: l.params,
          duration: Math.max(1.2, l.end - l.start),
        }),
      });
      const data = await res.json();
      if (!data.task_id) throw new Error(data.error || 'Falha no worker');
      l.task_id = data.task_id;
      l.asset_id = data.asset_id || '';
      while (true) {
        await new Promise((r) => setTimeout(r, 700));
        const stRes = await fetch('/api/motion/tasks/' + l.task_id);
        const st = await stRes.json();
        l.render_pct = st.progress || 0;
        if (st.status === 'done') {
          l.render_status = 'done';
          l.asset_id = st.asset_id || l.asset_id;
          break;
        }
        if (st.status === 'cancelled' || st.status === 'error') {
          l.render_status = st.status;
          break;
        }
        renderTimelineLayers();
      }
    } catch {
      l.render_status = 'error';
    }
    renderTimelineLayers();
  }

  async function cancelLayerRender(idx) {
    const l = layers[idx];
    if (!l || !l.task_id) return;
    await fetch('/api/motion/tasks/' + l.task_id + '/cancel', { method: 'POST' }).catch(() => {});
    l.render_status = 'cancelled';
    renderTimelineLayers();
  }

  async function regenerateFromPrompt(idx, promptText, keepTemplate) {
    const l = layers[idx];
    if (!l || !promptText.trim()) return;
    const res = await fetch('/api/motion/from_prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: promptText.trim(),
        template_id: keepTemplate ? l.template_id : '',
      }),
    });
    const d = await res.json();
    if (d && d.ok && d.params) {
      l.template_id = d.template_id || l.template_id;
      l.template_name = d.template_name || l.template_name;
      l.category = d.category || l.category;
      l.params = d.params;
      l.prompt = promptText.trim();
      l.render_status = 'pending';
      l.asset_id = '';
      renderTimelineLayers();
      if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
    }
  }

  function renderTimelineLayers() {
    const box = $('motionTimelineList');
    if (!box) return;
    box.replaceChildren();
    layers.forEach((l, idx) => {
      const row = document.createElement('div');
      row.className = 'mg-layer-row';
      const head = document.createElement('div');
      head.className = 'mg-layer-head';
      const layerTitle = (l.params && l.params.title) || l.template_name || l.template_id;
      head.innerHTML = `<strong>🎬 ${layerTitle}</strong><span class="mg-time">${l.start.toFixed(1)}s → ${l.end.toFixed(1)}s</span>`;

      const ctrls = document.createElement('div');
      ctrls.className = 'mg-layer-ctrls';

      const inS = document.createElement('input');
      inS.type = 'number'; inS.step = '0.2'; inS.min = '0'; inS.value = l.start; inS.className = 'media-time-in';
      inS.addEventListener('input', () => {
        l.start = Math.max(0, Number(inS.value || 0));
        if (l.end <= l.start + 0.8) l.end = Number((l.start + 1.5).toFixed(1));
        if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
      });

      const inE = document.createElement('input');
      inE.type = 'number'; inE.step = '0.2'; inE.min = '0.5'; inE.value = l.end; inE.className = 'media-time-in';
      inE.addEventListener('input', () => {
        l.end = Math.max(l.start + 0.8, Number(inE.value || l.start + 2));
        if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
      });

      const posSel = document.createElement('select');
      posSel.className = 'media-sel';
      [
        ['bottom-card', 'Inferior (Sem cobrir rosto)'],
        ['top-center', 'Topo Flutuante'],
        ['top-right', 'Topo Direita'],
        ['top-left', 'Topo Esquerda'],
        ['center', 'Centro'],
      ].forEach(([v, txt]) => {
        const o = document.createElement('option'); o.value = v; o.textContent = txt;
        if ((l.position || 'bottom-card') === v) o.selected = true;
        posSel.append(o);
      });
      posSel.addEventListener('change', () => {
        l.position = posSel.value;
        l.params.position = posSel.value;
        l.render_status = 'pending';
        if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
      });

      const editBtn = document.createElement('button');
      editBtn.type = 'button'; editBtn.className = 'mg-btn'; editBtn.textContent = activeEditIdx === idx ? '▲ Fechar' : '⚙️ Editar Prompt';
      editBtn.addEventListener('click', () => {
        activeEditIdx = activeEditIdx === idx ? -1 : idx;
        renderTimelineLayers();
      });

      const renBtn = document.createElement('button');
      renBtn.type = 'button'; renBtn.className = 'mg-btn';
      if (l.render_status === 'rendering') {
        renBtn.textContent = `⏳ ${l.render_pct || 0}% · ✕ Cancelar`;
        renBtn.addEventListener('click', () => cancelLayerRender(idx));
      } else if (l.render_status === 'done') {
        renBtn.textContent = '✓ Renderizado';
        renBtn.addEventListener('click', () => preRenderLayer(idx));
      } else {
        renBtn.textContent = '▶ Gerar camada';
        renBtn.addEventListener('click', () => preRenderLayer(idx));
      }

      const delBtn = document.createElement('button');
      delBtn.type = 'button'; delBtn.className = 'media-del'; delBtn.textContent = '✕';
      delBtn.addEventListener('click', () => {
        const sMatch = suggestions.find((s) => s.id === l.sug_id);
        if (sMatch) sMatch.inserted = false;
        layers.splice(idx, 1);
        activeEditIdx = -1;
        renderSuggestions();
        renderTimelineLayers();
        if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
      });

      const l1 = document.createElement('span'); l1.textContent = 'De:';
      const l2 = document.createElement('span'); l2.textContent = 'Até:';
      ctrls.append(l1, inS, l2, inE, posSel, editBtn, renBtn, delBtn);
      row.append(head, ctrls);

      if (activeEditIdx === idx) {
        const ed = document.createElement('div');
        ed.className = 'mg-param-editor';
        const p = l.params || {};
        const promptVal = (l.prompt || p.visual_prompt || '').replace(/</g, '&lt;').replace(/"/g, '&quot;');
        const ptsVal = Array.isArray(p.points) ? p.points.join('\n') : '';
        ed.innerHTML = `
          <label style="grid-column:1 / -1;">
            <span>💬 Prompt da cena (baseado na fala)</span>
            <textarea rows="2" data-p="visual_prompt" placeholder="Descreva o que este Motion Graphic deve explicar visualmente...">${promptVal}</textarea>
            <div style="display:flex;gap:8px;margin-top:6px;flex-wrap:wrap;">
              <button type="button" class="mg-btn primary" data-regen="auto">✨ Gerar cena do Prompt</button>
              <label style="display:inline-flex;align-items:center;gap:6px;font-size:12px;">
                <input type="checkbox" data-p="replace_captions" ${l.replace_captions !== false ? 'checked' : ''}>
                Substituir legenda neste trecho
              </label>
            </div>
          </label>
          <label><span>Título do roteiro</span><input type="text" data-p="title" value="${(p.title || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Destaque itálico</span><input type="text" data-p="accent_text" value="${(p.accent_text || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Métrica / Valor</span><input type="text" data-p="metric" value="${(p.metric || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Tags / Itens (vírgula)</span><input type="text" data-p="labels" value="${(Array.isArray(p.labels) ? p.labels.join(', ') : '').replace(/"/g, '&quot;')}"></label>
          <label style="grid-column:1 / -1;"><span>Frase explicativa (1 por linha)</span><textarea rows="2" data-p="points">${ptsVal.replace(/</g, '&lt;')}</textarea></label>
          <label><span>Cor</span><input type="color" data-p="accent_color" value="${p.accent_color || '#22C55E'}"></label>
          <label><span>Tamanho (%)</span><input type="number" min="60" max="135" step="5" data-p="scale" value="${l.scale || 100}"></label>
        `;
        ed.querySelector('[data-regen="auto"]')?.addEventListener('click', () => {
          const ta = ed.querySelector('textarea[data-p="visual_prompt"]');
          regenerateFromPrompt(idx, ta ? ta.value : '', false);
        });
        ed.querySelectorAll('input, textarea').forEach((inp) => {
          inp.addEventListener('input', () => {
            const key = inp.dataset.p;
            if (!key) return;
            if (key === 'replace_captions') {
              l.replace_captions = Boolean(inp.checked);
            } else if (key === 'labels') {
              l.params.labels = inp.value.split(',').map((s) => s.trim()).filter(Boolean);
            } else if (key === 'points') {
              l.params.points = inp.value.split('\n').map((s) => s.trim()).filter(Boolean).slice(0, 2);
            } else if (key === 'visual_prompt') {
              l.prompt = inp.value;
              l.params.visual_prompt = inp.value;
            } else if (key === 'scale') {
              l.scale = Math.max(60, Math.min(135, Number(inp.value || 100)));
              l.params.scale = l.scale;
            } else {
              l.params[key] = inp.value;
            }
            l.render_status = 'pending';
            if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
          });
        });
        row.append(ed);
      }

      box.append(row);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('analyzeMotionBtn')?.addEventListener('click', async () => {
      const btn = $('analyzeMotionBtn');
      const jid = window.getEuEditoJobId?.() || '';
      const caps = window.getEuEditoCaptions?.() || [];
      if (!jid || !caps.length) return;
      btn.disabled = true;
      btn.textContent = '🤖 Criando cenas do roteiro…';
      try {
        const res = await fetch('/api/motion/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jid, captions: caps }),
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        suggestions = data.suggestions || [];
        renderSuggestions();
        if (!suggestions.length) {
          const box = $('motionSuggestionsList');
          if (box) box.innerHTML = '<small class="broll-hint">Nenhuma oportunidade óbvia detectada automaticamente. Você pode adicionar um Motion manual abaixo.</small>';
        }
      } catch (err) {
        const box = $('motionSuggestionsList');
        if (box) box.innerHTML = `<small class="broll-hint">Erro na análise: ${err?.message || 'tente novamente'}</small>`;
      } finally {
        btn.textContent = '✨ Analisar vídeo e sugerir Motion Graphics';
        btn.disabled = false;
      }
    });

    $('applyAllMotionBtn')?.addEventListener('click', () => {
      suggestions.forEach((_, i) => insertSuggestion(i));
    });

    $('addManualMotionBtn')?.addEventListener('click', async () => {
      if (!catalog.templates.length) await loadCatalog();
      const sel = $('manualMotionTplSelect');
      addManualLayer((sel && sel.value) || 'sketch_calligraphy');
    });

    loadCatalog().then(() => {
      const sel = $('manualMotionTplSelect');
      if (sel && catalog.templates.length) {
        sel.replaceChildren();
        catalog.templates.forEach((t) => {
          const o = document.createElement('option');
          o.value = t.id;
          const cat = catalog.categories.find((c) => c.id === t.category);
          o.textContent = `${cat ? cat.name : t.category} · ${t.name}`;
          sel.append(o);
        });
      }
    });
  });

  window.EuEditoMotion = {
    getLayers: () => layers,
    reset: () => { suggestions = []; layers = []; activeEditIdx = -1; renderSuggestions(); renderTimelineLayers(); },
  };
})();
