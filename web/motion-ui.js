/* Eu Edito — Intelligent Motion Graphics Frontend Module */
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
    ctx.roundRect(x, y, w, h, r);
  }

  function drawMotionCanvas(canvas, tplId, params, prog, tSec) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const accent = (params && params.accent_color) || '#22C55E';
    const easingMode = (params && params.easing) || 'cubic-out';
    const enterP = ease(Math.min(1, prog / 0.18), easingMode);
    const exitP = ease(Math.min(1, (1 - prog) / 0.16), 'smooth');
    const alphaEnv = Math.max(0, Math.min(1, Math.min(enterP, exitP)));
    const animP = ease(Math.max(0, Math.min(1, (prog - 0.05) / 0.65)), easingMode);

    ctx.save();
    ctx.globalAlpha = alphaEnv;
    const pad = Math.round(w * 0.03);
    const dy = (1 - enterP) * 14;
    const bx = pad, by = pad + dy, bw = w - pad * 2, bh = h - pad * 2;

    roundRect(ctx, bx, by, bw, bh, 14);
    ctx.fillStyle = 'rgba(10, 18, 14, 0.86)';
    ctx.fill();
    ctx.strokeStyle = accent;
    ctx.lineWidth = 1.6;
    ctx.stroke();

    // Top animated progress accent bar
    roundRect(ctx, bx + 12, by + 8, Math.max(6, (bw - 24) * animP), 3, 2);
    ctx.fillStyle = accent;
    ctx.fill();

    const title = String((params && params.title) || 'Motion').slice(0, 26);
    const sub = String((params && params.subtitle) || '').slice(0, 32);
    const metric = String((params && params.metric) || '').slice(0, 14);
    const labels = Array.isArray(params && params.labels) && params.labels.length ? params.labels : ['A', 'B', 'C'];
    const vals = Array.isArray(params && params.values) && params.values.length ? params.values.map(Number) : [32, 68, 96];

    ctx.fillStyle = '#f4f9f5';
    ctx.font = `800 ${Math.max(11, Math.round(h * 0.12))}px sans-serif`;
    ctx.fillText(title, bx + 14, by + Math.round(h * 0.24));
    if (sub) {
      ctx.fillStyle = '#9cc0a9';
      ctx.font = `500 ${Math.max(9, Math.round(h * 0.085))}px sans-serif`;
      ctx.fillText(sub, bx + 14, by + Math.round(h * 0.36));
    }
    if (metric) {
      ctx.fillStyle = accent;
      ctx.font = `900 ${Math.max(12, Math.round(h * 0.14))}px sans-serif`;
      ctx.textAlign = 'right';
      ctx.fillText(metric, bx + bw - 14, by + Math.round(h * 0.26));
      ctx.textAlign = 'left';
    }

    const gx = bx + 16, gy = by + Math.round(h * 0.44), gw = bw - 32, gh = bh - Math.round(h * 0.54);
    if (tplId === 'revenue_growth' || tplId === 'data_dashboard') {
      ctx.strokeStyle = 'rgba(255,255,255,0.12)';
      ctx.lineWidth = 1;
      for (let r = 1; r <= 2; r++) {
        const yy = gy + (gh * r) / 3;
        ctx.beginPath(); ctx.moveTo(gx, yy); ctx.lineTo(gx + gw, yy); ctx.stroke();
      }
      const vmax = Math.max(...vals, 1);
      const pts = vals.map((v, i) => [
        gx + (gw * i) / Math.max(1, vals.length - 1),
        gy + gh - gh * 0.85 * (v / vmax) * animP,
      ]);
      ctx.beginPath();
      ctx.moveTo(pts[0][0], gy + gh);
      pts.forEach(([px, py]) => ctx.lineTo(px, py));
      ctx.lineTo(pts[pts.length - 1][0], gy + gh);
      ctx.closePath();
      ctx.fillStyle = accent + '33';
      ctx.fill();
      ctx.beginPath();
      pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
      ctx.strokeStyle = accent;
      ctx.lineWidth = 2.6;
      ctx.stroke();
      const [lx, ly] = pts[pts.length - 1];
      ctx.beginPath(); ctx.arc(lx, ly, 4 + Math.sin(tSec * 5) * 1.5, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff'; ctx.fill();
    } else if (tplId === 'bar_chart' || tplId === 'vs_split_card' || tplId === 'before_after_meter' || tplId === 'money_flow') {
      const nb = Math.max(2, Math.min(5, vals.length));
      const vmax = Math.max(...vals.slice(0, nb), 1);
      const gap = 8;
      const barW = Math.max(10, (gw - gap * (nb - 1)) / nb);
      for (let i = 0; i < nb; i++) {
        const ch = Math.max(4, (gh - 12) * (vals[i] / vmax) * animP);
        const x0 = gx + i * (barW + gap);
        const y0 = gy + gh - 10 - ch;
        roundRect(ctx, x0, y0, barW, ch, 4);
        ctx.fillStyle = i === nb - 1 ? accent : 'rgba(180,210,192,0.55)';
        ctx.fill();
      }
    } else if (tplId === 'donut_share' || tplId === 'cycle_loop' || tplId === 'counter_kpi') {
      const cx = gx + gw / 2, cy = gy + gh / 2, r = Math.max(14, Math.min(gw, gh) * 0.40);
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.16)'; ctx.lineWidth = 6; ctx.stroke();
      const ratio = vals[0] <= 100 ? vals[0] / 100 : 0.85;
      ctx.beginPath(); ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ratio * animP);
      ctx.strokeStyle = accent; ctx.lineWidth = 6; ctx.stroke();
    } else if (tplId === 'multi_city_map' || tplId === 'route_path') {
      const pts = labels.slice(0, 3).map((_, i) => [
        gx + gw * (0.16 + 0.34 * i),
        gy + gh * (i % 2 === 0 ? 0.65 : 0.30),
      ]);
      ctx.strokeStyle = accent; ctx.lineWidth = 2.2;
      for (let i = 0; i < pts.length - 1; i++) {
        const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
        ctx.beginPath(); ctx.moveTo(x0, y0);
        ctx.lineTo(x0 + (x1 - x0) * animP, y0 + (y1 - y0) * animP);
        ctx.stroke();
      }
      pts.forEach(([px, py], i) => {
        ctx.beginPath(); ctx.arc(px, py, 5 + Math.abs(Math.sin(tSec * 4 + i)) * 3, 0, Math.PI * 2);
        ctx.fillStyle = accent + '55'; ctx.fill();
        ctx.beginPath(); ctx.arc(px, py, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = '#fff'; ctx.fill();
      });
    } else {
      const n = Math.max(2, Math.min(3, labels.length));
      const sw = Math.max(30, (gw - 16 * (n - 1)) / n);
      const cy = gy + gh / 2;
      for (let i = 0; i < n; i++) {
        const sx = gx + i * (sw + 16);
        const lit = animP >= i / n;
        roundRect(ctx, sx, cy - 12, sw, 24, 6);
        ctx.fillStyle = lit ? accent + '44' : 'rgba(255,255,255,0.08)';
        ctx.fill();
        ctx.strokeStyle = lit ? accent : 'rgba(255,255,255,0.2)';
        ctx.lineWidth = 1.3; ctx.stroke();
        ctx.fillStyle = '#fff'; ctx.font = '700 9px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(String(labels[i]).slice(0, 9), sx + sw / 2, cy + 3);
      }
      ctx.textAlign = 'left';
    }
    ctx.restore();
  }

  // Live preview animation loop over #previewVideo inside #previewWrap
  let rafId = null;
  function tickPreviewLoop(nowMs) {
    const cv = $('motionPreviewCanvas');
    const vid = $('previewVideo');
    if (cv && layers.length) {
      const tNow = (vid && !vid.hidden && !vid.paused) ? vid.currentTime : ((nowMs / 1000) % 12);
      let active = layers.find((l) => !vid || vid.hidden ? true : (tNow >= l.start && tNow <= l.end));
      if (!active && vid && vid.paused) active = layers[0];
      if (active) {
        cv.hidden = false;
        const pos = active.position || (active.params && active.params.position) || 'top-center';
        cv.dataset.pos = pos;
        const sc = Math.max(0.55, Math.min(1.35, Number(active.scale || 100) / 100));
        cv.style.transform = pos === 'top-center' || pos === 'bottom-card' || pos === 'center'
          ? `translateX(-50%) scale(${sc})`
          : `scale(${sc})`;
        const dur = Math.max(1.2, (active.end - active.start) || 3.2);
        const prog = (vid && !vid.hidden && !vid.paused)
          ? Math.max(0, Math.min(1, (tNow - active.start) / dur))
          : ((nowMs / 1000) % dur) / dur;
        drawMotionCanvas(cv, active.template_id, active.params || {}, prog, nowMs / 1000);
      } else {
        cv.hidden = true;
      }
    } else if (cv) {
      cv.hidden = true;
    }
    // Also animate suggestion mini-canvases
    document.querySelectorAll('canvas[data-mg-thumb]').forEach((c) => {
      const idx = Number(c.dataset.mgThumb);
      const s = suggestions[idx];
      if (!s) return;
      const p = ((nowMs / 1000) % 2.8) / 2.8;
      drawMotionCanvas(c, s.template_id, s.params || {}, 0.2 + 0.72 * p, nowMs / 1000);
    });
    rafId = requestAnimationFrame(tickPreviewLoop);
  }
  rafId = requestAnimationFrame(tickPreviewLoop);

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
      cv.width = 210; cv.height = 90;
      cv.className = 'mg-thumb-cv';
      cv.dataset.mgThumb = String(idx);

      const meta = document.createElement('div');
      meta.className = 'mg-sug-meta';
      const catObj = catalog.categories.find((c) => c.id === sug.category);
      meta.innerHTML = `
        <div class="mg-badges">
          <span class="mg-pill">${catObj ? catObj.name : sug.category}</span>
          <span class="mg-pill rel-${(sug.relevance || 'Média').toLowerCase()}">Relevância: ${sug.relevance || 'Média'}</span>
          <span class="mg-time">${Number(sug.start).toFixed(1)}s – ${Number(sug.end).toFixed(1)}s</span>
        </div>
        <strong>${sug.template_name || sug.template_id}</strong>
        <p class="mg-excerpt">"${sug.excerpt || ''}"</p>
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
      swapSel.addEventListener('change', () => {
        const t = catalog.templates.find((x) => x.id === swapSel.value);
        if (!t) return;
        sug.template_id = t.id;
        sug.template_name = t.name;
        sug.category = t.category;
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
      position: sug.position || 'top-center',
      scale: Number((sug.params && sug.params.scale) || 100),
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
    layers.push({
      id: 'layer_' + Date.now(),
      template_id: t.id,
      template_name: t.name,
      category: t.category,
      start: curT,
      end: Number((curT + 3.2).toFixed(1)),
      position: (t.default_params && t.default_params.position) || 'top-center',
      scale: 100,
      params: JSON.parse(JSON.stringify(t.default_params || {})),
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
      [['top-center', 'Topo Centro'], ['top-right', 'Topo Direita'], ['top-left', 'Topo Esquerda'], ['bottom-card', 'Inferior'], ['center', 'Centro']].forEach(([v, txt]) => {
        const o = document.createElement('option'); o.value = v; o.textContent = txt;
        if (l.position === v) o.selected = true;
        posSel.append(o);
      });
      posSel.addEventListener('change', () => {
        l.position = posSel.value;
        l.params.position = posSel.value;
        l.render_status = 'pending';
        if (typeof window.onMotionLayersChanged === 'function') window.onMotionLayersChanged();
      });

      const editBtn = document.createElement('button');
      editBtn.type = 'button'; editBtn.className = 'mg-btn'; editBtn.textContent = activeEditIdx === idx ? '▲ Fechar' : '⚙️ Params';
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
        ed.innerHTML = `
          <label><span>Título</span><input type="text" data-p="title" value="${(p.title || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Subtítulo</span><input type="text" data-p="subtitle" value="${(p.subtitle || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Métrica / Valor</span><input type="text" data-p="metric" value="${(p.metric || '').replace(/"/g, '&quot;')}"></label>
          <label><span>Rótulos (vírgula)</span><input type="text" data-p="labels" value="${(Array.isArray(p.labels) ? p.labels.join(', ') : '')}"></label>
          <label><span>Cor</span><input type="color" data-p="accent_color" value="${p.accent_color || '#22C55E'}"></label>
          <label><span>Tamanho (%)</span><input type="number" min="60" max="135" step="5" data-p="scale" value="${l.scale || 100}"></label>
        `;
        ed.querySelectorAll('input').forEach((inp) => {
          inp.addEventListener('input', () => {
            const key = inp.dataset.p;
            if (key === 'labels') {
              l.params.labels = inp.value.split(',').map((s) => s.trim()).filter(Boolean);
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
      btn.textContent = '🤖 Analisando fala e sugerindo Motion Graphics…';
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
