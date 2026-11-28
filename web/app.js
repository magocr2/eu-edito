if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
const PV = window.EuEditoPreview;

let selectedFile = null;
let selectedFiles = []; // [{ file, name, sizeMB, duration, thumbUrl }]
let currentTakeRanges = [];
let appendVideoMode = false;
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
let activePreviewCardIdx = -1;
let activePosTarget = null; // { kind: 'broll'|'comp'|'card', idx: number }
let detectedFaceZone = { x: 24, y: 12, w: 52, h: 42, detected: false };
let activePreviewCaptionIdx = -1;
let pendingCompUploadIdx = -1;
let pendingCardBrollIdx = -1;
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
  const s = Math.max(1, Math.min(6, Number(step) || 1));
  if (s > 1 && !videoUnlocked) return;
  currentStep = s;
  // Preview fica oculto nas Etapas 1 e 2 (aparece da Etapa 3 em diante, ou quando há resultado)
  const hasResult = $('resultBox') && !$('resultBox').hidden;
  if ($('previewCard')) $('previewCard').hidden = ((s <= 2 && !hasResult) || !videoUnlocked);

  document.querySelectorAll('.wizard-step').forEach((sec) => { sec.hidden = Number(sec.dataset.step) !== s; });
  document.querySelectorAll('#wizardStepper .ws-pill').forEach((pill) => {
    const ps = Number(pill.dataset.step);
    pill.disabled = ps > 1 && !videoUnlocked;
    pill.classList.toggle('is-active', ps === s);
    pill.classList.toggle('is-done', videoUnlocked && ps < s);
  });

  // Sticky CTA aparece nas etapas 5 (Transcrição/Revisão) e 6 (Exportar), ou quando há revisão aberta
  const inActionStep = (s === 5 || s === 6);
  if (hasResult) {
    setStickyVisible(false);
  } else if ($('reviewCard') && !$('reviewCard').hidden && s >= 5) {
    setStickyVisible(true);
  } else {
    setStickyVisible(inActionStep);
  }
  if (s !== 6 && !hasResult) clearMediaPreview();
  if ($('pvStageHint')) {
    $('pvStageHint').textContent = s === 6 ? 'Prévia de legendas, B-rolls e composições' : 'Arraste a legenda ou use A-/A+';
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
  activePreviewCompIdx = -1; activePreviewBrollIdx = -1; activePreviewCardIdx = -1;
  const r = stageRefs(); r.wrap?.classList.remove('split-top', 'split-bottom');
  if (r.brollVid) { try { r.brollVid.pause(); } catch {} r.brollVid.hidden = true; r.brollVid.removeAttribute('src'); }
  if (r.brollImg) { r.brollImg.hidden = true; r.brollImg.removeAttribute('src'); }
  if (r.brollLayer) { r.brollLayer.hidden = true; r.brollLayer.classList.remove('is-editable', 'is-overlap-warn'); }
  const brh = r.brollLayer?.querySelector('.pv-resize-handle'); if (brh) brh.hidden = true;
  if (r.splitStage) r.splitStage.hidden = true;
  if (r.cardStage) { r.cardStage.hidden = true; r.cardStage.classList.remove('is-editable', 'is-overlap-warn'); r.cardStage.replaceChildren(); }
  if ($('pvFaceBox')) $('pvFaceBox').hidden = true;
  if ($('pvCapBox')) $('pvCapBox').hidden = true;
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = true;
}
$('clearPreviewMediaBtn')?.addEventListener('click', () => { activePosTarget = null; if ($('brollPosStudio')) $('brollPosStudio').hidden = true; clearMediaPreview(); });

function getPosItemByTarget(tgt) {
  if (!tgt) return null;
  if (tgt.kind === 'broll' && selectedBrolls[tgt.idx]) return selectedBrolls[tgt.idx];
  if (tgt.kind === 'comp' && selectedCompositions[tgt.idx]) return selectedCompositions[tgt.idx];
  if (tgt.kind === 'card' && selectedCards[tgt.idx]) return selectedCards[tgt.idx];
  return null;
}

function getAllPlacedBoxes(excludeTgt) {
  const wrap = $('previewWrap');
  const boxes = [];
  selectedBrolls.forEach((b, i) => {
    if (excludeTgt?.kind === 'broll' && excludeTgt.idx === i) return;
    if (b.x != null && b.y != null) { const c = PV.computeBoxCss(wrap, b); boxes.push({ x: c.leftPct, y: c.topPct, w: c.widthPct, h: c.heightPct }); }
  });
  selectedCompositions.forEach((c, i) => {
    if (excludeTgt?.kind === 'comp' && excludeTgt.idx === i) return;
    if (c.type !== 'split-composition') { const css = PV.computeBoxCss(wrap, c); boxes.push({ x: css.leftPct, y: css.topPct, w: css.widthPct, h: css.heightPct }); }
  });
  selectedCards.forEach((c, i) => {
    if (excludeTgt?.kind === 'card' && excludeTgt.idx === i) return;
    if (c.x != null && c.y != null) { const css = PV.computeBoxCss(wrap, c, 1.0); boxes.push({ x: css.leftPct, y: css.topPct, w: css.widthPct, h: css.heightPct }); }
  });
  return boxes;
}

async function refreshFaceZone() {
  const vid = $('previewVideo');
  if (vid && !vid.hidden && vid.readyState >= 2) detectedFaceZone = await PV.detectVideoFaceZone(vid);
  syncGuidesAndOverlap();
}

function syncGuidesAndOverlap() {
  const fb = $('pvFaceBox'), cb = $('pvCapBox'), alertBox = $('brollOverlapAlert');
  const item = getPosItemByTarget(activePosTarget);
  const editing = !!item && !item.confirmed && currentStep === 6;
  const bl = $('pvBrollLayer'), cs = $('pvCardStage');
  bl?.classList.remove('is-overlap-warn'); cs?.classList.remove('is-overlap-warn');
  if (!item) { if (fb) fb.hidden = true; if (cb) cb.hidden = true; if (alertBox) alertBox.hidden = true; return; }
  const capY = Number($('posY')?.value || 74);
  if (fb) {
    fb.hidden = !editing;
    fb.style.left = detectedFaceZone.x.toFixed(1) + '%'; fb.style.top = detectedFaceZone.y.toFixed(1) + '%';
    fb.style.width = detectedFaceZone.w.toFixed(1) + '%'; fb.style.height = detectedFaceZone.h.toFixed(1) + '%';
  }
  if (cb) {
    cb.hidden = !editing;
    cb.style.left = '10%'; cb.style.top = Math.max(0, capY - 8) + '%'; cb.style.width = '80%'; cb.style.height = '16%';
  }
  const wrap = $('previewWrap');
  const intrinsic = activePosTarget.kind === 'card' ? 1.0 : (activePosTarget.kind === 'comp' && item.type === 'editorial-card' ? 0.52 : undefined);
  const boxCss = PV.computeBoxCss(wrap, item, intrinsic);
  const warn = PV.computeOverlapWarnings({ x: boxCss.leftPct, y: boxCss.topPct, w: boxCss.widthPct, h: boxCss.heightPct }, detectedFaceZone, capY);
  const showWarn = warn.hasOverlap && !item.ignoreOverlap;
  if (alertBox) { alertBox.hidden = !showWarn; if ($('brollOverlapText')) $('brollOverlapText').textContent = warn.message; }
  const stageEl = (activePosTarget.kind === 'broll' || (activePosTarget.kind === 'comp' && item.type === 'floating-media')) ? bl : cs;
  if (showWarn && stageEl && !stageEl.hidden) stageEl.classList.add('is-overlap-warn');
}

function updatePosStudioUI() {
  const studio = $('brollPosStudio');
  const item = getPosItemByTarget(activePosTarget);
  if (!studio || !item) { if (studio) studio.hidden = true; return; }
  studio.hidden = false;
  const kind = activePosTarget.kind;
  const label = kind === 'broll' ? `🎞️ B${activePosTarget.idx + 1} · ${item.name || 'B-roll'}` : (kind === 'card' ? `🖼️ C${activePosTarget.idx + 1} · ${item.name || 'Card'}` : `✨ Comp ${activePosTarget.idx + 1}`);
  if ($('posStudioLabel')) $('posStudioLabel').textContent = label;
  const badge = $('posStatusBadge');
  if (badge) { badge.textContent = item.confirmed ? 'Confirmado ✓' : 'Ajustando'; badge.classList.toggle('is-confirmed', !!item.confirmed); }
  const isAspectItem = kind === 'broll' || (kind === 'comp' && item.type === 'floating-media');
  if ($('posAspectRow')) $('posAspectRow').style.gridTemplateColumns = isAspectItem ? '' : '1fr';
  if ($('posAspectSel')?.parentElement) $('posAspectSel').parentElement.hidden = !isAspectItem;
  if ($('posRadiusRow')) $('posRadiusRow').hidden = (kind === 'card');
  const x = Math.round(Number(item.x ?? 8)), y = Math.round(Number(item.y ?? 10));
  const sc = Math.round(Number(item.scale ?? (kind === 'card' ? 34 : 42)));
  const mg = Math.round(Number(item.margin ?? 4)), rot = Math.round(Number(item.rotation ?? 0)), rad = Math.round(Number(item.radius ?? 22));
  if ($('posAspectSel')) $('posAspectSel').value = item.aspect || '16/9';
  if ($('posScaleRange')) { $('posScaleRange').value = sc; $('posScaleVal').textContent = sc + '%'; }
  if ($('posXRange')) { $('posXRange').value = x; $('posXVal').textContent = x + '%'; }
  if ($('posYRange')) { $('posYRange').value = y; $('posYVal2').textContent = y + '%'; }
  if ($('posMarginRange')) { $('posMarginRange').value = mg; $('posMarginVal').textContent = mg + '%'; }
  if ($('posRotRange')) { $('posRotRange').value = rot; $('posRotVal').textContent = rot + '°'; }
  if ($('posRadiusRange')) { $('posRadiusRange').value = rad; $('posRadiusVal').textContent = rad + 'px'; }
  $('posGrid9')?.querySelectorAll('button').forEach((btn) => {
    btn.classList.toggle('is-active', Math.abs(Number(btn.dataset.ax) - x) <= 6 && Math.abs(Number(btn.dataset.ay) - y) <= 6);
  });
}

function renderActiveTargetPreview(editable = false) {
  if (!activePosTarget) return;
  if (activePosTarget.kind === 'broll') previewBrollInStage(activePosTarget.idx, editable);
  else if (activePosTarget.kind === 'comp') previewCompositionInStage(activePosTarget.idx, editable);
  else if (activePosTarget.kind === 'card') previewCardInStage(activePosTarget.idx, editable);
}

function openPosStudio(kind, idx) {
  activePosTarget = { kind, idx };
  const item = getPosItemByTarget(activePosTarget);
  if (!item) return;
  if (kind === 'broll' && !['custom', 'top', 'bottom', 'full'].includes(item.layout)) item.layout = 'custom';
  else if (kind === 'broll' && ['top', 'bottom', 'full'].includes(item.layout)) item.layout = 'custom';
  if (kind === 'card') item.anim = 'custom';
  if (item.x == null || item.y == null) {
    const slot = PV.pickSmartSafeSlot($('previewWrap'), getAllPlacedBoxes(activePosTarget), detectedFaceZone, Number($('posY')?.value || 74), item);
    item.x = slot.x; item.y = slot.y;
  }
  item.scale = item.scale ?? (kind === 'card' ? 34 : 42);
  item.margin = item.margin ?? 4;
  item.rotation = item.rotation ?? 0;
  item.aspect = item.aspect || '16/9';
  item.radius = item.radius ?? 22;
  item.confirmed = false;
  updatePosStudioUI();
  renderActiveTargetPreview(true);
  if ($('brollList')) renderBrollList();
  if ($('cardList')) renderCardList();
  refreshFaceZone();
}

function previewCompositionInStage(idx, editable = false) {
  const c = selectedCompositions[idx]; if (!c) return;
  activePreviewCompIdx = idx; activePreviewBrollIdx = -1; activePreviewCardIdx = -1;
  PV.renderCompositionStage(c, stageRefs());
  const bl = $('pvBrollLayer'), cs = $('pvCardStage');
  const isFloat = c.type === 'floating-media';
  if (isFloat && bl && !bl.hidden) {
    bl.classList.toggle('is-editable', editable && !c.confirmed);
    const rh = bl.querySelector('.pv-resize-handle'); if (rh) rh.hidden = !(editable && !c.confirmed);
  } else if (cs && !cs.hidden) {
    cs.classList.toggle('is-editable', editable && !c.confirmed && c.type !== 'split-composition');
    if (editable && !c.confirmed && !cs.querySelector('.pv-resize-handle')) {
      const h = document.createElement('button'); h.type = 'button'; h.className = 'pv-resize-handle'; h.dataset.resize = 'card'; h.textContent = '⤡';
      cs.appendChild(h);
    }
  }
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
  syncGuidesAndOverlap();
}

function createDefaultComposition(type) {
  const slot = PV.pickSmartSafeSlot($('previewWrap'), getAllPlacedBoxes(null), detectedFaceZone, Number($('posY')?.value || 74), { scale: type === 'editorial-card' ? 74 : 42, aspect: '16/9', margin: 4 });
  const base = {
    type, start: '', end: '', title: '', subtitle: '', tag: '', labels: [], media: [],
    bg_color: '#FFFFFF', accent_color: '#F472B6', text_color: '#111827',
    x: slot.x, y: slot.y, scale: 42, aspect: '16/9', radius: 22, shadow: 55, rotation: 0, margin: 4, confirmed: false, ignoreOverlap: false,
    stack_count: 3, stack_gap: 14, orientation: 'vertical', split_ratio: 50, gap: 10, highlight_pane: 'a',
    anim_in: 'scale-in', anim_out: 'fade-out', anim_dur: 0.34, anim_intensity: 1.0,
  };
  if (type === 'editorial-card') { base.title = 'Ponto principal'; base.subtitle = 'Explicação clara ao espectador.'; base.tag = 'DESTAQUE'; base.scale = 74; base.x = 50; base.y = 18; base.anim_in = 'slide-up'; }
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
        ${!isSplit ? `<button type="button" class="media-preview-btn" data-act="pos">📍 Posicionar</button>` : ''}
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
    card.querySelector('[data-act="pos"]')?.addEventListener('click', () => openPosStudio('comp', idx));
    card.querySelector('[data-act="pv"]')?.addEventListener('click', () => previewCompositionInStage(idx));
    card.querySelector('[data-act="del"]')?.addEventListener('click', () => { selectedCompositions.splice(idx, 1); if (activePosTarget?.kind === 'comp' && activePosTarget.idx === idx) { activePosTarget = null; $('brollPosStudio').hidden = true; } clearMediaPreview(); renderCompList(); markDirtyAfterRender(); });
    card.querySelector('[data-act="up"]')?.addEventListener('click', () => { pendingCompUploadIdx = idx; $('compMediaInput')?.click(); });
    card.querySelectorAll('[data-k]').forEach((inp) => {
      const ev = (inp.tagName === 'SELECT' || inp.type === 'color') ? 'change' : 'input';
      inp.addEventListener(ev, () => {
        const k = inp.dataset.k;
        comp[k] = (inp.type === 'range' || inp.type === 'number') ? (inp.value === '' ? '' : Number(inp.value)) : inp.value;
        comp.confirmed = false;
        previewCompositionInStage(idx, activePosTarget?.kind === 'comp' && activePosTarget.idx === idx);
        if (activePosTarget?.kind === 'comp' && activePosTarget.idx === idx) updatePosStudioUI();
        markDirtyAfterRender();
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
    const row = document.createElement('div');
    const isEditing = activePosTarget?.kind === 'broll' && activePosTarget.idx === idx && !b.confirmed;
    row.className = 'media-item' + (isEditing ? ' is-editing' : '');
    const lbl = document.createElement('span'); lbl.className = 'media-name'; lbl.textContent = `🎞️ B${idx + 1} · ${b.name}`;
    if (b.layout === 'custom') {
      const stBadge = document.createElement('span');
      stBadge.className = 'media-pos-badge' + (b.confirmed ? '' : ' is-pending');
      stBadge.textContent = b.confirmed ? `✓ ${Math.round(b.x)}%,${Math.round(b.y)}%` : 'Ajuste';
      lbl.append(' ', stBadge);
    }
    const sel = document.createElement('select'); sel.className = 'media-sel';
    [['custom', 'Posição Manual'], ['auto', 'Automático'], ['top', 'Topo (c/ máscara)'], ['bottom', 'Baixo (c/ máscara)'], ['pip-rounded', 'Janela Canto'], ['center-frame', 'Quadro Central'], ['full', 'Tela cheia']].forEach(([v, t]) => {
      const o = document.createElement('option'); o.value = v; o.textContent = t; if (b.layout === v) o.selected = true; sel.append(o);
    });
    sel.addEventListener('change', () => {
      b.layout = sel.value;
      if (b.layout === 'custom') openPosStudio('broll', idx);
      else { b.confirmed = true; if (activePosTarget?.kind === 'broll' && activePosTarget.idx === idx && $('brollPosStudio')) $('brollPosStudio').hidden = true; previewBrollInStage(idx); renderBrollList(); renderSyncTimeline(); }
      markDirtyAfterRender();
    });
    const posBtn = document.createElement('button'); posBtn.type = 'button'; posBtn.className = 'media-preview-btn'; posBtn.textContent = '📍'; posBtn.title = 'Posicionar na tela';
    posBtn.addEventListener('click', () => openPosStudio('broll', idx));
    const pvBtn = document.createElement('button'); pvBtn.type = 'button'; pvBtn.className = 'media-preview-btn'; pvBtn.textContent = '👁️';
    pvBtn.addEventListener('click', () => previewBrollInStage(idx, false));
    const del = document.createElement('button'); del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => {
      selectedBrolls.splice(idx, 1);
      if (activePosTarget?.kind === 'broll' && activePosTarget.idx === idx) { activePosTarget = null; if ($('brollPosStudio')) $('brollPosStudio').hidden = true; }
      clearMediaPreview(); renderBrollList(); markDirtyAfterRender();
    });
    const times = document.createElement('div'); times.className = 'media-times';
    times.innerHTML = `<span>Início:</span><input type="number" step="0.5" min="0" class="media-time-in" value="${b.start ?? ''}" placeholder="Auto"><span>Fim:</span><input type="number" step="0.5" min="0" class="media-time-in" value="${b.end ?? ''}" placeholder="Auto">`;
    const [inS, inE] = times.querySelectorAll('input');
    inS.addEventListener('input', () => { b.start = inS.value === '' ? '' : Number(inS.value); markDirtyAfterRender(); });
    inE.addEventListener('input', () => { b.end = inE.value === '' ? '' : Number(inE.value); markDirtyAfterRender(); });
    row.append(lbl, posBtn, pvBtn, sel, del, times); list.append(row);
  });
}

function previewBrollInStage(idx, editable = false) {
  const b = selectedBrolls[idx]; if (!b) return;
  activePreviewBrollIdx = idx; activePreviewCompIdx = -1; activePreviewCardIdx = -1;
  const bl = $('pvBrollLayer'); if (!bl) return;
  const cs = $('pvCardStage'); if (cs) { cs.hidden = true; cs.replaceChildren(); }
  bl.hidden = false; bl.style.cssText = '';
  $('previewWrap')?.classList.toggle('split-top', b.layout === 'top');
  $('previewWrap')?.classList.toggle('split-bottom', b.layout === 'bottom');
  if (b.layout === 'custom' || (b.x != null && b.y != null && !['top', 'bottom', 'full', 'auto'].includes(b.layout))) {
    bl.dataset.layout = 'custom-floating';
    const box = PV.computeBoxCss($('previewWrap'), b);
    bl.style.left = box.leftPct.toFixed(2) + '%';
    bl.style.top = box.topPct.toFixed(2) + '%';
    bl.style.width = box.widthPct + '%';
    bl.style.aspectRatio = box.aspectCss;
    bl.style.borderRadius = (Number(b.radius ?? 22)) + 'px';
    bl.style.transform = Math.abs(box.rotDeg) > 0.25 ? `rotate(${box.rotDeg}deg)` : '';
    bl.style.boxShadow = '0 12px 28px rgba(0,0,0,0.65)';
  } else {
    bl.dataset.layout = b.layout || 'top';
  }
  const canEdit = editable && !b.confirmed && !['top', 'bottom', 'full'].includes(b.layout);
  bl.classList.toggle('is-editable', canEdit);
  const rh = bl.querySelector('.pv-resize-handle'); if (rh) rh.hidden = !canEdit;
  if (b.isImage) { $('pvBrollVid').hidden = true; $('pvBrollImg').src = b.previewUrl; $('pvBrollImg').hidden = false; }
  else { $('pvBrollImg').hidden = true; $('pvBrollVid').src = b.previewUrl; $('pvBrollVid').hidden = false; $('pvBrollVid').play?.().catch(() => {}); }
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
  syncGuidesAndOverlap();
}

function previewCardInStage(idx, editable = false) {
  const c = selectedCards[idx]; if (!c) return;
  activePreviewCardIdx = idx; activePreviewBrollIdx = -1; activePreviewCompIdx = -1;
  const bl = $('pvBrollLayer'); if (bl) bl.hidden = true;
  const cs = $('pvCardStage'); if (!cs) return;
  cs.hidden = false; cs.className = 'pv-card-stage'; cs.style.cssText = ''; cs.replaceChildren();
  const img = document.createElement('img'); img.src = c.url; img.alt = c.name || 'Card';
  cs.appendChild(img);
  if (c.x != null && c.y != null) {
    const ratio = (img.naturalWidth && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
    const box = PV.computeBoxCss($('previewWrap'), c, ratio);
    cs.style.left = box.leftPct.toFixed(2) + '%';
    cs.style.top = box.topPct.toFixed(2) + '%';
    cs.style.width = box.widthPct + '%';
    cs.style.transform = Math.abs(box.rotDeg) > 0.25 ? `rotate(${box.rotDeg}deg)` : '';
  } else {
    cs.dataset.anim = c.anim || 'side-right';
  }
  const canEdit = editable && !c.confirmed;
  cs.classList.toggle('is-editable', canEdit);
  if (canEdit) {
    const h = document.createElement('button'); h.type = 'button'; h.className = 'pv-resize-handle'; h.dataset.resize = 'card'; h.textContent = '⤡';
    cs.appendChild(h);
  }
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
  syncGuidesAndOverlap();
}

function renderCardList() {
  const list = $('cardList'); if (!list) return; list.replaceChildren();
  selectedCards.forEach((c, idx) => {
    const row = document.createElement('div');
    const isEditing = activePosTarget?.kind === 'card' && activePosTarget.idx === idx && !c.confirmed;
    row.className = 'media-item' + (isEditing ? ' is-editing' : '');
    const img = document.createElement('img'); img.className = 'media-thumb'; img.src = c.url; img.alt = c.name;
    const lbl = document.createElement('span'); lbl.className = 'media-name'; lbl.textContent = `C${idx + 1} · ${c.name}`;
    if (c.x != null) {
      const bdg = document.createElement('span'); bdg.className = 'media-pos-badge' + (c.confirmed ? '' : ' is-pending');
      bdg.textContent = c.confirmed ? `✓ ${Math.round(c.x)}%,${Math.round(c.y)}%` : 'Ajuste';
      lbl.append(' ', bdg);
    }
    const posBtn = document.createElement('button'); posBtn.type = 'button'; posBtn.className = 'media-preview-btn'; posBtn.textContent = '📍'; posBtn.title = 'Posicionar card';
    posBtn.addEventListener('click', () => openPosStudio('card', idx));
    const del = document.createElement('button'); del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => {
      selectedCards.splice(idx, 1);
      if (activePosTarget?.kind === 'card' && activePosTarget.idx === idx) { activePosTarget = null; if ($('brollPosStudio')) $('brollPosStudio').hidden = true; }
      clearMediaPreview(); renderCardList(); markDirtyAfterRender();
    });
    row.append(img, lbl, posBtn, del); list.append(row);
  });
}

$('brollFile')?.addEventListener('change', async (e) => {
  for (const f of [...(e.target.files || [])]) {
    try {
      const fd = new FormData(); fd.append('broll', f, f.name);
      const data = await safeJson(await fetch('/api/upload_broll', { method: 'POST', body: fd }));
      if (data.broll_id) {
        const slot = PV.pickSmartSafeSlot($('previewWrap'), getAllPlacedBoxes(null), detectedFaceZone, Number($('posY')?.value || 74), { scale: 42, aspect: '16/9', margin: 4 });
        const linkCap = (pendingCardBrollIdx >= 0 && currentCaptions[pendingCardBrollIdx]) ? currentCaptions[pendingCardBrollIdx] : null;
        selectedBrolls.push({
          id: data.broll_id, name: f.name, layout: 'custom',
          start: linkCap ? Number(Number(linkCap.s || 0).toFixed(1)) : '',
          end: linkCap ? Number(Number(linkCap.e || (Number(linkCap.s || 0) + 3)).toFixed(1)) : '',
          cardIdx: linkCap ? pendingCardBrollIdx : undefined,
          previewUrl: URL.createObjectURL(f), isImage: (f.type || '').startsWith('image/'),
          x: slot.x, y: slot.y, scale: 42, aspect: '16/9', rotation: 0, margin: 4, radius: 22, confirmed: false, ignoreOverlap: false,
        });
      }
    } catch {}
  }
  e.target.value = ''; renderBrollList();
  if (selectedBrolls.length) {
    if (pendingCardBrollIdx >= 0) goToStep(6);
    openPosStudio('broll', selectedBrolls.length - 1);
  }
  renderSyncTimeline();
});

$('cardFile')?.addEventListener('change', async (e) => {
  for (const f of [...(e.target.files || [])]) {
    try {
      const fd = new FormData(); fd.append('card', f, f.name); fd.append('remove_bg', '1');
      const data = await safeJson(await fetch('/api/upload_card', { method: 'POST', body: fd }));
      if (data.card_id) {
        const slot = PV.pickSmartSafeSlot($('previewWrap'), getAllPlacedBoxes(null), detectedFaceZone, Number($('posY')?.value || 74), { scale: 34, aspect: '1/1', margin: 4 });
        selectedCards.push({ id: data.card_id, name: f.name, url: data.url, anim: 'custom', start: '', end: '', x: slot.x, y: slot.y, scale: 34, rotation: 0, margin: 4, confirmed: false, ignoreOverlap: false });
      }
    } catch {}
  }
  e.target.value = ''; renderCardList();
  if (selectedCards.length) openPosStudio('card', selectedCards.length - 1);
});

/* Positioning Studio Controls + Interactive Drag/Resize */
(function initBrollPosStudio() {
  const applyChange = (fn) => {
    const item = getPosItemByTarget(activePosTarget); if (!item) return;
    fn(item);
    item.confirmed = false;
    updatePosStudioUI();
    renderActiveTargetPreview(true);
    if (activePosTarget.kind === 'comp') renderCompList();
    else if (activePosTarget.kind === 'broll') renderBrollList();
    else renderCardList();
    markDirtyAfterRender();
  };
  $('posGrid9')?.querySelectorAll('button').forEach((btn) => {
    btn.addEventListener('click', () => applyChange((it) => { it.x = Number(btn.dataset.ax); it.y = Number(btn.dataset.ay); }));
  });
  $('posAspectSel')?.addEventListener('change', () => applyChange((it) => { it.aspect = $('posAspectSel').value; }));
  $('posScaleRange')?.addEventListener('input', () => applyChange((it) => { it.scale = Number($('posScaleRange').value); }));
  $('posXRange')?.addEventListener('input', () => applyChange((it) => { it.x = Number($('posXRange').value); }));
  $('posYRange')?.addEventListener('input', () => applyChange((it) => { it.y = Number($('posYRange').value); }));
  $('posMarginRange')?.addEventListener('input', () => applyChange((it) => { it.margin = Number($('posMarginRange').value); }));
  $('posRotRange')?.addEventListener('input', () => applyChange((it) => { it.rotation = Number($('posRotRange').value); }));
  $('posRadiusRange')?.addEventListener('input', () => applyChange((it) => { it.radius = Number($('posRadiusRange').value); }));
  $('posRotResetBtn')?.addEventListener('click', () => applyChange((it) => { it.rotation = 0; }));
  $('posDetectFaceBtn')?.addEventListener('click', async () => { await refreshFaceZone(); flash(detectedFaceZone.detected ? 'Rosto detectado e protegido!' : 'Área de rosto padrão aplicada.'); });
  $('brollIgnoreWarnBtn')?.addEventListener('click', () => {
    const it = getPosItemByTarget(activePosTarget); if (!it) return;
    it.ignoreOverlap = true; syncGuidesAndOverlap();
  });
  $('posSmartSafeBtn')?.addEventListener('click', () => applyChange((it) => {
    it.ignoreOverlap = false;
    const slot = PV.pickSmartSafeSlot($('previewWrap'), getAllPlacedBoxes(activePosTarget), detectedFaceZone, Number($('posY')?.value || 74), it);
    it.x = slot.x; it.y = slot.y;
  }));
  $('confirmBrollPosBtn')?.addEventListener('click', () => {
    const it = getPosItemByTarget(activePosTarget); if (!it) return;
    it.confirmed = true;
    // Se veio de um card da Central de Transcrição, vincula ao card após confirmação
    if (pendingCardBrollIdx >= 0 && currentCaptions[pendingCardBrollIdx] && activePosTarget.kind === 'broll') {
      const cap = currentCaptions[pendingCardBrollIdx];
      it.cardIdx = pendingCardBrollIdx;
      if (it.start === '' || it.start == null) it.start = Number(cap.s || 0);
      if (it.end === '' || it.end == null) it.end = Number(cap.e || (Number(cap.s || 0) + 3.0));
      pendingCardBrollIdx = -1;
      renderCaptionEditor(currentCaptions);
    }
    updatePosStudioUI();
    renderActiveTargetPreview(false);
    renderBrollList(); renderCardList(); renderCompList();
    renderSyncTimeline();
    flash('Posição salva para este elemento!');
  });

  // Drag to move & corner handle to resize directly on previewWrap
  let dragMode = null, sx = 0, sy = 0, startX = 0, startY = 0, startSc = 42;
  const onDown = (e) => {
    const item = getPosItemByTarget(activePosTarget); if (!item || item.confirmed) return;
    const stageEl = e.target.closest('#pvBrollLayer.is-editable, #pvCardStage.is-editable');
    if (!stageEl) return;
    e.preventDefault(); e.stopPropagation();
    dragMode = e.target.closest('.pv-resize-handle') ? 'resize' : 'move';
    sx = e.clientX; sy = e.clientY;
    startX = Number(item.x ?? 8); startY = Number(item.y ?? 10); startSc = Number(item.scale ?? 42);
  };
  $('pvBrollLayer')?.addEventListener('pointerdown', onDown);
  $('pvCardStage')?.addEventListener('pointerdown', onDown);
  window.addEventListener('pointermove', (e) => {
    if (!dragMode) return;
    const wrap = $('previewWrap'), item = getPosItemByTarget(activePosTarget);
    if (!wrap || !item) return;
    const r = wrap.getBoundingClientRect();
    const dx = e.clientX - sx, dy = e.clientY - sy;
    if (dragMode === 'resize') {
      item.scale = Math.round(Math.max(18, Math.min(88, startSc + ((dx + dy * 0.5) / Math.max(120, r.width)) * 100)));
    } else {
      const box = PV.computeBoxCss(wrap, item);
      const spanX = Math.max(12, 100 - box.widthPct - 2 * box.marginPct);
      const spanY = Math.max(12, 100 - box.heightPct - 2 * box.marginPct);
      item.x = Math.round(Math.max(0, Math.min(100, startX + ((dx / Math.max(120, r.width)) * 100 / spanX) * 100)));
      item.y = Math.round(Math.max(0, Math.min(100, startY + ((dy / Math.max(160, r.height)) * 100 / spanY) * 100)));
    }
    item.confirmed = false;
    updatePosStudioUI();
    renderActiveTargetPreview(true);
    markDirtyAfterRender();
  });
  const endDrag = () => { if (dragMode) { dragMode = null; renderBrollList(); renderCardList(); } };
  window.addEventListener('pointerup', endDrag); window.addEventListener('pointercancel', endDrag);
})();

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
  if ($('stlPlayheadVal')) $('stlPlayheadVal').textContent = t.toFixed(1) + 's';
  if (currentCaptions.length) {
    const capIdx = currentCaptions.findIndex((c) => t >= Number(c.orig_s ?? c.s ?? 0) && t <= Number(c.orig_e ?? c.e ?? 999));
    if (capIdx >= 0 && activePreviewCaptionIdx !== capIdx) {
      activePreviewCaptionIdx = capIdx; syncOverlay(true); renderSyncTimeline();
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
  if (currentStep === 6 && (!activePosTarget || getPosItemByTarget(activePosTarget)?.confirmed)) {
    const matchWindow = (arr) => arr.findIndex((it) => {
      const s = parseFloat(it.start); if (isNaN(s)) return false;
      const e = isNaN(parseFloat(it.end)) ? s + 3.5 : parseFloat(it.end);
      return t >= s && t <= e;
    });
    const ci = matchWindow(selectedCompositions);
    const bi = matchWindow(selectedBrolls);
    const ki = matchWindow(selectedCards);
    if (ci >= 0) { if (activePreviewCompIdx !== ci) previewCompositionInStage(ci, false); }
    else if (bi >= 0) { if (activePreviewBrollIdx !== bi) previewBrollInStage(bi, false); }
    else if (ki >= 0) { if (activePreviewCardIdx !== ki) previewCardInStage(ki, false); }
    else if (
      (selectedCompositions.some((c) => c.start !== '') && activePreviewCompIdx >= 0) ||
      (selectedBrolls.some((b) => b.start !== '') && activePreviewBrollIdx >= 0) ||
      (selectedCards.some((k) => k.start !== '') && activePreviewCardIdx >= 0)
    ) clearMediaPreview();
  }
});

function probeLocalVideoMeta(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement('video');
    v.preload = 'metadata';
    v.muted = true;
    v.playsInline = true;
    v.src = url;
    const done = (dur = 0, thumbUrl = '') => {
      try { URL.revokeObjectURL(url); } catch {}
      resolve({ duration: dur, thumbUrl });
    };
    const timer = setTimeout(() => done(0, ''), 3500);
    v.onloadedmetadata = () => {
      const dur = Number(v.duration || 0);
      try {
        v.currentTime = Math.min(0.25, dur > 0 ? dur * 0.1 : 0);
      } catch {
        clearTimeout(timer); done(dur, '');
      }
    };
    v.onseeked = () => {
      clearTimeout(timer);
      try {
        const c = document.createElement('canvas');
        c.width = 96; c.height = 128;
        const ctx = c.getContext('2d');
        if (ctx && v.videoWidth && v.videoHeight) {
          ctx.drawImage(v, 0, 0, c.width, c.height);
          done(Number(v.duration || 0), c.toDataURL('image/jpeg', 0.65));
          return;
        }
      } catch {}
      done(Number(v.duration || 0), '');
    };
    v.onerror = () => { clearTimeout(timer); done(0, ''); };
  });
}

function renderVideoQueue() {
  const box = $('videoQueueBox'), list = $('videoQueueList'), ttl = $('videoQueueTitle');
  if (!box || !list) return;
  if (!selectedFiles.length) {
    box.hidden = true;
    list.replaceChildren();
    videoUnlocked = false;
    selectedFile = null;
    if ($('generateBtn')) $('generateBtn').disabled = true;
    if ($('uploadTitle')) $('uploadTitle').textContent = 'Escolher um ou mais vídeos (takes)';
    if ($('uploadSub')) $('uploadSub').textContent = 'Toque ou arraste seus vídeos (MP4, MOV, WebM)';
    document.querySelectorAll('#wizardStepper .ws-pill').forEach((pill) => {
      const ps = Number(pill.dataset.step);
      pill.disabled = ps > 1;
    });
    return;
  }
  box.hidden = false;
  if (ttl) ttl.textContent = `Vídeos na sequência (${selectedFiles.length})`;
  const totalMB = selectedFiles.reduce((acc, it) => acc + it.sizeMB, 0);
  if ($('uploadTitle')) {
    $('uploadTitle').textContent = selectedFiles.length === 1
      ? selectedFiles[0].name
      : `${selectedFiles.length} vídeos selecionados`;
  }
  if ($('uploadSub')) {
    $('uploadSub').textContent = `${totalMB.toFixed(1)} MB · Clique em ＋ Adicionar para incluir mais takes`;
  }
  list.replaceChildren();
  selectedFiles.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'vq-item';
    const ord = document.createElement('span'); ord.className = 'vq-order'; ord.textContent = String(idx + 1);
    const thumb = item.thumbUrl ? document.createElement('img') : document.createElement('div');
    thumb.className = 'vq-thumb';
    if (item.thumbUrl) { thumb.src = item.thumbUrl; thumb.alt = item.name; }
    else { thumb.style.display = 'grid'; thumb.style.placeItems = 'center'; thumb.textContent = '🎬'; }
    const meta = document.createElement('div'); meta.className = 'vq-meta';
    const nm = document.createElement('strong'); nm.textContent = item.name;
    const sub = document.createElement('small');
    sub.textContent = `${item.duration > 0 ? fmtMMSS(item.duration) + ' · ' : ''}${item.sizeMB.toFixed(1)} MB`;
    meta.append(nm, sub);
    const acts = document.createElement('div'); acts.className = 'vq-actions';
    const upBtn = document.createElement('button'); upBtn.type = 'button'; upBtn.className = 'vq-btn'; upBtn.textContent = '↑'; upBtn.title = 'Mover para cima';
    upBtn.disabled = (idx === 0);
    upBtn.addEventListener('click', () => {
      if (idx === 0) return;
      [selectedFiles[idx - 1], selectedFiles[idx]] = [selectedFiles[idx], selectedFiles[idx - 1]];
      syncPrimaryFilePreview(); renderVideoQueue();
    });
    const dnBtn = document.createElement('button'); dnBtn.type = 'button'; dnBtn.className = 'vq-btn'; dnBtn.textContent = '↓'; dnBtn.title = 'Mover para baixo';
    dnBtn.disabled = (idx === selectedFiles.length - 1);
    dnBtn.addEventListener('click', () => {
      if (idx >= selectedFiles.length - 1) return;
      [selectedFiles[idx], selectedFiles[idx + 1]] = [selectedFiles[idx + 1], selectedFiles[idx]];
      syncPrimaryFilePreview(); renderVideoQueue();
    });
    const delBtn = document.createElement('button'); delBtn.type = 'button'; delBtn.className = 'vq-btn is-del'; delBtn.textContent = '✕'; delBtn.title = 'Remover vídeo';
    delBtn.addEventListener('click', () => {
      selectedFiles.splice(idx, 1);
      syncPrimaryFilePreview(); renderVideoQueue();
    });
    acts.append(upBtn, dnBtn, delBtn);
    row.append(ord, thumb, meta, acts);
    list.append(row);
  });
}

function syncPrimaryFilePreview() {
  selectedFile = selectedFiles[0]?.file || null;
  if (!selectedFile) return;
  try {
    const vid = $('previewVideo');
    vid.src = URL.createObjectURL(selectedFile);
    vid.muted = true; vid.hidden = false; $('emptyStage').hidden = true;
    vid.addEventListener('loadedmetadata', () => {
      try {
        vid.currentTime = 0.001;
        vid.play().then(() => setTimeout(() => { vid.pause(); vid.muted = false; vid.currentTime = 0.001; refreshFaceZone(); }, 110)).catch(() => { vid.muted = false; });
      } catch {}
    }, { once: true });
    vid.load();
  } catch {}
}

async function handleVideoFilesSelected(fileList, append = false) {
  const arr = [...(fileList || [])];
  if (!arr.length) return;
  const isVideoFile = (f) => (f.type || '').startsWith('video/') || /\.(mp4|mov|webm|m4v|mkv|avi)$/i.test(f.name || '');
  const valid = arr.filter(isVideoFile);
  if (!valid.length) {
    $('errorMsg').textContent = 'Formato inválido: selecione apenas arquivos de vídeo (MP4, MOV, WebM).';
    $('errorMsg').hidden = false;
    return;
  }
  const tooBig = valid.find((f) => (f.size || 0) > 550 * 1024 * 1024);
  if (tooBig) {
    $('errorMsg').textContent = `O arquivo "${tooBig.name}" excede o limite de 550 MB.`;
    $('errorMsg').hidden = false;
    return;
  }
  $('errorMsg').hidden = true;
  if (!append) selectedFiles = [];

  for (const f of valid) {
    const meta = await probeLocalVideoMeta(f);
    selectedFiles.push({
      file: f,
      name: f.name || `video_${selectedFiles.length + 1}.mp4`,
      sizeMB: (f.size || 0) / (1024 * 1024),
      duration: meta.duration,
      thumbUrl: meta.thumbUrl,
    });
  }

  videoUnlocked = true; currentJobId = ''; cachedVideoBlob = null; currentCaptions = []; currentTakeRanges = [];
  flowStage = 'transcribe'; activePreviewCaptionIdx = -1; lastCineFiredIdx = -1; pendingCardBrollIdx = -1;
  clearMediaPreview();
  $('reviewCard').hidden = true;
  if ($('goExportBtn')) $('goExportBtn').disabled = true;
  if ($('syncTimelineBox')) $('syncTimelineBox').hidden = true;
  $('generateBtn').textContent = '1. Transcrever & Abrir Central de Edição →';
  $('liveOverlay').hidden = false; $('resultBox').hidden = true; $('generateBtn').disabled = false;

  syncPrimaryFilePreview();
  renderVideoQueue();
  document.querySelectorAll('#wizardStepper .ws-pill').forEach((pill) => {
    const ps = Number(pill.dataset.step);
    pill.disabled = ps > 1 && !videoUnlocked;
  });

  // Se selecionou apenas 1 vídeo do zero, avança direto para Etapa 2; se múltiplos ou adicionando, fica na Etapa 1 para organizar
  if (!append && selectedFiles.length === 1) {
    goToStep(2);
  }
}

$('videoFile')?.addEventListener('change', (e) => {
  const files = e.target.files;
  const app = appendVideoMode;
  appendVideoMode = false;
  handleVideoFilesSelected(files, app);
  e.target.value = '';
});
$('addMoreVideosBtn')?.addEventListener('click', () => { appendVideoMode = true; $('videoFile')?.click(); });
$('clearVideosBtn')?.addEventListener('click', () => { selectedFiles = []; currentTakeRanges = []; renderVideoQueue(); });
$('step1NextBtn')?.addEventListener('click', () => { if (selectedFiles.length) goToStep(2); });

(() => {
  const box = $('uploadBox');
  if (!box) return;
  ['dragenter', 'dragover'].forEach((ev) => box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.add('is-dragover'); }));
  ['dragleave', 'drop'].forEach((ev) => box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.remove('is-dragover'); }));
  box.addEventListener('drop', (e) => {
    const files = [...(e.dataTransfer?.files || [])];
    if (files.length) handleVideoFilesSelected(files, selectedFiles.length > 0);
  });
})();

function guessDefaultMainIdx(tokens) {
  let best = 0, bestLen = -1;
  tokens.forEach((t, i) => { const c = t.replace(/[^\p{L}\p{N}]/gu, '').length; if (c > bestLen) { bestLen = c; best = i; } });
  return best;
}

const _STOPWORDS_PT = new Set(['a', 'o', 'e', 'de', 'da', 'do', 'em', 'um', 'uma', 'para', 'com', 'que', 'se', 'no', 'na', 'os', 'as', 'por', 'mais', 'como', 'mas', 'foi', 'ao', 'ele', 'ela', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'você', 'isso', 'só']);

function analyzeCaptionsSmart(captions, autoApply = false) {
  const caps = (captions || []);
  let suggestedHighlights = 0, suggestedCines = 0, suggestedBrolls = 0;
  caps.forEach((cap, idx) => {
    const toks = (cap.text || '').replace(/[|\n]+/g, ' ').trim().split(/\s+/).filter(Boolean);
    const scored = toks.map((t, i) => {
      const clean = t.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
      const len = clean.length;
      const sc = (_STOPWORDS_PT.has(clean) || len <= 2) ? 0 : len + (/^\d+$/.test(clean) ? 6 : 0);
      return { i, sc };
    }).sort((a, b) => b.sc - a.sc);
    const topIndices = scored.filter((x) => x.sc >= 5).slice(0, toks.length >= 6 ? 2 : 1).map((x) => x.i).sort((a, b) => a - b);
    if (!topIndices.length && toks.length) topIndices.push(guessDefaultMainIdx(toks));
    const prevEnd = idx > 0 ? Number(caps[idx - 1].e || 0) : 0;
    const pauseGap = idx > 0 ? Math.max(0, Number(cap.s || 0) - prevEnd) : 0;
    const isStrongMoment = (idx % 4 === 1 && toks.length >= 3);
    const suggestBroll = (pauseGap >= 0.6 || toks.length >= 7) && (idx % 3 === 2);
    cap._analysis = {
      keyIndices: topIndices,
      suggestCine: isStrongMoment,
      suggestBroll,
      pauseGap: Number(pauseGap.toFixed(1)),
    };
    if (topIndices.length) suggestedHighlights++;
    if (isStrongMoment) suggestedCines++;
    if (suggestBroll) suggestedBrolls++;

    if (autoApply) {
      cap.main_indices = [...topIndices];
      cap.main_idx = topIndices[0] ?? 0;
      if (isStrongMoment && suggestedCines <= 3) {
        cap.cine_indices = [...topIndices];
      }
    }
  });
  return { total: caps.length, suggestedHighlights, suggestedCines, suggestedBrolls };
}

function fmtMMSS(sec) {
  const s = Math.max(0, Number(sec || 0));
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

function renderSyncTimeline() {
  const box = $('syncTimelineBox'), tracks = $('syncTimelineTracks');
  if (!box || !tracks) return;
  if (!currentCaptions.length) { box.hidden = true; return; }
  box.hidden = false;
  tracks.replaceChildren();
  const maxEnd = Math.max(
    1,
    ...currentCaptions.map((c) => Number(c.e || 0)),
    ...currentTakeRanges.map((t) => Number(t.e || 0)),
    ...selectedBrolls.map((b) => Number(b.end || 0)),
    Number($('previewVideo')?.duration || 0)
  );
  const pct = (v) => Math.max(0, Math.min(100, (Number(v || 0) / maxEnd) * 100));

  // Faixa 0: Vídeos / Takes (quando múltiplos vídeos)
  if (currentTakeRanges.length > 1) {
    const rTk = document.createElement('div'); rTk.className = 'stl-row';
    currentTakeRanges.forEach((tk, idx) => {
      const b = document.createElement('div'); b.className = 'stl-block is-take';
      const left = pct(tk.s), width = Math.max(4, pct(tk.e) - left);
      b.style.left = left.toFixed(2) + '%'; b.style.width = width.toFixed(2) + '%';
      b.textContent = `🎬 Take ${idx + 1}`;
      b.title = `${tk.filename} (${fmtMMSS(tk.s)}–${fmtMMSS(tk.e)})`;
      b.addEventListener('click', () => {
        const vid = $('previewVideo');
        if (vid) vid.currentTime = Number(tk.s || 0);
      });
      rTk.append(b);
    });
    tracks.append(rTk);
  }

  // Faixa 1: Blocos de Fala / Legenda
  const rCap = document.createElement('div'); rCap.className = 'stl-row';
  currentCaptions.forEach((cap, idx) => {
    if (cap.cut) return;
    const b = document.createElement('div');
    b.className = 'stl-block' + (activePreviewCaptionIdx === idx ? ' is-active' : '');
    const left = pct(cap.s), width = Math.max(3, pct(cap.e) - left);
    b.style.left = left.toFixed(2) + '%'; b.style.width = width.toFixed(2) + '%';
    b.textContent = `${idx + 1}. ${(cap.text || '').slice(0, 14)}`;
    b.title = `${fmtMMSS(cap.s)}–${fmtMMSS(cap.e)}: ${cap.text}`;
    b.addEventListener('click', () => focusCaptionCard(idx, true));
    rCap.append(b);
  });
  tracks.append(rCap);

  // Faixa 2: Efeitos Gráficos e Holofote
  const fxCaps = currentCaptions.map((c, idx) => ({ c, idx })).filter(({ c }) => (c.graphic_fx && c.graphic_fx !== 'none') || (c.cine_indices && c.cine_indices.length) || c.cine_block);
  if (fxCaps.length) {
    const rFx = document.createElement('div'); rFx.className = 'stl-row';
    fxCaps.forEach(({ c, idx }) => {
      const b = document.createElement('div'); b.className = 'stl-block is-fx';
      const left = pct(c.s), width = Math.max(3, pct(c.e) - left);
      b.style.left = left.toFixed(2) + '%'; b.style.width = width.toFixed(2) + '%';
      b.textContent = (c.cine_indices?.length || c.cine_block ? '🎬 ' : '') + (c.graphic_fx && c.graphic_fx !== 'none' ? c.graphic_fx : 'Holofote');
      b.addEventListener('click', () => focusCaptionCard(idx, true));
      rFx.append(b);
    });
    tracks.append(rFx);
  }

  // Faixa 3: B-rolls associados
  const activeBrolls = selectedBrolls.filter((b) => b.confirmed || b.start !== '');
  if (activeBrolls.length) {
    const rBr = document.createElement('div'); rBr.className = 'stl-row';
    activeBrolls.forEach((br) => {
      const bs = parseFloat(br.start); if (isNaN(bs)) return;
      const be = isNaN(parseFloat(br.end)) ? bs + 3.0 : parseFloat(br.end);
      const b = document.createElement('div'); b.className = 'stl-block is-broll';
      const left = pct(bs), width = Math.max(3, pct(be) - left);
      b.style.left = left.toFixed(2) + '%'; b.style.width = width.toFixed(2) + '%';
      b.textContent = `🎞️ ${br.name || 'B-roll'}`;
      b.addEventListener('click', () => {
        const vid = $('previewVideo');
        if (vid) { vid.currentTime = bs; }
        if (br.cardIdx != null) focusCaptionCard(br.cardIdx, false);
      });
      rBr.append(b);
    });
    tracks.append(rBr);
  }
}

function focusCaptionCard(idx, play = false) {
  if (idx < 0 || idx >= currentCaptions.length) return;
  activePreviewCaptionIdx = idx;
  const cap = currentCaptions[idx];
  syncOverlay(true);
  renderSyncTimeline();
  document.querySelectorAll('#captionEditorList .cap-edit-row').forEach((el, i) => el.classList.toggle('is-active-card', i === idx));
  const targetRow = document.querySelectorAll('#captionEditorList .cap-edit-row')[idx];
  targetRow?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  const vid = $('previewVideo');
  if (vid) {
    vid.muted = false;
    vid.currentTime = Math.max(0, Number(cap.orig_s ?? cap.s ?? 0));
    if (play) vid.play().catch(() => {});
  }
}

$('prevCardBtn')?.addEventListener('click', () => focusCaptionCard(Math.max(0, activePreviewCaptionIdx <= 0 ? 0 : activePreviewCaptionIdx - 1), false));
$('nextCardBtn')?.addEventListener('click', () => focusCaptionCard(Math.min(currentCaptions.length - 1, activePreviewCaptionIdx + 1), false));
$('applyAutoSuggestionsBtn')?.addEventListener('click', () => {
  analyzeCaptionsSmart(currentCaptions, true);
  if ($('cineModeSelect') && currentCaptions.some((c) => c.cine_indices?.length) && $('cineModeSelect').value === 'off') {
    $('cineModeSelect').value = 'manual';
  }
  renderCaptionEditor(currentCaptions);
  syncOverlay(true);
  markDirtyAfterRender();
});

function renderCaptionEditor(captions) {
  currentCaptions = (captions || []).map((c) => ({ ...c }));
  const stats = analyzeCaptionsSmart(currentCaptions, false);
  if ($('reviewAnalysisSummary')) {
    $('reviewAnalysisSummary').textContent = `${stats.total} blocos · ${stats.suggestedHighlights} destaques · ${stats.suggestedCines} sugestões de holofote`;
  }
  const list = $('captionEditorList'); list.replaceChildren();

  currentCaptions.forEach((cap, idx) => {
    const row = document.createElement('div');
    row.className = 'cap-edit-row' + (activePreviewCaptionIdx === idx ? ' is-active-card' : '') + (cap.cut ? ' is-cut' : '');

    const topBar = document.createElement('div'); topBar.className = 'cap-edit-top';
    const playBtn = document.createElement('button'); playBtn.type = 'button'; playBtn.className = 'cap-edit-play'; playBtn.textContent = '▶';
    playBtn.title = 'Reproduzir trecho';
    playBtn.addEventListener('click', () => focusCaptionCard(idx, true));

    const rewindBtn = document.createElement('button'); rewindBtn.type = 'button'; rewindBtn.className = 'mini-pill-btn'; rewindBtn.textContent = '⏮';
    rewindBtn.title = 'Voltar ao início do bloco';
    rewindBtn.addEventListener('click', () => focusCaptionCard(idx, false));

    const tm = document.createElement('span'); tm.className = 'cap-edit-time';
    tm.textContent = `${fmtMMSS(cap.s)}–${fmtMMSS(cap.e)}`;

    const inp = document.createElement('input'); inp.type = 'text'; inp.className = 'cap-edit-input'; inp.value = cap.text || '';

    const elToggleBtn = document.createElement('button'); elToggleBtn.type = 'button'; elToggleBtn.className = 'mini-pill-btn';
    elToggleBtn.textContent = '＋ Elementos';

    const cutBtn = document.createElement('button'); cutBtn.type = 'button'; cutBtn.className = 'cap-edit-cut'; cutBtn.textContent = cap.cut ? 'Voltar' : '✂️';
    cutBtn.addEventListener('click', () => {
      currentCaptions[idx].cut = !currentCaptions[idx].cut; row.classList.toggle('is-cut', !!currentCaptions[idx].cut);
      cutBtn.textContent = currentCaptions[idx].cut ? 'Voltar' : '✂️';
      renderSyncTimeline(); markDirtyAfterRender();
    });

    topBar.append(playBtn, rewindBtn, tm, inp, elToggleBtn, cutBtn);

    // Análise automática discreta
    const analysisBar = document.createElement('div'); analysisBar.className = 'cap-analysis-bar';
    if (cap._analysis?.suggestCine) {
      const tag = document.createElement('span'); tag.className = 'cap-analysis-tag'; tag.textContent = '💡 Sugestão: Holofote';
      analysisBar.append(tag);
    }
    if (cap._analysis?.suggestBroll) {
      const tag = document.createElement('span'); tag.className = 'cap-analysis-tag'; tag.textContent = '🖼️ Bom ponto p/ B-roll';
      analysisBar.append(tag);
    }

    const chipsBox = document.createElement('div'); chipsBox.className = 'cap-word-chips';
    const summaryBox = document.createElement('div'); summaryBox.className = 'cap-elements-summary';

    function renderChipsAndSummary() {
      const toks = (inp.value || '').replace(/[|\n]+/g, ' ').trim().split(/\s+/).filter(Boolean);
      chipsBox.replaceChildren(); summaryBox.replaceChildren();
      if (!toks.length) return;
      if (!Array.isArray(currentCaptions[idx].main_indices) || !currentCaptions[idx].main_indices.length) {
        const defI = currentCaptions[idx].main_idx ?? guessDefaultMainIdx(toks);
        currentCaptions[idx].main_indices = [defI]; currentCaptions[idx].main_idx = defI;
      }
      const mSet = new Set(currentCaptions[idx].main_indices);
      const fxSet = new Set(currentCaptions[idx].fx_indices || []);
      const cSet = new Set(currentCaptions[idx].cine_indices || []);

      toks.forEach((tok, wIdx) => {
        const chip = document.createElement('button'); chip.type = 'button';
        chip.className = 'cap-word-chip' + (mSet.has(wIdx) ? ' is-main' : '') + (fxSet.has(wIdx) ? ' is-fx' : '') + (cSet.has(wIdx) ? ' is-cine' : '');
        chip.textContent = tok;
        chip.addEventListener('click', () => {
          const curSet = new Set(currentCaptions[idx].main_indices || []);
          if (curSet.has(wIdx) && curSet.size > 1) curSet.delete(wIdx); else curSet.add(wIdx);
          currentCaptions[idx].main_indices = [...curSet].sort((a, b) => a - b);
          currentCaptions[idx].main_idx = currentCaptions[idx].main_indices[0];
          activePreviewCaptionIdx = idx; renderChipsAndSummary(); syncOverlay(true); markDirtyAfterRender();
        });
        chipsBox.append(chip);
      });

      const cineBtn = document.createElement('button'); cineBtn.type = 'button';
      cineBtn.className = 'cap-chip-cine' + ((cSet.size || currentCaptions[idx].cine_block) ? ' is-on' : '');
      cineBtn.textContent = (cSet.size || currentCaptions[idx].cine_block) ? '🎬 Holofote ON' : '🎬 Holofote';
      cineBtn.addEventListener('click', () => {
        if (cSet.size || currentCaptions[idx].cine_block) {
          currentCaptions[idx].cine_indices = []; currentCaptions[idx].cine_block = false;
        } else {
          currentCaptions[idx].cine_indices = [...(currentCaptions[idx].main_indices || [0])];
          if ($('cineModeSelect') && $('cineModeSelect').value === 'off') $('cineModeSelect').value = 'manual';
        }
        activePreviewCaptionIdx = idx; renderChipsAndSummary(); renderSyncTimeline();
        syncOverlay(false, false, !!(currentCaptions[idx].cine_indices?.length || currentCaptions[idx].cine_block));
        markDirtyAfterRender();
      });
      chipsBox.append(cineBtn);

      // Resumo de elementos adicionados no card
      const addSummaryChip = (label, onDel) => {
        const sc = document.createElement('span'); sc.className = 'cap-el-chip';
        sc.textContent = label + ' ';
        const x = document.createElement('button'); x.type = 'button'; x.textContent = '✕';
        x.addEventListener('click', onDel);
        sc.append(x); summaryBox.append(sc);
      };
      if (currentCaptions[idx].style_id) {
        addSummaryChip(`Legenda: ${currentCaptions[idx].style_id}`, () => { delete currentCaptions[idx].style_id; renderChipsAndSummary(); markDirtyAfterRender(); });
      }
      if (currentCaptions[idx].graphic_fx && currentCaptions[idx].graphic_fx !== 'none') {
        const fxWords = (currentCaptions[idx].fx_indices?.length ? currentCaptions[idx].fx_indices : currentCaptions[idx].main_indices).map((wi) => toks[wi]).filter(Boolean).join(' ');
        addSummaryChip(`Efeito: ${currentCaptions[idx].graphic_fx}${fxWords ? ' em "' + fxWords + '"' : ''}`, () => {
          delete currentCaptions[idx].graphic_fx; delete currentCaptions[idx].fx_indices;
          renderChipsAndSummary(); renderSyncTimeline(); markDirtyAfterRender();
        });
      }
      if (currentCaptions[idx].cine_indices?.length || currentCaptions[idx].cine_block) {
        addSummaryChip(currentCaptions[idx].cine_block ? '🎬 Holofote (Bloco)' : '🎬 Holofote (Seleção)', () => {
          currentCaptions[idx].cine_indices = []; currentCaptions[idx].cine_block = false;
          renderChipsAndSummary(); renderSyncTimeline(); markDirtyAfterRender();
        });
      }
      selectedBrolls.forEach((br, bi) => {
        if (br.cardIdx === idx && br.confirmed) {
          addSummaryChip(`🎞️ ${br.name} (${fmtMMSS(br.start)}–${fmtMMSS(br.end)})`, () => {
            selectedBrolls.splice(bi, 1); renderBrollList(); renderChipsAndSummary(); renderSyncTimeline(); markDirtyAfterRender();
          });
        }
      });
    }
    renderChipsAndSummary();

    // Painel expansível "ADICIONAR ELEMENTOS" dentro do card
    const elPanel = document.createElement('div'); elPanel.className = 'cap-add-elements-box'; elPanel.hidden = true;
    elPanel.innerHTML = `
      <div class="cap-el-tabs">
        <button type="button" class="cap-el-tab is-active" data-tab="cap">💬 Legenda</button>
        <button type="button" class="cap-el-tab" data-tab="fx">✏️ Efeitos</button>
        <button type="button" class="cap-el-tab" data-tab="broll">🎞️ B-roll</button>
      </div>
      <div class="cap-el-pane" data-pane="cap">
        <div class="row-2">
          <label class="field"><span>Modelo do bloco</span>
            <select data-k="style_id">
              <option value="">Herdar global</option>
              <option value="classic">Impacto Bold</option>
              <option value="editorial-serif">Editorial Serif</option>
              <option value="big-word">Big Word</option>
              <option value="highlight-words">Highlight Words</option>
              <option value="pink-highlight">Pink Highlight</option>
              <option value="clean-dynamic">Clean Dynamic</option>
            </select>
          </label>
          <label class="field"><span>Cor destaque</span><input type="color" data-k="accent_color" value="${cap.accent_color || ($('accentColor')?.value || '#22C55E')}"></label>
        </div>
      </div>
      <div class="cap-el-pane" data-pane="fx" hidden>
        <div class="row-2">
          <label class="field"><span>Efeito gráfico</span>
            <select data-k="graphic_fx">
              <option value="">Padrão global</option>
              <option value="none">Nenhum</option>
              <option value="underline">Sublinhado animado</option>
              <option value="underline-double">Sublinhado duplo</option>
              <option value="strike">Riscado horizontal</option>
              <option value="strike-diag">Riscado diagonal</option>
              <option value="circle">Círculo completo</option>
              <option value="circle-open">Círculo incompleto</option>
              <option value="hand-circle">Círculo à mão</option>
              <option value="hand-underline">Sublinhado manual</option>
              <option value="hand-mark">Grifo pincel</option>
              <option value="arrow-curved">Seta curva</option>
              <option value="arrow-straight">Seta reta</option>
              <option value="arrow-angled">Seta angular</option>
            </select>
          </label>
          <label class="field"><span>Cor do efeito</span><input type="color" data-k="fx_color" value="${cap.gfx_cfg?.color || ($('gfxColor')?.value || '#FACC15')}"></label>
        </div>
        <div class="row-2">
          <button type="button" class="mini-pill-btn" data-act="bind-fx">🔗 Vincular às palavras selecionadas</button>
          <button type="button" class="mini-pill-btn" data-act="cine-block">🎬 Holofote no bloco todo</button>
        </div>
      </div>
      <div class="cap-el-pane" data-pane="broll" hidden>
        <p class="step-hint">Adicione imagem ou vídeo exatamente entre <b>${fmtMMSS(cap.s)}</b> e <b>${fmtMMSS(cap.e)}</b>. Só entra na composição após confirmar.</p>
        <button type="button" class="primary-btn" data-act="add-broll" style="padding:9px;font-size:12px">＋ Escolher mídia &amp; posicionar B-roll</button>
      </div>
    `;

    elPanel.querySelectorAll('.cap-el-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        elPanel.querySelectorAll('.cap-el-tab').forEach((t) => t.classList.remove('is-active'));
        tab.classList.add('is-active');
        elPanel.querySelectorAll('.cap-el-pane').forEach((p) => { p.hidden = (p.dataset.pane !== tab.dataset.tab); });
      });
    });
    const selStyle = elPanel.querySelector('[data-k="style_id"]');
    if (selStyle) { selStyle.value = cap.style_id || ''; selStyle.addEventListener('change', () => { currentCaptions[idx].style_id = selStyle.value || ''; renderChipsAndSummary(); markDirtyAfterRender(); }); }
    const selAcc = elPanel.querySelector('[data-k="accent_color"]');
    if (selAcc) selAcc.addEventListener('change', () => { currentCaptions[idx].accent_color = selAcc.value; markDirtyAfterRender(); });
    const selFx = elPanel.querySelector('[data-k="graphic_fx"]');
    if (selFx) {
      selFx.value = cap.graphic_fx || '';
      selFx.addEventListener('change', () => {
        currentCaptions[idx].graphic_fx = selFx.value || '';
        if (!currentCaptions[idx].fx_indices?.length) currentCaptions[idx].fx_indices = [...(currentCaptions[idx].main_indices || [0])];
        renderChipsAndSummary(); renderSyncTimeline(); markDirtyAfterRender();
      });
    }
    const selFxCol = elPanel.querySelector('[data-k="fx_color"]');
    if (selFxCol) selFxCol.addEventListener('change', () => { currentCaptions[idx].gfx_cfg = { ...(currentCaptions[idx].gfx_cfg || {}), color: selFxCol.value }; markDirtyAfterRender(); });
    elPanel.querySelector('[data-act="bind-fx"]')?.addEventListener('click', () => {
      currentCaptions[idx].fx_indices = [...(currentCaptions[idx].main_indices || [0])];
      if (!currentCaptions[idx].graphic_fx) currentCaptions[idx].graphic_fx = selFx?.value || 'underline';
      renderChipsAndSummary(); renderSyncTimeline(); markDirtyAfterRender();
    });
    elPanel.querySelector('[data-act="cine-block"]')?.addEventListener('click', () => {
      currentCaptions[idx].cine_block = !currentCaptions[idx].cine_block;
      if ($('cineModeSelect') && $('cineModeSelect').value === 'off') $('cineModeSelect').value = 'manual';
      renderChipsAndSummary(); renderSyncTimeline(); markDirtyAfterRender();
    });
    elPanel.querySelector('[data-act="add-broll"]')?.addEventListener('click', () => {
      pendingCardBrollIdx = idx;
      $('brollFile')?.click();
    });

    elToggleBtn.addEventListener('click', () => {
      elPanel.hidden = !elPanel.hidden;
      elToggleBtn.textContent = elPanel.hidden ? '＋ Elementos' : '− Fechar';
      focusCaptionCard(idx, false);
    });

    inp.addEventListener('focus', () => focusCaptionCard(idx, false));
    inp.addEventListener('input', () => { currentCaptions[idx].text = inp.value; activePreviewCaptionIdx = idx; renderChipsAndSummary(); syncOverlay(false); renderSyncTimeline(); markDirtyAfterRender(); });

    row.append(topBar, analysisBar, chipsBox, summaryBox, elPanel);
    list.append(row);
  });
  renderSyncTimeline();
}

async function safeJson(res) {
  const txt = await res.text();
  try { return JSON.parse(txt); } catch { throw new Error(`Servidor ocupado (HTTP ${res.status}).`); }
}

function uploadWithProgress(filesOrFile) {
  const list = Array.isArray(filesOrFile) ? filesOrFile.map((x) => x.file || x) : [filesOrFile];
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open('POST', '/api/upload', true);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.min(25, Math.max(5, Math.round((e.loaded / e.total) * 25)));
        $('progressText').textContent = list.length > 1
          ? `Enviando ${list.length} vídeos… (${Math.round((e.loaded / e.total) * 100)}%)`
          : `Enviando vídeo… (${Math.round((e.loaded / e.total) * 100)}%)`;
        $('progressPct').textContent = pct + '%'; $('progressFill').style.width = pct + '%';
      }
    };
    xhr.onload = () => {
      try { const d = JSON.parse(xhr.responseText || '{}'); if (xhr.status >= 200 && xhr.status < 300 && !d.error) resolve(d); else reject(new Error(d.error || 'Erro no upload.')); }
      catch { reject(new Error(`Resposta inválida (${xhr.status}).`)); }
    };
    xhr.onerror = () => reject(new Error('Falha de rede.'));
    const fd = new FormData();
    list.forEach((file, idx) => fd.append('video', file, file.name || `video_${idx + 1}.mp4`));
    xhr.send(fd);
  });
}

function buildRenderPayload() {
  const cCfg = readCineConfig();
  return {
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
    caption_lines: selectedLines, zoom: false, studio_audio: $('studioAudioToggle').checked,
    color_grade: !!$('colorGradeToggle')?.checked,
    compositions: selectedCompositions.filter((c) => c.confirmed || c.type === 'split-composition').map((c) => ({ ...c, media: (c.media || []).map((m) => ({ id: m.id })) })),
    brolls: selectedBrolls.filter((b) => b.confirmed).map((b) => ({
      id: b.id, layout: b.layout, start: b.start, end: b.end,
      x: b.x, y: b.y, scale: b.scale, aspect: b.aspect, rotation: b.rotation, margin: b.margin, radius: b.radius,
    })),
    cards: selectedCards.filter((c) => c.confirmed).map((c) => ({
      id: c.id, anim: c.anim, start: c.start, end: c.end,
      x: c.x, y: c.y, scale: c.scale, rotation: c.rotation, margin: c.margin,
    })),
    resolution: selectedResolution,
  };
}

async function pollRenderCompletion() {
  while (true) {
    await new Promise((r) => setTimeout(r, 1400));
    const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
    $('progressText').textContent = st.message || 'Renderizando…'; $('progressPct').textContent = (st.progress || 0) + '%'; $('progressFill').style.width = (st.progress || 0) + '%';
    if (st.status === 'done') {
      clearMediaPreview(); lastVideoUrl = st.video_url; cachedVideoBlob = null; cachedShareFile = null;
      if ($('previewCard')) $('previewCard').hidden = false;
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
}

async function runOneClickPipeline(mode) {
  if (!selectedFile) return;
  $('errorMsg').hidden = true; $('resultBox').hidden = true; $('reviewCard').hidden = true;
  $('progressBox').hidden = false; $('progressBox').scrollIntoView({ behavior: 'smooth', block: 'center' });
  try {
    if (mode === 'auto') {
      selectedStyle = 'highlight-words';
      selectedLines = 3;
      if ($('accentColor')) $('accentColor').value = '#FACC15';
      if ($('customColorToggle')) $('customColorToggle').checked = true;
      if ($('cineModeSelect')) $('cineModeSelect').value = 'auto';
      syncOverlay(true);
    } else if (mode === 'quick') {
      selectedLines = 2;
      syncOverlay(true);
    }
    $('progressText').textContent = mode === 'auto' ? '🤖 Modo Automático: enviando vídeo…' : '⚡ Modo Rápido: enviando vídeo…';
    $('progressPct').textContent = '5%'; $('progressFill').style.width = '5%';
    const up = await uploadWithProgress(selectedFiles.length ? selectedFiles : [selectedFile]); currentJobId = up.job_id;
    currentTakeRanges = up.take_ranges || [];
    if (up.source_url && selectedFiles.length > 1 && $('previewVideo')) {
      $('previewVideo').src = up.source_url; $('previewVideo').load();
    }
    const tr = await safeJson(await fetch('/api/transcribe', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: currentJobId, cuts: $('cutsToggle')?.checked ?? true, rhythm: selectedRhythm || 'natural' }),
    }));
    if (tr.error) throw new Error(tr.error);
    while (true) {
      await new Promise((r) => setTimeout(r, 1200));
      const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
      $('progressText').textContent = st.message || 'Analisando falas…'; $('progressPct').textContent = (st.progress || 0) + '%'; $('progressFill').style.width = (st.progress || 0) + '%';
      if (st.status === 'review') {
        currentCaptions = (st.captions || []).map((c) => ({ ...c }));
        analyzeCaptionsSmart(currentCaptions, true);
        break;
      }
      if (st.status === 'error') throw new Error(st.message || 'Erro na transcrição.');
    }
    $('progressText').textContent = mode === 'auto' ? '🤖 Aplicando edição automática…' : '⚡ Gerando vídeo rápido…';
    const ren = await safeJson(await fetch('/api/render', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildRenderPayload()),
    }));
    if (ren.error) throw new Error(ren.error);
    await pollRenderCompletion();
  } catch (err) {
    $('progressBox').hidden = true; $('errorMsg').textContent = err?.message || 'Falha no processamento.'; $('errorMsg').hidden = false;
  }
}

$('autoModeBtn')?.addEventListener('click', () => runOneClickPipeline('auto'));
$('quickModeBtn')?.addEventListener('click', () => runOneClickPipeline('quick'));

$('generateBtn').addEventListener('click', async () => {
  if (!selectedFile) return;
  $('generateBtn').disabled = true; $('errorMsg').hidden = true; $('resultBox').hidden = true;
  $('progressBox').hidden = false; $('progressBox').scrollIntoView({ behavior: 'smooth', block: 'center' });
  try {
    if (flowStage === 'transcribe') {
      $('progressText').textContent = 'Enviando vídeo…'; $('progressPct').textContent = '5%'; $('progressFill').style.width = '5%';
      const up = await uploadWithProgress(selectedFiles.length ? selectedFiles : [selectedFile]); currentJobId = up.job_id;
      currentTakeRanges = up.take_ranges || [];
      if (up.source_url && selectedFiles.length > 1 && $('previewVideo')) {
        $('previewVideo').src = up.source_url; $('previewVideo').load();
      }
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
          if ($('goExportBtn')) $('goExportBtn').disabled = false;
          goToStep(5);
          $('reviewCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
          flowStage = 'render'; $('generateBtn').textContent = '2. Gerar Vídeo Pronto →'; $('generateBtn').disabled = false;
          setStickyVisible(true); return;
        }
        if (st.status === 'error') throw new Error(st.message || 'Erro na transcrição.');
      }
    }

    const ren = await safeJson(await fetch('/api/render', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildRenderPayload()),
    }));
    if (ren.error) throw new Error(ren.error);
    await pollRenderCompletion();
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
