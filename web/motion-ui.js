/* Eu Edito — Speech-Driven Explanatory Motion Graphics Frontend Module */
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
      if (u < 0.72) {
        const s = u / 0.72;
        return 1.06 * (1 - Math.pow(1 - s, 3));
      }
      const s = (u - 0.72) / 0.28;
      return 1.06 - 0.06 * (s * s * (3 - 2 * s));
    }
    if (mode === 'smooth') return u * u * (3 - 2 * u);
    return 1 - Math.pow(1 - u, 3);
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, Math.max(2, w), Math.max(2, h), Math.min(r, w / 2, h / 2));
  }

  function hexRgba(hex, a) {
    const clean = String(hex || '#22C55E').replace('#', '');
    if (clean.length !== 6) return `rgba(34,197,94,${a})`;
    const r = parseInt(clean.slice(0, 2), 16) || 34;
    const g = parseInt(clean.slice(2, 4), 16) || 197;
    const b = parseInt(clean.slice(4, 6), 16) || 94;
    return `rgba(${r},${g},${b},${a})`;
  }

  function drawSceneHeader(ctx, bx, by, bw, h, title, sub, metric, accent, animP) {
    const scaleY = h / 260;
    const padX = Math.max(10, Math.round(bw * 0.04));
    // Progress accent bar at top
    roundRect(ctx, bx + padX, by + Math.max(5, Math.round(7 * scaleY)), Math.max(6, (bw - padX * 2) * animP), Math.max(2, Math.round(3 * scaleY)), 2);
    ctx.fillStyle = accent;
    ctx.fill();

    const titleSz = Math.max(10, Math.round(16 * scaleY));
    const subSz = Math.max(8, Math.round(10.5 * scaleY));
    const metSz = Math.max(10, Math.round(15 * scaleY));

    if (metric) {
      ctx.font = `900 ${metSz}px sans-serif`;
      const mw = Math.min(bw * 0.36, ctx.measureText(metric).width + 16);
      const pillH = Math.max(14, Math.round(22 * scaleY));
      const mx = bx + bw - padX - mw;
      const my = by + Math.max(10, Math.round(14 * scaleY));
      roundRect(ctx, mx, my, mw, pillH, Math.round(pillH / 2));
      ctx.fillStyle = hexRgba(accent, 0.2);
      ctx.fill();
      ctx.strokeStyle = accent;
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.fillText(metric.slice(0, 14), mx + mw / 2, my + pillH * 0.68);
      ctx.textAlign = 'left';
    }

    ctx.fillStyle = '#f8fafc';
    ctx.font = `800 ${titleSz}px sans-serif`;
    ctx.fillText(title.slice(0, 28), bx + padX, by + Math.max(18, Math.round(28 * scaleY)));

    if (sub) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = `500 ${subSz}px sans-serif`;
      ctx.fillText(sub.slice(0, 42), bx + padX, by + Math.max(28, Math.round(43 * scaleY)));
    }
  }

  function drawPointsStrip(ctx, bx, by, bw, bh, points, accent, animP, h) {
    if (!Array.isArray(points) || !points.length || h < 120) return;
    const list = points.slice(0, 2);
    const stripH = Math.max(20, Math.round(bh * 0.16));
    const sy = by + bh - stripH - 8;
    const pw = (bw - 24 - (list.length - 1) * 6) / list.length;
    list.forEach((pt, idx) => {
      const shown = animP >= idx * 0.3;
      const sx = bx + 12 + idx * (pw + 6);
      ctx.save();
      ctx.globalAlpha *= shown ? 1 : 0.25;
      roundRect(ctx, sx, sy, pw, stripH, 7);
      ctx.fillStyle = 'rgba(255,255,255,0.06)';
      ctx.fill();
      ctx.strokeStyle = hexRgba(accent, shown ? 0.55 : 0.18);
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = accent;
      ctx.beginPath();
      ctx.arc(sx + 10, sy + stripH / 2, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `600 ${Math.max(8, Math.round(h * 0.042))}px sans-serif`;
      ctx.fillText(String(pt).slice(0, 24), sx + 18, sy + stripH * 0.62);
      ctx.restore();
    });
  }

  function drawMotionCanvas(canvas, tplId, params, prog, tSec) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const p = params || {};
    const accent = p.accent_color || '#22C55E';
    const easingMode = p.easing || 'cubic-out';
    const enterP = ease(Math.min(1, prog / 0.16), easingMode);
    const exitP = ease(Math.min(1, (1 - prog) / 0.14), 'smooth');
    const alphaEnv = Math.max(0, Math.min(1, Math.min(enterP, exitP)));
    const animP = ease(Math.max(0, Math.min(1, (prog - 0.04) / 0.68)), easingMode);

    ctx.save();
    ctx.globalAlpha = alphaEnv;
    const pad = Math.max(4, Math.round(w * 0.025));
    const dy = (1 - enterP) * 14;
    const bx = pad;
    const by = pad + dy;
    const bw = w - pad * 2;
    const bh = h - pad * 2;

    // Distinct card backdrop + soft glow border
    roundRect(ctx, bx, by, bw, bh, Math.max(8, Math.round(h * 0.06)));
    const bgGrad = ctx.createLinearGradient(bx, by, bx, by + bh);
    bgGrad.addColorStop(0, 'rgba(11, 18, 28, 0.92)');
    bgGrad.addColorStop(1, 'rgba(7, 11, 18, 0.94)');
    ctx.fillStyle = bgGrad;
    ctx.fill();
    ctx.strokeStyle = hexRgba(accent, 0.72);
    ctx.lineWidth = 1.6;
    ctx.stroke();

    const title = String(p.title || 'Motion');
    const sub = String(p.subtitle || '');
    const metric = String(p.metric || '');
    const labels = Array.isArray(p.labels) && p.labels.length ? p.labels : ['Passo 1', 'Passo 2', 'Passo 3'];
    const vals = Array.isArray(p.values) && p.values.length ? p.values.map(Number) : [28, 64, 96];
    const points = Array.isArray(p.points) ? p.points : [];

    drawSceneHeader(ctx, bx, by, bw, h, title, sub, metric, accent, animP);

    const hasPts = points.length > 0 && h >= 120;
    const gx = bx + Math.max(10, Math.round(bw * 0.045));
    const gy = by + Math.round(h * 0.24);
    const gw = bw - Math.max(20, Math.round(bw * 0.09));
    const gh = bh - Math.round(h * (hasPts ? 0.44 : 0.30));

    if (tplId === 'revenue_growth') {
      // Grid + climbing exponential curve + milestone nodes
      ctx.strokeStyle = 'rgba(255,255,255,0.10)';
      ctx.lineWidth = 1;
      for (let r = 1; r <= 3; r++) {
        const yy = gy + (gh * r) / 4;
        ctx.beginPath(); ctx.moveTo(gx, yy); ctx.lineTo(gx + gw, yy); ctx.stroke();
      }
      const vmax = Math.max(...vals, 1);
      const pts = vals.map((v, i) => [
        gx + (gw * i) / Math.max(1, vals.length - 1),
        gy + gh - gh * 0.85 * (v / vmax) * animP,
      ]);
      const areaG = ctx.createLinearGradient(0, gy, 0, gy + gh);
      areaG.addColorStop(0, hexRgba(accent, 0.42));
      areaG.addColorStop(1, hexRgba(accent, 0.02));
      ctx.beginPath();
      ctx.moveTo(pts[0][0], gy + gh);
      pts.forEach(([px, py]) => ctx.lineTo(px, py));
      ctx.lineTo(pts[pts.length - 1][0], gy + gh);
      ctx.closePath();
      ctx.fillStyle = areaG;
      ctx.fill();

      ctx.beginPath();
      pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
      ctx.strokeStyle = accent;
      ctx.lineWidth = 2.8;
      ctx.stroke();

      pts.forEach(([px, py], i) => {
        const last = i === pts.length - 1;
        ctx.beginPath();
        ctx.arc(px, py, last ? 4.5 + Math.sin(tSec * 5) * 1.4 : 3.2, 0, Math.PI * 2);
        ctx.fillStyle = last ? '#ffffff' : accent;
        ctx.fill();
        if (labels[i] && h >= 100) {
          ctx.fillStyle = '#cbd5e1';
          ctx.font = `600 ${Math.max(8, Math.round(h * 0.042))}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.fillText(String(labels[i]).slice(0, 10), px, gy + gh + 10);
        }
      });
      ctx.textAlign = 'left';
    } else if (tplId === 'money_flow') {
      // Stacked gold coins + transfer arrows + value pills
      const stacks = Math.min(3, Math.max(2, vals.length));
      const slotW = gw / stacks;
      for (let i = 0; i < stacks; i++) {
        const cx = gx + slotW * (i + 0.5);
        const coinCount = Math.max(2, Math.min(6, Math.round((vals[i] / Math.max(...vals, 1)) * 5 * animP) + 1));
        const cw = Math.min(48, slotW * 0.54);
        for (let c = 0; c < coinCount; c++) {
          const cy = gy + gh - 12 - c * Math.max(6, Math.round(gh * 0.11));
          ctx.beginPath();
          ctx.ellipse(cx, cy, cw / 2, Math.max(4, cw * 0.22), 0, 0, Math.PI * 2);
          ctx.fillStyle = i === stacks - 1 ? '#FACC15' : '#EAB308';
          ctx.fill();
          ctx.strokeStyle = '#713F12';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
        if (i < stacks - 1) {
          const ax1 = cx + cw * 0.55;
          const ax2 = cx + slotW - cw * 0.55;
          const ay = gy + gh * 0.45;
          ctx.strokeStyle = accent;
          ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(ax1, ay); ctx.lineTo(ax2, ay); ctx.stroke();
        }
        ctx.fillStyle = '#fef08a';
        ctx.font = `700 ${Math.max(8, Math.round(h * 0.045))}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(String(labels[i] || `$${vals[i]}`).slice(0, 10), cx, gy + gh + 8);
      }
      ctx.textAlign = 'left';
    } else if (tplId === 'bar_chart') {
      const nb = Math.max(2, Math.min(5, vals.length));
      const vmax = Math.max(...vals.slice(0, nb), 1);
      const gap = Math.max(6, Math.round(gw * 0.04));
      const barW = Math.max(12, (gw - gap * (nb - 1)) / nb);
      for (let i = 0; i < nb; i++) {
        const ratio = (vals[i] / vmax) * ease(Math.max(0, Math.min(1, animP * 1.2 - i * 0.12)), easingMode);
        const ch = Math.max(6, (gh - 18) * ratio);
        const x0 = gx + i * (barW + gap);
        const y0 = gy + gh - 12 - ch;
        roundRect(ctx, x0, y0, barW, ch, 5);
        ctx.fillStyle = i === nb - 1 ? accent : hexRgba(accent, 0.45 + i * 0.08);
        ctx.fill();
        if (h >= 100) {
          ctx.fillStyle = '#ffffff';
          ctx.font = `700 ${Math.max(8, Math.round(h * 0.042))}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.fillText(String(Math.round(vals[i] * animP)), x0 + barW / 2, y0 - 4);
          ctx.fillStyle = '#cbd5e1';
          ctx.fillText(String(labels[i] || '').slice(0, 9), x0 + barW / 2, gy + gh + 6);
        }
      }
      ctx.textAlign = 'left';
    } else if (tplId === 'donut_share') {
      const r = Math.max(16, Math.min(gw * 0.25, gh * 0.40));
      const cx = gx + r + 8;
      const cy = gy + gh / 2;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = Math.max(5, r * 0.28); ctx.stroke();
      const segs = vals.slice(0, 3);
      const tot = segs.reduce((a, b) => a + Math.max(1, b), 0);
      const palette = [accent, '#38BDF8', '#A78BFA'];
      let ang = -Math.PI / 2;
      segs.forEach((v, idx) => {
        const sweep = ((Math.max(1, v) / tot) * Math.PI * 2) * animP;
        ctx.beginPath();
        ctx.arc(cx, cy, r, ang, ang + sweep);
        ctx.strokeStyle = palette[idx % palette.length];
        ctx.lineWidth = Math.max(5, r * 0.28);
        ctx.stroke();
        ang += sweep;
      });
      // Right-hand breakdown bars
      const lx = cx + r + 16;
      const lw = Math.max(30, gx + gw - lx);
      segs.forEach((v, idx) => {
        const ly = gy + 6 + idx * Math.max(16, (gh - 8) / segs.length);
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `700 ${Math.max(8, Math.round(h * 0.044))}px sans-serif`;
        ctx.fillText(String(labels[idx] || `Item ${idx + 1}`).slice(0, 14), lx, ly + 8);
        roundRect(ctx, lx, ly + 12, lw, 6, 3);
        ctx.fillStyle = 'rgba(255,255,255,0.12)'; ctx.fill();
        roundRect(ctx, lx, ly + 12, Math.max(4, lw * (v / tot) * animP), 6, 3);
        ctx.fillStyle = palette[idx % palette.length]; ctx.fill();
      });
    } else if (tplId === 'multi_city_map' || tplId === 'route_path') {
      // Radar rings + landmass shapes + curved trajectory arcs + animated pins
      const midX = gx + gw / 2;
      const midY = gy + gh / 2;
      [0.35, 0.68, 0.96].forEach((f) => {
        ctx.beginPath();
        ctx.ellipse(midX, midY, gw * 0.45 * f, gh * 0.44 * f, 0, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 1;
        ctx.stroke();
      });
      const n = Math.max(2, Math.min(4, labels.length));
      const pts = Array.from({ length: n }, (_, i) => [
        gx + gw * (0.14 + (0.72 * i) / Math.max(1, n - 1)),
        gy + gh * (i % 2 === 0 ? 0.66 : 0.28),
      ]);
      ctx.strokeStyle = accent;
      ctx.lineWidth = 2.4;
      for (let i = 0; i < pts.length - 1; i++) {
        const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
        const mx = (x0 + x1) / 2, my = Math.min(y0, y1) - 18;
        ctx.beginPath(); ctx.moveTo(x0, y0);
        ctx.quadraticCurveTo(mx, my, x0 + (x1 - x0) * animP, y0 + (y1 - y0) * animP);
        ctx.stroke();
      }
      pts.forEach(([px, py], i) => {
        ctx.beginPath(); ctx.arc(px, py, 5 + Math.abs(Math.sin(tSec * 4 + i)) * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = hexRgba(accent, 0.35); ctx.fill();
        ctx.beginPath(); ctx.arc(px, py, 3.8, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff'; ctx.fill();
        if (h >= 95) {
          ctx.fillStyle = '#f8fafc';
          ctx.font = `700 ${Math.max(8, Math.round(h * 0.044))}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.fillText(String(labels[i] || `Ponto ${i + 1}`).slice(0, 12), px, py + 15);
        }
      });
      ctx.textAlign = 'left';
    } else if (tplId === 'ai_network') {
      // Hexagonal neural core + pulsing satellite chips
      const cx = gx + gw / 2;
      const cy = gy + gh / 2;
      const rad = Math.max(20, Math.min(gw, gh) * 0.42);
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(tSec * 0.35);
      ctx.beginPath();
      for (let k = 0; k < 6; k++) {
        const a = (k * Math.PI) / 3;
        const rx = Math.cos(a) * rad * 0.45, ry = Math.sin(a) * rad * 0.45;
        k === 0 ? ctx.moveTo(rx, ry) : ctx.lineTo(rx, ry);
      }
      ctx.closePath();
      ctx.strokeStyle = accent; ctx.lineWidth = 1.6; ctx.stroke();
      ctx.restore();

      const sats = Math.max(3, Math.min(5, labels.length));
      for (let i = 0; i < sats; i++) {
        const a = -Math.PI / 2 + (i * Math.PI * 2) / sats;
        const sx = cx + Math.cos(a) * rad * 0.92;
        const sy = cy + Math.sin(a) * rad * 0.78;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(sx, sy);
        ctx.strokeStyle = hexRgba(accent, 0.48); ctx.lineWidth = 1.4; ctx.stroke();
        const tx = cx + (sx - cx) * ((tSec * 0.9 + i * 0.25) % 1);
        const ty = cy + (sy - cy) * ((tSec * 0.9 + i * 0.25) % 1);
        ctx.beginPath(); ctx.arc(tx, ty, 2.8, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff'; ctx.fill();

        roundRect(ctx, sx - 26, sy - 9, 52, 18, 6);
        ctx.fillStyle = 'rgba(15,23,42,0.92)'; ctx.fill();
        ctx.strokeStyle = accent; ctx.lineWidth = 1; ctx.stroke();
        ctx.fillStyle = '#f1f5f9';
        ctx.font = `700 ${Math.max(7.5, Math.round(h * 0.038))}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(String(labels[i] || `Nó ${i + 1}`).slice(0, 9), sx, sy + 3);
      }
      ctx.beginPath(); ctx.arc(cx, cy, Math.max(10, rad * 0.26), 0, Math.PI * 2);
      ctx.fillStyle = accent; ctx.fill();
      ctx.fillStyle = '#071018';
      ctx.font = `900 ${Math.max(8, Math.round(h * 0.045))}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText('IA', cx, cy + 4);
      ctx.textAlign = 'left';
    } else if (tplId === 'data_dashboard') {
      // OS window chrome + live equalizer + sparkline pane
      roundRect(ctx, gx, gy, gw, gh, 8);
      ctx.fillStyle = 'rgba(255,255,255,0.04)'; ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.14)'; ctx.lineWidth = 1; ctx.stroke();
      ['#EF4444', '#F59E0B', '#22C55E'].forEach((dc, di) => {
        ctx.beginPath(); ctx.arc(gx + 12 + di * 10, gy + 10, 2.8, 0, Math.PI * 2);
        ctx.fillStyle = dc; ctx.fill();
      });
      const half = gw * 0.55;
      // Sparkline left
      const vmax = Math.max(...vals, 1);
      ctx.beginPath();
      vals.forEach((v, i) => {
        const px = gx + 12 + ((half - 20) * i) / Math.max(1, vals.length - 1);
        const py = gy + gh - 14 - (gh - 36) * (v / vmax) * animP;
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.strokeStyle = accent; ctx.lineWidth = 2.4; ctx.stroke();
      // Live mini bars right
      const eqX = gx + half + 6;
      const eqW = (gw - half - 18) / 5;
      for (let b = 0; b < 5; b++) {
        const bh2 = (gh - 34) * (0.35 + 0.55 * Math.abs(Math.sin(tSec * 3.2 + b)));
        roundRect(ctx, eqX + b * (eqW + 2), gy + gh - 12 - bh2, Math.max(4, eqW - 2), bh2, 2);
        ctx.fillStyle = hexRgba(accent, 0.55 + b * 0.09); ctx.fill();
      }
    } else if (tplId === 'vs_split_card' || tplId === 'before_after_meter') {
      // Red left vs Green right split comparison + glowing VS pill
      const colW = (gw - 16) / 2;
      roundRect(ctx, gx, gy, colW, gh, 9);
      ctx.fillStyle = 'rgba(239,68,68,0.16)'; ctx.fill();
      ctx.strokeStyle = 'rgba(239,68,68,0.65)'; ctx.lineWidth = 1.4; ctx.stroke();

      roundRect(ctx, gx + colW + 16, gy, colW, gh, 9);
      ctx.fillStyle = hexRgba(accent, 0.18); ctx.fill();
      ctx.strokeStyle = accent; ctx.lineWidth = 1.4; ctx.stroke();

      ctx.textAlign = 'center';
      ctx.fillStyle = '#fca5a5';
      ctx.font = `800 ${Math.max(9, Math.round(h * 0.055))}px sans-serif`;
      ctx.fillText(String(labels[0] || 'ANTES').slice(0, 14), gx + colW / 2, gy + gh * 0.42);
      ctx.fillStyle = '#86efac';
      ctx.fillText(String(labels[1] || 'AGORA').slice(0, 14), gx + colW + 16 + colW / 2, gy + gh * 0.42);

      // Center VS badge
      const vcx = gx + gw / 2, vcy = gy + gh / 2;
      ctx.beginPath(); ctx.arc(vcx, vcy, Math.max(10, Math.round(h * 0.07)), 0, Math.PI * 2);
      ctx.fillStyle = '#0f172a'; ctx.fill();
      ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.font = `900 ${Math.max(8, Math.round(h * 0.048))}px sans-serif`;
      ctx.fillText('VS', vcx, vcy + 4);
      ctx.textAlign = 'left';
    } else if (tplId === 'cycle_loop') {
      const cx = gx + gw / 2, cy = gy + gh / 2;
      const rad = Math.max(18, Math.min(gw, gh) * 0.36);
      ctx.beginPath(); ctx.arc(cx, cy, rad, 0, Math.PI * 2);
      ctx.strokeStyle = hexRgba(accent, 0.45); ctx.lineWidth = 2; ctx.stroke();
      const n = 3;
      for (let i = 0; i < n; i++) {
        const a = -Math.PI / 2 + (i * Math.PI * 2) / n + tSec * 0.25;
        const nx = cx + Math.cos(a) * rad;
        const ny = cy + Math.sin(a) * rad;
        roundRect(ctx, nx - 28, ny - 10, 56, 20, 8);
        ctx.fillStyle = 'rgba(15,23,42,0.92)'; ctx.fill();
        ctx.strokeStyle = accent; ctx.lineWidth = 1.2; ctx.stroke();
        ctx.fillStyle = '#f8fafc';
        ctx.font = `700 ${Math.max(8, Math.round(h * 0.04))}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(String(labels[i] || `Etapa ${i + 1}`).slice(0, 10), nx, ny + 3);
      }
      ctx.textAlign = 'left';
    } else if (tplId === 'counter_kpi') {
      const cx = gx + gw / 2, cy = gy + gh / 2;
      const r = Math.max(18, Math.min(gw, gh) * 0.42);
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 5; ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * animP);
      ctx.strokeStyle = accent; ctx.lineWidth = 5; ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.font = `900 ${Math.max(14, Math.round(h * 0.14))}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText((metric || String(vals[0] || '+100%')).slice(0, 12), cx, cy + 5);
      ctx.textAlign = 'left';
    } else {
      // flow_diagram, timeline_steps, concept_callout, badge_alert: sequential numbered step cards
      const n = Math.max(2, Math.min(3, labels.length));
      const gap = 12;
      const sw = Math.max(32, (gw - gap * (n - 1)) / n);
      const ch = Math.max(28, Math.min(gh * 0.72, 64));
      const cy = gy + (gh - ch) / 2;
      for (let i = 0; i < n; i++) {
        const sx = gx + i * (sw + gap);
        const lit = animP >= i / n;
        roundRect(ctx, sx, cy, sw, ch, 8);
        ctx.fillStyle = lit ? hexRgba(accent, 0.22) : 'rgba(255,255,255,0.06)';
        ctx.fill();
        ctx.strokeStyle = lit ? accent : 'rgba(255,255,255,0.22)';
        ctx.lineWidth = 1.4; ctx.stroke();

        // Step number badge
        ctx.beginPath(); ctx.arc(sx + 12, cy + 12, 7, 0, Math.PI * 2);
        ctx.fillStyle = lit ? accent : 'rgba(255,255,255,0.2)'; ctx.fill();
        ctx.fillStyle = lit ? '#071018' : '#f8fafc';
        ctx.font = '800 9px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(String(i + 1), sx + 12, cy + 15);

        ctx.fillStyle = '#f8fafc';
        ctx.font = `700 ${Math.max(8, Math.round(h * 0.044))}px sans-serif`;
        ctx.fillText(String(labels[i] || `Passo ${i + 1}`).slice(0, 12), sx + sw / 2, cy + ch * 0.68);
        if (i < n - 1) {
          ctx.strokeStyle = accent; ctx.lineWidth = 1.6;
          ctx.beginPath(); ctx.moveTo(sx + sw + 2, cy + ch / 2); ctx.lineTo(sx + sw + gap - 2, cy + ch / 2); ctx.stroke();
        }
      }
      ctx.textAlign = 'left';
    }

    if (hasPts) {
      drawPointsStrip(ctx, bx, by, bw, bh, points, accent, animP, h);
    }
    ctx.restore();
  }

  // Live preview animation loop over #previewVideo inside #previewWrap
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
        const pos = active.position || (active.params && active.params.position) || 'center';
        cv.dataset.pos = pos;
        const sc = Math.max(0.55, Math.min(1.35, Number(active.scale || 100) / 100));
        if (pos === 'center') {
          cv.style.transform = `translate(-50%, -50%) scale(${sc})`;
        } else if (pos === 'top-center' || pos === 'bottom-card') {
          cv.style.transform = `translateX(-50%) scale(${sc})`;
        } else {
          cv.style.transform = `scale(${sc})`;
        }
        const dur = Math.max(1.2, (active.end - active.start) || 3.5);
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

    // Animate suggestion thumbnails
    document.querySelectorAll('canvas[data-mg-thumb]').forEach((c) => {
      const idx = Number(c.dataset.mgThumb);
      const s = suggestions[idx];
      if (!s) return;
      const p = ((nowMs / 1000) % 2.8) / 2.8;
      drawMotionCanvas(c, s.template_id, s.params || {}, 0.22 + 0.72 * p, nowMs / 1000);
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
      cv.width = 220; cv.height = 110;
      cv.className = 'mg-thumb-cv';
      cv.dataset.mgThumb = String(idx);

      const meta = document.createElement('div');
      meta.className = 'mg-sug-meta';
      const catObj = catalog.categories.find((c) => c.id === sug.category);
      const promptTxt = sug.prompt || (sug.params && sug.params.visual_prompt) || '';
      const repBadge = sug.replace_captions !== false
        ? '<span class="mg-pill" style="background:rgba(34,197,94,0.16);color:#86efac;">Substitui legenda</span>'
        : '';
      meta.innerHTML = `
        <div class="mg-badges">
          <span class="mg-pill">${catObj ? catObj.name : sug.category}</span>
          <span class="mg-pill rel-${(sug.relevance || 'Média').toLowerCase()}">Relevância: ${sug.relevance || 'Média'}</span>
          ${repBadge}
          <span class="mg-time">${Number(sug.start).toFixed(1)}s – ${Number(sug.end).toFixed(1)}s</span>
        </div>
        <strong>${sug.template_name || sug.template_id}</strong>
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
      position: sug.position || (sug.params && sug.params.position) || 'center',
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
    defParams.position = 'center';
    layers.push({
      id: 'layer_' + Date.now(),
      template_id: t.id,
      template_name: t.name,
      category: t.category,
      start: curT,
      end: Number((curT + 3.5).toFixed(1)),
      position: 'center',
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
      head.innerHTML = `<strong>📊 ${l.template_name || l.template_id}</strong><span class="mg-time">${l.start.toFixed(1)}s → ${l.end.toFixed(1)}s</span>`;

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
      [['center', 'Centro (Explicativo)'], ['top-center', 'Topo Centro'], ['bottom-card', 'Inferior'], ['top-right', 'Topo Direita'], ['top-left', 'Topo Esquerda']].forEach(([v, txt]) => {
        const o = document.createElement('option'); o.value = v; o.textContent = txt;
        if ((l.position || 'center') === v) o.selected = true;
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
          <label><span>Título</span><input type="text" data-p="title" value="${(p.title || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Subtítulo</span><input type="text" data-p="subtitle" value="${(p.subtitle || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Métrica / Valor</span><input type="text" data-p="metric" value="${(p.metric || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Rótulos (vírgula)</span><input type="text" data-p="labels" value="${(Array.isArray(p.labels) ? p.labels.join(', ') : '').replace(/"/g, '&quot;')}"></label>
          <label style="grid-column:1 / -1;"><span>Pontos explicativos (1 por linha)</span><textarea rows="2" data-p="points">${ptsVal.replace(/</g, '&lt;')}</textarea></label>
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
              l.params.points = inp.value.split('\n').map((s) => s.trim()).filter(Boolean).slice(0, 3);
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
      btn.textContent = '🤖 Analisando fala e gerando cenas Motion…';
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
      addManualLayer((sel && sel.value) || 'revenue_growth');
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
