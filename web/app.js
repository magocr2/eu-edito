if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
const PV = window.EuEditoPreview;

let selectedFile = null;
let selectedStyle = 'classic';
let selectedAlign = 'center';
let selectedFx = 'auto';
let selectedLines = 3;
let selectedRhythm = 'natural';
let selectedResolution = '1080p';
let selectedCompositions = [];
let selectedBrolls = [];
let selectedCards = [];
let activePreviewCompIdx = -1;
let activePreviewBrollIdx = -1;
let activePreviewCaptionIdx = -1;
let pendingCompUploadIdx = -1;
let lastCineFiredIdx = -1;

let deferredPrompt = null;
let lastVideoUrl = '';
let cachedVideoBlob = null;
let cachedShareFile = null;
let currentJobId = '';
let currentCaptions = [];
let flowStage = 'transcribe';
let maxExportRes = '1080p';
let currentStep = 1;
let videoUnlocked = false;

function stageRefs() {
  return {
    wrap: $('previewWrap'),
    brollLayer: $('pvBrollLayer'),
    brollImg: $('pvBrollImg'),
    brollVid: $('pvBrollVid'),
    splitStage: $('pvSplitStage'),
    cardStage: $('pvCardStage'),
  };
}

function goToStep(step) {
  const s = Math.max(1, Math.min(7, Number(step) || 1));
  if (s > 1 && !videoUnlocked) return;
  currentStep = s;
  if ($('previewCard')) $('previewCard').hidden = (s === 1 || !videoUnlocked);

  document.querySelectorAll('.wizard-step').forEach((sec) => { sec.hidden = Number(sec.dataset.step) !== s; });
  document.querySelectorAll('#wizardStepper .ws-pill').forEach((pill) => {
    const ps = Number(pill.dataset.step);
    pill.disabled = ps > 1 && !videoUnlocked;
    pill.classList.toggle('is-active', ps === s);
    pill.classList.toggle('is-done', videoUnlocked && ps < s);
  });

  const inFinal = (s === 7);
  setStickyVisible(inFinal && !$('resultBox').hidden ? ($('reviewCard') && !$('reviewCard').hidden) : inFinal);
  if (s !== 7 && $('resultBox').hidden) clearMediaPreview();
  if ($('pvStageHint')) {
    $('pvStageHint').textContent = s === 7 ? 'Prévia de legendas, B-rolls e composições' : 'Arraste a legenda ou use A-/A+';
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('#wizardStepper .ws-pill').forEach((p) => p.addEventListener('click', () => goToStep(Number(p.dataset.step))));
document.querySelectorAll('[data-next]').forEach((b) => b.addEventListener('click', () => goToStep(Number(b.dataset.next))));
document.querySelectorAll('[data-prev]').forEach((b) => b.addEventListener('click', () => goToStep(Number(b.dataset.prev))));

function markDirtyAfterRender() {
  if (flowStage === 'render' && $('resultBox') && !$('resultBox').hidden) {
    $('generateBtn').textContent = '🎨 Gerar novamente com estes ajustes →';
    setStickyVisible(true);
  }
}

function setStickyVisible(vis) { if ($('stickyCta')) $('stickyCta').hidden = !vis; }

function updateResTagDisplay() {
  let label = selectedResolution === '4k' ? '4K UHD' : selectedResolution === '1080p' ? '1080p HD' : 'Original';
  if (maxExportRes === '720p' && (selectedResolution === '1080p' || selectedResolution === '4k')) label = '720p HD';
  if ($('resTag')) $('resTag').textContent = label;
}

fetch('/api/hardware').then((r) => r.json()).then((hw) => {
  if (hw && hw.max_export_res === '720p') {
    maxExportRes = '720p';
    const b1080 = $('resGrid')?.querySelector('[data-res="1080p"]');
    if (b1080) { b1080.querySelector('strong').textContent = '720p HD'; b1080.querySelector('small').textContent = 'Nuvem rápida'; }
    const b4k = $('resGrid')?.querySelector('[data-res="4k"]');
    if (b4k) b4k.hidden = true;
    updateResTagDisplay();
  }
}).catch(() => {});

window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredPrompt = e; $('installBtn').hidden = false; });
$('installBtn')?.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt = null; $('installBtn').hidden = true;
});

function resolveActiveFx() {
  return selectedFx === 'auto' ? (PV.STYLE_DEFAULTS[selectedStyle]?.fx || 'none') : selectedFx;
}

function readGfxConfig() {
  return {
    color: $('gfxColor')?.value || ($('customColorToggle')?.checked ? $('accentColor').value : '#FACC15'),
    thickness: Number($('gfxThickness')?.value || 4.5),
    length_pct: Number($('gfxLength')?.value || 100),
    size_pct: Number($('gfxLength')?.value || 100),
    dur: Number($('gfxDur')?.value || 0.38),
    pos_offset_y: Number($('gfxPosY')?.value || 0),
    direction: $('gfxDirection')?.value || 'ltr',
    anim_out: $('gfxAnimOut')?.value || 'fade-out',
  };
}

function readCineConfig() {
  return {
    mode: $('cineModeSelect')?.value || 'off',
    intensity: Number($('cineIntensity')?.value || 45),
    trans_dur: Number($('cineTransDur')?.value || 0.26),
    hold_pad: Number($('cineHoldPad')?.value || 0.12),
    scale: Number($('cineScale')?.value || 116),
    color: $('cineColor')?.value || '#FFFFFF',
    bold: !!$('cineBoldToggle')?.checked,
    glow: !!$('cineGlowToggle')?.checked,
  };
}

function syncOverlay(animate = false, previewExit = false, demoCine = false) {
  const ov = $('liveOverlay');
  if (!ov) return;
  const isClean10 = (selectedStyle === 'clean-10');
  const lineMode = isClean10 ? 1 : selectedLines;
  $('linesGrid')?.querySelectorAll('.res-pill').forEach((b) => {
    const l = Number(b.dataset.lines || 3);
    b.disabled = isClean10 && l !== 1;
    b.classList.toggle('is-active', l === lineMode);
  });

  const isBold = !!$('boldToggle')?.checked;
  const activeFx = resolveActiveFx();
  const fxCls = activeFx !== 'none' ? ` has-fx-${activeFx}` : '';
  const modeCls = (lineMode === 1 ? ' is-one-line' : (lineMode === 2 ? ' is-two-line' : '')) + (isBold ? ' is-bold' : '') + fxCls + ` align-${selectedAlign}`;
  ov.className = 'live-overlay style-' + selectedStyle + modeCls;

  const upper = PV.STYLE_DEFAULTS[selectedStyle]?.upper ?? true;
  if (activePreviewCaptionIdx >= 0 && currentCaptions[activePreviewCaptionIdx]) {
    ov.innerHTML = PV.buildCaptionHtmlFromData(currentCaptions[activePreviewCaptionIdx], selectedStyle, upper);
  } else {
    ov.innerHTML = PV.EXAMPLES[selectedStyle] || PV.EXAMPLES.classic;
  }

  const gfxCfg = readGfxConfig();
  const accentCol = $('customColorToggle')?.checked ? $('accentColor').value : (PV.STYLE_DEFAULTS[selectedStyle]?.accent || '#FACC15');
  ov.querySelectorAll('strong').forEach((mn, i) => {
    if (i === 0) PV.injectGraphicEffect(mn, activeFx, gfxCfg, accentCol);
  });

  if (lineMode === 2 && ov.children.length === 3 && !ov.querySelector('.row-wrap')) {
    const thirdTxt = ov.children[2].textContent.trim();
    if (thirdTxt.split(/\s+/).length <= 1) ov.children[2].remove();
    else {
      const wrap = document.createElement('div'); wrap.className = 'row-wrap';
      wrap.append(ov.children[1], ov.children[2]); ov.append(wrap);
    }
  }

  ov.style.top = ($('posY')?.value || 74) + '%';
  const sc = Number($('capScale')?.value || 100);
  const wSp = Number($('wordSpacing')?.value || 1.0);
  ov.style.setProperty('--cap-scale', (sc / 100).toFixed(2));
  ov.style.setProperty('--text-col', $('textColor')?.value || '#FFFFFF');
  ov.style.setProperty('--cap-ls', ($('letterSpacing')?.value || 0) + 'px');
  ov.style.setProperty('--cap-ws', Math.round((wSp - 1.0) * 8) + 'px');
  ov.style.setProperty('--cap-line-gap', Math.max(0, Math.round((Number($('lineSpacing')?.value || 1) - 1) * 14 + 2)) + 'px');
  ov.style.setProperty('--cap-shad', ($('shadowVal')?.value || 2) + 'px');
  ov.style.removeProperty('--cap-fit');

  if ($('pvLayeredBg')) {
    $('pvLayeredBg').hidden = (selectedStyle !== 'layered-type');
    const firstStrong = ov.querySelector('strong')?.textContent;
    if (firstStrong) $('pvLayeredBg').textContent = firstStrong.toUpperCase();
  }

  const frame = $('previewWrap');
  if (frame && frame.clientWidth) {
    const natW = ov.scrollWidth;
    if (natW > frame.clientWidth * 0.90 && natW > 0) ov.style.setProperty('--cap-fit', Math.max(0.54, (frame.clientWidth * 0.90) / natW).toFixed(3));
  }

  const fc = $('fontSelect')?.value || '';
  if (fc && PV.FONT_CSS_MAP[fc]) {
    const [ff, fst] = PV.FONT_CSS_MAP[fc];
    ov.classList.add('has-custom-font'); ov.style.setProperty('--main-font', ff); ov.style.setProperty('--main-style', fst);
  } else ov.classList.remove('has-custom-font');

  const sfc = $('smallFontSelect')?.value || '';
  if (sfc && PV.FONT_CSS_MAP[sfc]) {
    const [sff, sfst, swt] = PV.FONT_CSS_MAP[sfc];
    ov.classList.add('has-custom-small-font'); ov.style.setProperty('--small-font', sff);
    ov.style.setProperty('--small-style', sfst); ov.style.setProperty('--small-weight', isBold ? '800' : swt);
  } else ov.classList.remove('has-custom-small-font');

  if ($('customColorToggle')?.checked) ov.style.setProperty('--accent', $('accentColor').value);
  else ov.style.removeProperty('--accent');

  // Update displayed values cleanly
  const vals = [
    ['posYVal', ($('posY')?.value || 74) + '%'], ['capScaleVal', sc + '%'],
    ['lineSpVal', ($('lineSpacing')?.value || '1.0') + 'x'], ['wordSpVal', wSp.toFixed(1) + 'x'],
    ['letterSpVal', $('letterSpacing')?.value || '0'], ['gfxThickVal', $('gfxThickness')?.value || '4.5'],
    ['gfxLenVal', ($('gfxLength')?.value || '100') + '%'], ['gfxDurVal', ($('gfxDur')?.value || '0.38') + 's'],
    ['gfxPosYVal', ($('gfxPosY')?.value || '0') + 'px'], ['animDurVal', ($('animDur')?.value || '0.28') + 's'],
    ['animIntVal', ($('animIntensity')?.value || '1.0') + 'x'], ['cineIntVal', ($('cineIntensity')?.value || '45') + '%'],
    ['cineTransVal', ($('cineTransDur')?.value || '0.26') + 's'], ['cineHoldVal', ($('cineHoldPad')?.value || '0.12') + 's'],
    ['cineScaleVal', ($('cineScale')?.value || '116') + '%'],
  ];
  vals.forEach(([id, txt]) => { if ($(id)) $(id).textContent = txt; });

  if (animate) {
    const inKind = $('animInSelect')?.value || PV.STYLE_DEFAULTS[selectedStyle]?.animIn || 'pop';
    const outKind = $('animOutSelect')?.value || 'fade-out';
    const dSec = Number($('animDur')?.value || 0.28);
    const inten = Number($('animIntensity')?.value || 1.0);
    [...ov.querySelectorAll('small, strong, .row-wrap')].forEach((node, idx) => {
      PV.animateElementInOut(node, inKind, outKind, dSec, inten, previewExit, (inKind === 'stagger') ? idx * 75 : idx * 30);
    });
  }

  if (demoCine) {
    const spotNodes = [...ov.querySelectorAll('[data-cine="1"]')];
    const targetSpots = spotNodes.length ? spotNodes : [ov.querySelector('strong') || ov.querySelector('small')].filter(Boolean);
    PV.triggerCinematicDim($('pvCineDim'), targetSpots, readCineConfig(), 1100);
  }
}

/* ---------- Tabs Filtering (3 Caption Categories, 4 Graphic Categories, 4 Composition Categories) ---------- */
function bindCategoryTabs(tabsId, gridId, attrName) {
  $(tabsId)?.querySelectorAll('.cat-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      $(tabsId).querySelectorAll('.cat-tab').forEach((t) => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      const target = tab.dataset[attrName];
      $(gridId)?.querySelectorAll('.style-pill').forEach((p) => { p.hidden = (p.dataset[attrName] !== target); });
    });
  });
}
bindCategoryTabs('catTabs', 'styleGrid', 'cat');
bindCategoryTabs('gfxCatTabs', 'highlightFxGrid', 'gcat');
bindCategoryTabs('compCatTabs', 'compAddGrid', 'ccat');

$('styleGrid')?.querySelectorAll('.style-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('styleGrid').querySelectorAll('.style-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedStyle = btn.dataset.style;
    const def = PV.STYLE_DEFAULTS[selectedStyle];
    if (def) { if ($('accentColor')) $('accentColor').value = def.accent; if ($('posY')) $('posY').value = String(def.posY); }
    syncOverlay(true); markDirtyAfterRender();
  });
});

$('alignGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('alignGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active'); selectedAlign = btn.dataset.align || 'center';
    syncOverlay(false); markDirtyAfterRender();
  });
});

$('highlightFxGrid')?.querySelectorAll('.style-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('highlightFxGrid').querySelectorAll('.style-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active'); selectedFx = btn.dataset.fx || 'auto';
    syncOverlay(true); markDirtyAfterRender();
  });
});

$('linesGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('linesGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active'); selectedLines = Number(btn.dataset.lines || 3);
    syncOverlay(true); markDirtyAfterRender();
  });
});

[
  'customColorToggle', 'accentColor', 'textColor', 'posY', 'capScale', 'boldToggle',
  'lineSpacing', 'wordSpacing', 'letterSpacing', 'outlineVal', 'shadowVal',
  'gfxColor', 'gfxThickness', 'gfxLength', 'gfxDur', 'gfxPosY', 'gfxDirection', 'gfxAnimOut',
  'cineModeSelect', 'cineIntensity', 'cineTransDur', 'cineHoldPad', 'cineScale', 'cineColor', 'cineBoldToggle', 'cineGlowToggle',
].forEach((id) => {
  $(id)?.addEventListener('input', () => {
    if (id === 'customColorToggle' && $('accentColor')) $('accentColor').disabled = !$('customColorToggle').checked;
    syncOverlay(id.startsWith('gfx'), false); markDirtyAfterRender();
  });
  $(id)?.addEventListener('change', () => { syncOverlay(id.startsWith('gfx'), false); markDirtyAfterRender(); });
});

['fontSelect', 'smallFontSelect', 'animInSelect', 'animOutSelect', 'animDur', 'animIntensity'].forEach((id) => {
  $(id)?.addEventListener('change', () => { syncOverlay(true); markDirtyAfterRender(); });
  $(id)?.addEventListener('input', () => { syncOverlay(true); markDirtyAfterRender(); });
});

$('gfxReplayBtn')?.addEventListener('click', () => syncOverlay(true, false));
$('animReplayBtn')?.addEventListener('click', () => syncOverlay(true, true));
$('cineReplayBtn')?.addEventListener('click', () => syncOverlay(false, false, true));

// Touch drag (vertical position) + pinch / A-/A+ scale
(() => {
  const ov = $('liveOverlay'), frame = $('previewWrap'); if (!ov || !frame) return;
  const badge = $('pvLiveBadge'); let timer = null;
  const flash = (t) => { if (!badge) return; badge.textContent = t; clearTimeout(timer); timer = setTimeout(() => { badge.textContent = '↕ Pinça'; }, 1300); };
  const setSc = (p) => { const c = Math.round(Math.max(65, Math.min(135, p))); if ($('capScale')) $('capScale').value = String(c); syncOverlay(false); markDirtyAfterRender(); flash(`${c}% · ${$('posY').value}%`); };
  $('pvSizeDown')?.addEventListener('click', (e) => { e.stopPropagation(); setSc(Number($('capScale')?.value || 100) - 5); });
  $('pvSizeUp')?.addEventListener('click', (e) => { e.stopPropagation(); setSc(Number($('capScale')?.value || 100) + 5); });
  const ptrs = new Map(); let sy = 0, oy = 74, pdist = 0, osc = 100;
  const d2 = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  ov.addEventListener('pointerdown', (e) => {
    ptrs.set(e.pointerId, e); try { ov.setPointerCapture(e.pointerId); } catch {}
    if (ptrs.size === 1) { sy = e.clientY; oy = Number($('posY')?.value || 74); }
    else if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pdist = Math.max(10, d2(a, b)); osc = Number($('capScale')?.value || 100); }
    e.preventDefault();
  });
  window.addEventListener('pointermove', (e) => {
    if (!ptrs.has(e.pointerId)) return; ptrs.set(e.pointerId, e);
    if (ptrs.size >= 2) { const [a, b] = [...ptrs.values()]; if (pdist > 0) setSc(osc * (d2(a, b) / pdist)); return; }
    const r = frame.getBoundingClientRect(); if (!r.height) return;
    const ny = Math.round(Math.max(14, Math.min(86, oy + ((e.clientY - sy) / r.height) * 100)));
    if ($('posY')) $('posY').value = String(ny); syncOverlay(false); markDirtyAfterRender(); flash(`${$('capScale')?.value || 100}% · ${ny}%`);
  });
  const end = (e) => ptrs.delete(e.pointerId);
  window.addEventListener('pointerup', end); window.addEventListener('pointercancel', end);
})();

/* ---------- Step 7 Compositions, Quick B-rolls & Cards ---------- */
function clearMediaPreview() {
  activePreviewCompIdx = -1; activePreviewBrollIdx = -1;
  const r = stageRefs(); r.wrap?.classList.remove('split-top', 'split-bottom');
  if (r.brollVid) { try { r.brollVid.pause(); } catch {} r.brollVid.hidden = true; r.brollVid.removeAttribute('src'); }
  if (r.brollImg) { r.brollImg.hidden = true; r.brollImg.removeAttribute('src'); }
  if (r.brollLayer) r.brollLayer.hidden = true;
  if (r.splitStage) r.splitStage.hidden = true;
  if (r.cardStage) { r.cardStage.hidden = true; r.cardStage.replaceChildren(); }
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = true;
}
$('clearPreviewMediaBtn')?.addEventListener('click', clearMediaPreview);

function previewCompositionInStage(idx) {
  const c = selectedCompositions[idx]; if (!c) return;
  activePreviewCompIdx = idx; PV.renderCompositionStage(c, stageRefs());
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
}

function createDefaultComposition(type) {
  const base = {
    type, start: '', end: '', title: '', subtitle: '', tag: '', labels: [], media: [],
    bg_color: '#FFFFFF', accent_color: '#F472B6', text_color: '#111827',
    x: 8, y: 12, scale: 42, aspect: 'landscape', radius: 22, shadow: 55,
    stack_count: 3, stack_gap: 14, orientation: 'vertical', split_ratio: 50, gap: 10, highlight_pane: 'a',
    anim_in: 'scale-in', anim_out: 'fade-out', anim_dur: 0.34, anim_intensity: 1.0,
  };
  if (type === 'editorial-card') { base.title = 'Ponto principal'; base.subtitle = 'Explicação clara ao espectador.'; base.tag = 'DESTAQUE'; base.scale = 74; base.y = 18; base.anim_in = 'slide-up'; }
  if (type === 'stacked-cards') { base.title = 'Etapas'; base.labels = ['Etapa 1', 'Etapa 2', 'Etapa 3', 'Etapa 4']; base.anim_in = 'stagger'; base.y = 14; }
  if (type === 'visual-storytelling') { base.title = 'Como Funciona'; base.tag = 'ANÁLISE'; base.bg_color = '#0F172A'; base.text_color = '#F8FAFC'; base.accent_color = '#38BDF8'; base.labels = ['Principal', 'Detalhe A', 'Detalhe B']; base.anim_in = 'stagger'; }
  if (type === 'split-composition') { base.anim_in = 'reveal'; base.accent_color = '#22C55E'; }
  return base;
}

$('compAddGrid')?.querySelectorAll('.style-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    if (btn.dataset.brollQuick) { $('brollFile')?.click(); return; }
    if (btn.dataset.cardQuick) { $('cardFile')?.click(); return; }
    const c = createDefaultComposition(btn.dataset.comp);
    selectedCompositions.push(c); renderCompList();
    previewCompositionInStage(selectedCompositions.length - 1); markDirtyAfterRender();
  });
});

function renderCompList() {
  const list = $('compList'); if (!list) return; list.replaceChildren();
  selectedCompositions.forEach((comp, idx) => {
    const card = document.createElement('div'); card.className = 'comp-card-item';
    const names = { 'floating-media': 'Mídia Flutuante', 'editorial-card': 'Editorial Card', 'stacked-cards': 'Imagens Empilhadas', 'visual-storytelling': 'Visual Storytelling', 'split-composition': 'Split Composition' };
    const isCardText = ['editorial-card', 'stacked-cards', 'visual-storytelling'].includes(comp.type);
    const isSplit = comp.type === 'split-composition';
    const isStack = comp.type === 'stacked-cards';
    const isFloat = comp.type === 'floating-media';
    card.innerHTML = `
      <div class="comp-card-head">
        <strong>${idx + 1}. ${names[comp.type] || comp.type}</strong>
        <button type="button" class="media-preview-btn" data-act="pv">👁️ Prévia</button>
        <button type="button" class="media-del" data-act="del">✕</button>
      </div>
      <div class="row-2">
        <button type="button" class="broll-upload-btn" data-act="up">＋ Enviar mídia(s) (${comp.media.length})</button>
        <div class="media-times"><span>Início:</span><input type="number" step="0.5" min="0" class="media-time-in" data-k="start" value="${comp.start}" placeholder="Auto"><span>Fim:</span><input type="number" step="0.5" min="0" class="media-time-in" data-k="end" value="${comp.end}" placeholder="Auto"></div>
      </div>
      ${isFloat ? `<div class="row-2"><label class="field"><span>Proporção</span><select data-k="aspect"><option value="landscape" ${comp.aspect === 'landscape' ? 'selected' : ''}>Horizontal (16:9)</option><option value="square" ${comp.aspect === 'square' ? 'selected' : ''}>Quadrada (1:1)</option><option value="portrait" ${comp.aspect === 'portrait' ? 'selected' : ''}>Vertical (9:16)</option></select></label><label class="field"><span>Sombra (${comp.shadow}%)</span><input type="range" min="0" max="100" step="10" data-k="shadow" value="${comp.shadow}"></label></div>` : ''}
      ${isStack ? `<div class="row-2"><label class="field"><span>Qtd imagens (${comp.stack_count})</span><input type="range" min="2" max="4" step="1" data-k="stack_count" value="${comp.stack_count}"></label><label class="field"><span>Espaçamento (${comp.stack_gap}%)</span><input type="range" min="6" max="24" step="2" data-k="stack_gap" value="${comp.stack_gap}"></label></div>` : ''}
      ${isCardText ? `<div class="row-2"><label class="field"><span>Título</span><input type="text" data-k="title" value="${comp.title}"></label><label class="field"><span>Etiqueta</span><input type="text" data-k="tag" value="${comp.tag}"></label></div><label class="field"><span>Texto auxiliar</span><input type="text" data-k="subtitle" value="${comp.subtitle}"></label>` : ''}
      ${isSplit ? `<div class="row-2"><label class="field"><span>Divisão</span><select data-k="orientation"><option value="vertical" ${comp.orientation === 'vertical' ? 'selected' : ''}>Vertical (Topo/Base)</option><option value="horizontal" ${comp.orientation === 'horizontal' ? 'selected' : ''}>Horizontal (Esq/Dir)</option></select></label><label class="field"><span>Proporção A (${comp.split_ratio}%)</span><input type="range" min="30" max="70" step="5" data-k="split_ratio" value="${comp.split_ratio}"></label></div><div class="row-2"><label class="field"><span>Área destacada</span><select data-k="highlight_pane"><option value="a" ${comp.highlight_pane === 'a' ? 'selected' : ''}>Área A</option><option value="b" ${comp.highlight_pane === 'b' ? 'selected' : ''}>Área B</option><option value="none" ${comp.highlight_pane === 'none' ? 'selected' : ''}>Sem borda</option></select></label><label class="field"><span>Espaço (${comp.gap}px)</span><input type="range" min="0" max="24" step="2" data-k="gap" value="${comp.gap}"></label></div>`
        : `<div class="row-2"><label class="field"><span>Posição X/Y (%)</span><div class="row-2"><input type="number" min="0" max="85" data-k="x" value="${comp.x}"><input type="number" min="0" max="85" data-k="y" value="${comp.y}"></div></label><label class="field"><span>Tamanho (${comp.scale}%)</span><input type="range" min="25" max="88" step="2" data-k="scale" value="${comp.scale}"></label></div>`}
      <div class="row-2"><label class="field"><span>Cor destaque</span><input type="color" data-k="accent_color" value="${comp.accent_color}"></label><label class="field"><span>${isCardText ? 'Fundo Card' : 'Cantos (px)'}</span>${isCardText ? `<input type="color" data-k="bg_color" value="${comp.bg_color}">` : `<input type="range" min="0" max="40" step="2" data-k="radius" value="${comp.radius}">`}</label></div>
      <div class="row-2"><label class="field"><span>Entrada</span><select data-k="anim_in">${['fade-in', 'scale-in', 'slide-up', 'slide-down', 'slide-left', 'slide-right', 'pop', 'reveal', 'stagger', 'none'].map((a) => `<option value="${a}" ${comp.anim_in === a ? 'selected' : ''}>${a}</option>`).join('')}</select></label><label class="field"><span>Saída</span><select data-k="anim_out">${['fade-out', 'scale-in', 'slide-up', 'slide-down', 'slide-left', 'slide-right', 'reveal', 'none'].map((a) => `<option value="${a}" ${comp.anim_out === a ? 'selected' : ''}>${a}</option>`).join('')}</select></label></div>
    `;
    card.querySelector('[data-act="pv"]')?.addEventListener('click', () => previewCompositionInStage(idx));
    card.querySelector('[data-act="del"]')?.addEventListener('click', () => { selectedCompositions.splice(idx, 1); clearMediaPreview(); renderCompList(); markDirtyAfterRender(); });
    card.querySelector('[data-act="up"]')?.addEventListener('click', () => { pendingCompUploadIdx = idx; $('compMediaInput')?.click(); });
    card.querySelectorAll('[data-k]').forEach((inp) => {
      const ev = (inp.tagName === 'SELECT' || inp.type === 'color') ? 'change' : 'input';
      inp.addEventListener(ev, () => {
        const k = inp.dataset.k;
        comp[k] = (inp.type === 'range' || inp.type === 'number') ? (inp.value === '' ? '' : Number(inp.value)) : inp.value;
        previewCompositionInStage(idx); markDirtyAfterRender();
      });
    });
    list.append(card);
  });
}

$('compMediaInput')?.addEventListener('change', async (e) => {
  const files = [...(e.target.files || [])]; if (!files.length || pendingCompUploadIdx < 0 || !selectedCompositions[pendingCompUploadIdx]) return;
  const comp = selectedCompositions[pendingCompUploadIdx];
  for (const f of files) {
    try {
      const fd = new FormData(); fd.append('broll', f, f.name);
      const data = await safeJson(await fetch('/api/upload_broll', { method: 'POST', body: fd }));
      if (data.broll_id) comp.media.push({ id: data.broll_id, name: f.name, previewUrl: URL.createObjectURL(f), isImage: (f.type || '').startsWith('image/') });
    } catch {}
  }
  e.target.value = ''; renderCompList(); previewCompositionInStage(pendingCompUploadIdx); markDirtyAfterRender();
});

function renderBrollList() {
  const list = $('brollList'); if (!list) return; list.replaceChildren();
  selectedBrolls.forEach((b, idx) => {
    const row = document.createElement('div'); row.className = 'media-item';
    const lbl = document.createElement('span'); lbl.className = 'media-name'; lbl.textContent = `🎞️ B${idx + 1} · ${b.name}`;
    const sel = document.createElement('select'); sel.className = 'media-sel';
    [['auto', 'Automático'], ['top', 'Topo (c/ máscara)'], ['bottom', 'Baixo (c/ máscara)'], ['pip-rounded', 'Janela Canto'], ['center-frame', 'Quadro Central'], ['full', 'Tela cheia']].forEach(([v, t]) => {
      const o = document.createElement('option'); o.value = v; o.textContent = t; if (b.layout === v) o.selected = true; sel.append(o);
    });
    sel.addEventListener('change', () => { b.layout = sel.value; previewBrollInStage(idx); markDirtyAfterRender(); });
    const pvBtn = document.createElement('button'); pvBtn.type = 'button'; pvBtn.className = 'media-preview-btn'; pvBtn.textContent = '👁️';
    pvBtn.addEventListener('click', () => previewBrollInStage(idx));
    const del = document.createElement('button'); del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => { selectedBrolls.splice(idx, 1); clearMediaPreview(); renderBrollList(); markDirtyAfterRender(); });
    row.append(lbl, pvBtn, sel, del); list.append(row);
  });
}

function previewBrollInStage(idx) {
  const b = selectedBrolls[idx]; if (!b) return;
  activePreviewBrollIdx = idx; const bl = $('pvBrollLayer'); if (!bl) return;
  bl.dataset.layout = b.layout || 'top'; bl.hidden = false; bl.style.cssText = '';
  $('previewWrap')?.classList.toggle('split-top', b.layout === 'top');
  $('previewWrap')?.classList.toggle('split-bottom', b.layout === 'bottom');
  if (b.isImage) { $('pvBrollVid').hidden = true; $('pvBrollImg').src = b.previewUrl; $('pvBrollImg').hidden = false; }
  else { $('pvBrollImg').hidden = true; $('pvBrollVid').src = b.previewUrl; $('pvBrollVid').hidden = false; $('pvBrollVid').play?.().catch(() => {}); }
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
}

function renderCardList() {
  const list = $('cardList'); if (!list) return; list.replaceChildren();
  selectedCards.forEach((c, idx) => {
    const row = document.createElement('div'); row.className = 'media-item';
    const img = document.createElement('img'); img.className = 'media-thumb'; img.src = c.url; img.alt = c.name;
    const lbl = document.createElement('span'); lbl.className = 'media-name'; lbl.textContent = `C${idx + 1} · ${c.name}`;
    const del = document.createElement('button'); del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => { selectedCards.splice(idx, 1); clearMediaPreview(); renderCardList(); markDirtyAfterRender(); });
    row.append(img, lbl, del); list.append(row);
  });
}

$('brollFile')?.addEventListener('change', async (e) => {
  for (const f of [...(e.target.files || [])]) {
    try {
      const fd = new FormData(); fd.append('broll', f, f.name);
      const data = await safeJson(await fetch('/api/upload_broll', { method: 'POST', body: fd }));
      if (data.broll_id) selectedBrolls.push({ id: data.broll_id, name: f.name, layout: 'top', start: '', end: '', previewUrl: URL.createObjectURL(f), isImage: (f.type || '').startsWith('image/') });
    } catch {}
  }
  e.target.value = ''; renderBrollList(); if (selectedBrolls.length) previewBrollInStage(selectedBrolls.length - 1);
});

$('cardFile')?.addEventListener('change', async (e) => {
  for (const f of [...(e.target.files || [])]) {
    try {
      const fd = new FormData(); fd.append('card', f, f.name); fd.append('remove_bg', '1');
      const data = await safeJson(await fetch('/api/upload_card', { method: 'POST', body: fd }));
      if (data.card_id) selectedCards.push({ id: data.card_id, name: f.name, url: data.url, anim: 'side-right' });
    } catch {}
  }
  e.target.value = ''; renderCardList();
});

$('cutsToggle')?.addEventListener('change', () => { $('rhythmBox').hidden = !$('cutsToggle').checked; });
$('rhythmGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => { $('rhythmGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active')); btn.classList.add('is-active'); selectedRhythm = btn.dataset.rhythm; });
});
$('resGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => { $('resGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active')); btn.classList.add('is-active'); selectedResolution = btn.dataset.res; updateResTagDisplay(); });
});

/* ---------- Safe Zones, Timeline Playback & Review Editor ---------- */
const SAFE_MODES = [
  { id: 'off', label: '📱 Área segura', bottom: '' },
  { id: 'reels', label: '📱 Reels', bottom: 'Botões / Legenda Reels' },
  { id: 'tiktok', label: '🎵 TikTok', bottom: 'Descrição / Som TikTok' },
  { id: 'shorts', label: '▶ Shorts', bottom: 'Título / Canal Shorts' },
];
let safeModeIdx = 0;
$('safeZoneBtn')?.addEventListener('click', () => {
  safeModeIdx = (safeModeIdx + 1) % SAFE_MODES.length;
  const m = SAFE_MODES[safeModeIdx], sz = $('safeZones'), on = m.id !== 'off';
  sz.hidden = !on; if (on) { sz.dataset.platform = m.id; sz.querySelector('.sz-bottom').textContent = m.bottom; }
  $('safeZoneBtn').textContent = m.label; $('safeZoneBtn').classList.toggle('is-on', on);
});

$('previewVideo')?.addEventListener('timeupdate', () => {
  const vid = $('previewVideo'); if (!vid || !$('resultBox').hidden) return;
  const t = vid.currentTime || 0;
  if (currentCaptions.length) {
    const capIdx = currentCaptions.findIndex((c) => t >= Number(c.orig_s ?? c.s ?? 0) && t <= Number(c.orig_e ?? c.e ?? 999));
    if (capIdx >= 0 && activePreviewCaptionIdx !== capIdx) {
      activePreviewCaptionIdx = capIdx; syncOverlay(true);
    }
    const cCfg = readCineConfig();
    if (capIdx >= 0 && cCfg.mode !== 'off' && lastCineFiredIdx !== capIdx) {
      const cap = currentCaptions[capIdx];
      const hasManualCine = Array.isArray(cap.cine_indices) && cap.cine_indices.length > 0;
      const shouldFire = (cCfg.mode === 'manual' && hasManualCine) || (cCfg.mode === 'auto' && capIdx % 4 === 1);
      if (shouldFire) {
        lastCineFiredIdx = capIdx;
        syncOverlay(false, false, true);
      }
    }
  }
  if (selectedCompositions.length && currentStep === 7) {
    const ci = selectedCompositions.findIndex((c) => {
      const s = parseFloat(c.start); if (isNaN(s)) return false;
      const e = isNaN(parseFloat(c.end)) ? s + 3.5 : parseFloat(c.end);
      return t >= s && t <= e;
    });
    if (ci >= 0 && activePreviewCompIdx !== ci) previewCompositionInStage(ci);
    else if (ci < 0 && selectedCompositions.some((c) => c.start !== '') && activePreviewCompIdx >= 0) clearMediaPreview();
  }
});

$('videoFile').addEventListener('change', (e) => {
  const f = e.target.files?.[0]; if (!f) return;
  selectedFile = f; videoUnlocked = true; currentJobId = ''; cachedVideoBlob = null; currentCaptions = [];
  flowStage = 'transcribe'; activePreviewCaptionIdx = -1; lastCineFiredIdx = -1; clearMediaPreview();
  $('reviewCard').hidden = true; $('generateBtn').textContent = '1. Transcrever & Revisar Legendas →';
  $('uploadTitle').textContent = f.name || 'Vídeo selecionado';
  $('uploadSub').textContent = ((f.size || 0) / (1024 * 1024)).toFixed(1) + ' MB · Pronto!';
  if ($('step1Nav')) $('step1Nav').hidden = false;
  try {
    const vid = $('previewVideo'); vid.src = URL.createObjectURL(f); vid.muted = true; vid.hidden = false; $('emptyStage').hidden = true;
    vid.addEventListener('loadedmetadata', () => { try { vid.currentTime = 0.001; vid.play().then(() => setTimeout(() => { vid.pause(); vid.muted = false; vid.currentTime = 0.001; }, 80)).catch(() => { vid.muted = false; }); } catch {} }, { once: true });
    vid.load();
  } catch {}
  $('liveOverlay').hidden = false; $('resultBox').hidden = true; $('errorMsg').hidden = true; $('generateBtn').disabled = false;
  goToStep(2);
});

function guessDefaultMainIdx(tokens) {
  let best = 0, bestLen = -1;
  tokens.forEach((t, i) => { const c = t.replace(/[^\p{L}\p{N}]/gu, '').length; if (c > bestLen) { bestLen = c; best = i; } });
  return best;
}

function renderCaptionEditor(captions) {
  currentCaptions = (captions || []).map((c) => ({ ...c }));
  const list = $('captionEditorList'); list.replaceChildren();
  currentCaptions.forEach((cap, idx) => {
    const row = document.createElement('div'); row.className = 'cap-edit-row';
    const topBar = document.createElement('div'); topBar.className = 'cap-edit-top';
    const playBtn = document.createElement('button'); playBtn.type = 'button'; playBtn.className = 'cap-edit-play'; playBtn.textContent = '▶';
    playBtn.addEventListener('click', () => {
      activePreviewCaptionIdx = idx; syncOverlay(true);
      const vid = $('previewVideo'); if (vid) { vid.muted = false; vid.currentTime = Math.max(0, Number(cap.orig_s ?? cap.s ?? 0) - 0.1); vid.play().catch(() => {}); }
    });
    const tm = document.createElement('span'); tm.className = 'cap-edit-time'; tm.textContent = Number(cap.s || 0).toFixed(1) + 's';
    const inp = document.createElement('input'); inp.type = 'text'; inp.className = 'cap-edit-input'; inp.value = cap.text || '';
    const chipsBox = document.createElement('div'); chipsBox.className = 'cap-word-chips';

    function renderChips() {
      const toks = (inp.value || '').replace(/[|\n]+/g, ' ').trim().split(/\s+/).filter(Boolean);
      chipsBox.replaceChildren(); if (!toks.length) return;
      if (!Array.isArray(currentCaptions[idx].main_indices) || !currentCaptions[idx].main_indices.length) {
        const defI = currentCaptions[idx].main_idx ?? guessDefaultMainIdx(toks);
        currentCaptions[idx].main_indices = [defI]; currentCaptions[idx].main_idx = defI;
      }
      const mSet = new Set(currentCaptions[idx].main_indices);
      const cSet = new Set(currentCaptions[idx].cine_indices || []);
      toks.forEach((tok, wIdx) => {
        const chip = document.createElement('button'); chip.type = 'button';
        chip.className = 'cap-word-chip' + (mSet.has(wIdx) ? ' is-main' : ''); chip.textContent = tok;
        chip.addEventListener('click', () => {
          const curSet = new Set(currentCaptions[idx].main_indices || []);
          if (curSet.has(wIdx) && curSet.size > 1) curSet.delete(wIdx); else curSet.add(wIdx);
          currentCaptions[idx].main_indices = [...curSet].sort((a, b) => a - b);
          currentCaptions[idx].main_idx = currentCaptions[idx].main_indices[0];
          activePreviewCaptionIdx = idx; renderChips(); syncOverlay(true); markDirtyAfterRender();
        });
        chipsBox.append(chip);
      });

      const cineBtn = document.createElement('button'); cineBtn.type = 'button';
      cineBtn.className = 'cap-chip-cine' + (cSet.size ? ' is-on' : '');
      cineBtn.textContent = cSet.size ? '🎬 Holofote ON' : '🎬 Holofote';
      cineBtn.title = 'Aplicar escurecimento cinematográfico somente na palavra em destaque deste trecho';
      cineBtn.addEventListener('click', () => {
        if (cSet.size) currentCaptions[idx].cine_indices = [];
        else {
          currentCaptions[idx].cine_indices = [currentCaptions[idx].main_idx ?? 0];
          if ($('cineModeSelect') && $('cineModeSelect').value === 'off') $('cineModeSelect').value = 'manual';
        }
        activePreviewCaptionIdx = idx; renderChips();
        syncOverlay(false, false, !!currentCaptions[idx].cine_indices.length);
        markDirtyAfterRender();
      });
      chipsBox.append(cineBtn);
    }
    renderChips();

    inp.addEventListener('focus', () => { activePreviewCaptionIdx = idx; syncOverlay(false); });
    inp.addEventListener('input', () => { currentCaptions[idx].text = inp.value; activePreviewCaptionIdx = idx; renderChips(); syncOverlay(false); markDirtyAfterRender(); });
    const cutBtn = document.createElement('button'); cutBtn.type = 'button'; cutBtn.className = 'cap-edit-cut'; cutBtn.textContent = cap.cut ? 'Voltar' : '✂️';
    cutBtn.addEventListener('click', () => {
      currentCaptions[idx].cut = !currentCaptions[idx].cut; row.classList.toggle('is-cut', !!currentCaptions[idx].cut);
      cutBtn.textContent = currentCaptions[idx].cut ? 'Voltar' : '✂️'; markDirtyAfterRender();
    });
    topBar.append(playBtn, tm, inp, cutBtn); row.append(topBar, chipsBox); list.append(row);
  });
}

async function safeJson(res) {
  const txt = await res.text();
  try { return JSON.parse(txt); } catch { throw new Error(`Servidor ocupado (HTTP ${res.status}).`); }
}

function uploadWithProgress(file) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open('POST', '/api/upload', true);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.min(25, Math.max(5, Math.round((e.loaded / e.total) * 25)));
        $('progressText').textContent = `Enviando vídeo… (${Math.round((e.loaded / e.total) * 100)}%)`;
        $('progressPct').textContent = pct + '%'; $('progressFill').style.width = pct + '%';
      }
    };
    xhr.onload = () => {
      try { const d = JSON.parse(xhr.responseText || '{}'); if (xhr.status >= 200 && xhr.status < 300 && !d.error) resolve(d); else reject(new Error(d.error || 'Erro no upload.')); }
      catch { reject(new Error(`Resposta inválida (${xhr.status}).`)); }
    };
    xhr.onerror = () => reject(new Error('Falha de rede.'));
    const fd = new FormData(); fd.append('video', file, file.name || 'video.mp4'); xhr.send(fd);
  });
}

$('generateBtn').addEventListener('click', async () => {
  if (!selectedFile) return;
  $('generateBtn').disabled = true; $('errorMsg').hidden = true; $('resultBox').hidden = true;
  $('progressBox').hidden = false; $('progressBox').scrollIntoView({ behavior: 'smooth', block: 'center' });
  try {
    if (flowStage === 'transcribe') {
      $('progressText').textContent = 'Enviando vídeo do celular…'; $('progressPct').textContent = '5%'; $('progressFill').style.width = '5%';
      const up = await uploadWithProgress(selectedFile); currentJobId = up.job_id;
      const tr = await safeJson(await fetch('/api/transcribe', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: currentJobId, cuts: $('cutsToggle').checked, rhythm: selectedRhythm }),
      }));
      if (tr.error) throw new Error(tr.error);
      while (true) {
        await new Promise((r) => setTimeout(r, 1200));
        const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
        $('progressText').textContent = st.message || 'Transcrevendo…'; $('progressPct').textContent = (st.progress || 0) + '%'; $('progressFill').style.width = (st.progress || 0) + '%';
        if (st.status === 'review') {
          renderCaptionEditor(st.captions || []); $('progressBox').hidden = true; $('reviewCard').hidden = false;
          $('reviewCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
          flowStage = 'render'; $('generateBtn').textContent = '2. Gerar Vídeo Pronto →'; $('generateBtn').disabled = false;
          setStickyVisible(true); return;
        }
        if (st.status === 'error') throw new Error(st.message || 'Erro na transcrição.');
      }
    }

    const cCfg = readCineConfig();
    const { data: ren } = await (async () => {
      const r = await fetch('/api/render', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: currentJobId, captions: currentCaptions, style: selectedStyle,
          accent_color: $('customColorToggle')?.checked ? $('accentColor').value : '',
          text_color: $('textColor')?.value || '#FFFFFF',
          pos_y: Number($('posY').value), alignment: selectedAlign,
          caption_scale: Number($('capScale')?.value || 100),
          letter_spacing: Number($('letterSpacing')?.value || 0),
          word_spacing: Number($('wordSpacing')?.value || 1.0),
          line_spacing: Number($('lineSpacing')?.value || 1.0),
          outline_val: Number($('outlineVal')?.value || 0.8),
          shadow_val: Number($('shadowVal')?.value || 2.0),
          anim_in: $('animInSelect')?.value || '',
          anim_out: $('animOutSelect')?.value || 'fade-out',
          anim_dur: Number($('animDur')?.value || 0.28),
          anim_intensity: Number($('animIntensity')?.value || 1.0),
          caption_bold: !!$('boldToggle')?.checked,
          highlight_fx: selectedFx, gfx_cfg: readGfxConfig(),
          cine_mode: cCfg.mode, cine_intensity: cCfg.intensity, cine_trans_dur: cCfg.trans_dur,
          cine_hold_pad: cCfg.hold_pad, cine_scale: cCfg.scale, cine_color: cCfg.color, cine_bold: cCfg.bold, cine_glow: cCfg.glow,
          main_font: $('fontSelect')?.value || '', small_font: $('smallFontSelect')?.value || '',
          caption_lines: selectedLines, zoom: $('zoomToggle').checked, studio_audio: $('studioAudioToggle').checked,
          color_grade: !!$('colorGradeToggle')?.checked,
          compositions: selectedCompositions.map((c) => ({ ...c, media: (c.media || []).map((m) => ({ id: m.id })) })),
          brolls: selectedBrolls.map((b) => ({ id: b.id, layout: b.layout, start: b.start, end: b.end })),
          cards: selectedCards.map((c) => ({ id: c.id, anim: c.anim })),
          resolution: selectedResolution,
        }),
      });
      return { data: await safeJson(r) };
    })();
    if (ren.error) throw new Error(ren.error);
    while (true) {
      await new Promise((r) => setTimeout(r, 1400));
      const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
      $('progressText').textContent = st.message || 'Renderizando…'; $('progressPct').textContent = (st.progress || 0) + '%'; $('progressFill').style.width = (st.progress || 0) + '%';
      if (st.status === 'done') {
        clearMediaPreview(); lastVideoUrl = st.video_url; cachedVideoBlob = null; cachedShareFile = null;
        $('previewVideo').src = st.video_url; $('previewVideo').muted = false; $('previewVideo').hidden = false;
        $('emptyStage').hidden = true; $('liveOverlay').hidden = true;
        $('downloadMp4').href = st.video_url + '?dl=1'; $('downloadMp4').download = `eu-edito-${currentJobId || 'pronto'}.mp4`;
        $('downloadSrt').href = st.srt_url; $('shareBtn').hidden = !navigator.share;
        $('transcriptText').textContent = st.transcript || '';
        $('statsRow').innerHTML = `<div class="stat-pill"><strong>${st.stats.resolution}</strong><small>Qualidade</small></div><div class="stat-pill"><strong>${st.stats.duration}s</strong><small>Duração</small></div><div class="stat-pill"><strong>${st.stats.removed_seconds}s</strong><small>Cortados</small></div>`;
        $('progressBox').hidden = true; $('resultBox').hidden = false; $('resultBox').scrollIntoView({ behavior: 'smooth', block: 'start' });
        $('generateBtn').disabled = false; setStickyVisible(false); break;
      }
      if (st.status === 'error') throw new Error(st.message || 'Erro ao renderizar.');
    }
  } catch (err) {
    $('progressBox').hidden = true; $('errorMsg').textContent = err?.message || 'Falha no processamento.'; $('errorMsg').hidden = false; $('generateBtn').disabled = false;
  }
});

$('downloadMp4')?.addEventListener('click', () => { if ($('downloadMp4') && lastVideoUrl) $('downloadMp4').download = `eu-edito-${currentJobId || 'pronto'}.mp4`; });
$('shareBtn')?.addEventListener('click', async () => {
  if (!lastVideoUrl) return;
  try {
    if (!cachedVideoBlob) { cachedVideoBlob = await (await fetch(lastVideoUrl + '?dl=1')).blob(); cachedShareFile = new File([cachedVideoBlob], `eu-edito-${currentJobId}.mp4`, { type: 'video/mp4' }); }
    if (navigator.canShare?.({ files: [cachedShareFile] })) await navigator.share({ files: [cachedShareFile], title: 'Eu Edito' }); else $('downloadMp4').click();
  } catch {}
});
$('newVideoBtn')?.addEventListener('click', () => window.location.reload());

syncOverlay(false);
goToStep(1);
