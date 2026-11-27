if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
let selectedFile = null;
let selectedStyle = 'classic';
let selectedLines = 3;
let selectedHookStyle = 'pill-white';
let selectedHookY = 16;
let selectedRhythm = 'natural';
let selectedResolution = '1080p';
let selectedBrolls = []; // [{ id, name, layout }]
let selectedCards = [];  // [{ id, name, url, anim }]
let deferredPrompt = null;
let lastVideoUrl = '';
let cachedVideoBlob = null;
let currentJobId = '';
let currentCaptions = [];
let flowStage = 'transcribe'; // 'transcribe' -> 'render'
let maxExportRes = '1080p';

window.getEuEditoJobId = () => currentJobId;
window.getEuEditoCaptions = () => currentCaptions;
window.onMotionLayersChanged = () => markDirtyAfterRender();

function markDirtyAfterRender() {
  if (flowStage === 'render' && $('resultBox') && !$('resultBox').hidden) {
    $('generateBtn').textContent = '🎨 Gerar novamente com estes ajustes →';
    setStickyVisible(true);
  }
}

async function getVideoBlob() {
  if (cachedVideoBlob) return cachedVideoBlob;
  if (!lastVideoUrl) throw new Error('Vídeo indisponível.');
  const res = await fetch(lastVideoUrl + '?dl=1');
  if (!res.ok) throw new Error('Falha ao baixar vídeo.');
  cachedVideoBlob = await res.blob();
  return cachedVideoBlob;
}

function triggerBlobDownload(blob, filename) {
  const objUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objUrl;
  a.download = filename;
  a.rel = 'noopener';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    a.remove();
    URL.revokeObjectURL(objUrl);
  }, 15000);
}

function setStickyVisible(vis) {
  const cta = document.querySelector('.sticky-cta');
  if (cta) cta.hidden = !vis;
}

function updateResTagDisplay() {
  let label = selectedResolution === '4k' ? '4K UHD' : selectedResolution === '1080p' ? '1080p HD' : 'Original';
  if (maxExportRes === '720p' && (selectedResolution === '1080p' || selectedResolution === '4k')) {
    label = '720p HD';
  }
  $('resTag').textContent = label;
}

fetch('/api/hardware').then((r) => r.json()).then((hw) => {
  if (hw && hw.max_export_res === '720p') {
    maxExportRes = '720p';
    const b1080 = $('resGrid')?.querySelector('[data-res="1080p"]');
    if (b1080) {
      b1080.querySelector('strong').textContent = '720p HD';
      b1080.querySelector('small').textContent = 'Nuvem rápida';
    }
    const b4k = $('resGrid')?.querySelector('[data-res="4k"]');
    if (b4k) b4k.hidden = true;
    updateResTagDisplay();
  }
}).catch(() => {});

const EXAMPLES = {
  'classic': '<small>só que eu</small><strong>FARIA DIFERENTE</strong><small>hoje</small>',
  'model-07': '<small>disputar a</small><strong>ATENÇÃO</strong><small>do público</small>',
  'clean-12': '<small>ritmo dinâmico</small><strong>EM MOVIMENTO</strong><small>suave</small>',
  'clean-13': '<small>deslize lateral</small><strong>POR CURIOSIDADE</strong>',
  'clean-14': '<small>Você</small><em>comemorou</em>',
  'clean-9': '<small>leitura limpa e</small><strong>fluida</strong><small>no vídeo</small>',
  'clean-10': '<small>se eu fosse</small><strong>começar</strong><small>agora</small>',
  'clean-11': '<small>elegância e</small><strong>sofisticação</strong><small>em cada fala</small>',
  'clean-15': '<small>uma nova forma de</small><strong>imaginar</strong>',
  'clean-lavish': '<small>Essa</small><strong>CAMPANHA</strong><small>ela tem</small>',
  'clean': '<small>composição pura</small><strong>seguidores</strong><small>ativos</small>'
};

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  $('installBtn').hidden = false;
});
$('installBtn').addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  $('installBtn').hidden = true;
});

const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
if (isIos && !isStandalone) {
  $('iosHint').hidden = false;
  $('closeIosHint').addEventListener('click', () => { $('iosHint').hidden = true; });
}

function animateOverlay(style) {
  const ov = $('liveOverlay');
  if (!ov || typeof ov.animate !== 'function') return;
  const parts = [...ov.querySelectorAll('small, strong, em')];
  parts.forEach((node, idx) => {
    node.getAnimations?.().forEach((a) => a.cancel());
    const isMain = node.tagName === 'STRONG' || node.tagName === 'EM';
    const delay = idx * 55;
    let frames = [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'translateY(0)' }];
    let dur = 240;
    if (style === 'clean-14' || style === 'clean-12' || style === 'model-07') {
      frames = isMain
        ? [{ opacity: 0, transform: 'scale(.76)' }, { opacity: 1, transform: 'scale(1.05)', offset: 0.72 }, { opacity: 1, transform: 'scale(1)' }]
        : [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }];
      dur = 360;
    } else if (style === 'clean-13' || style === 'clean' || style === 'clean-lavish') {
      frames = [{ opacity: 0, transform: 'translateX(16px)' }, { opacity: 1, transform: 'translateX(0)' }];
    } else if (style === 'clean-9') {
      frames = [{ opacity: 0, transform: 'translateY(-8px)', filter: 'blur(3px)' }, { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' }];
    } else if (style === 'clean-11') {
      frames = [{ opacity: 0 }, { opacity: 1 }];
      dur = 170;
    }
    try { node.animate(frames, { duration: dur, delay, fill: 'both', easing: 'cubic-bezier(.16,1,.3,1)' }); } catch {}
  });
}

function syncOverlay(animate = false) {
  const ov = $('liveOverlay');
  const isClean10 = (selectedStyle === 'clean-10');
  const lineMode = isClean10 ? 1 : selectedLines;
  $('linesGrid')?.querySelectorAll('.res-pill').forEach((b) => {
    const l = Number(b.dataset.lines || 3);
    b.disabled = isClean10 && l !== 1;
    b.classList.toggle('is-active', l === lineMode);
  });
  const modeCls = lineMode === 1 ? ' is-one-line' : (lineMode === 2 ? ' is-two-line' : '');
  ov.className = 'live-overlay style-' + selectedStyle + modeCls;
  ov.innerHTML = EXAMPLES[selectedStyle] || EXAMPLES.classic;
  if (lineMode === 2 && ov.children.length === 3) {
    // Strictly 2 clean rows: NEVER mix highlight with a loose word on the same row
    ov.children[2].remove();
  }
  ov.style.top = $('posY').value + '%';
  const sc = Number($('capScale')?.value || 100);
  ov.style.setProperty('--cap-scale', (sc / 100).toFixed(2));
  ov.style.removeProperty('--cap-fit');
  if ($('capScaleVal')) $('capScaleVal').textContent = sc + '%';
  const frame = $('previewWrap');
  if (frame && frame.clientWidth) {
    const maxW = frame.clientWidth * 0.90;
    const natW = ov.scrollWidth;
    if (natW > maxW && natW > 0) {
      ov.style.setProperty('--cap-fit', Math.max(0.54, maxW / natW).toFixed(3));
    }
  }
  const fontChoice = $('fontSelect')?.value || '';
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
  if (fontChoice && FONT_CSS_MAP[fontChoice]) {
    const [ff, fst, fwt] = FONT_CSS_MAP[fontChoice];
    ov.classList.add('has-custom-font');
    ov.style.setProperty('--main-font', ff);
    ov.style.setProperty('--main-style', fst);
    ov.style.setProperty('--main-weight', fwt);
  } else {
    ov.classList.remove('has-custom-font');
    ov.style.removeProperty('--main-font');
    ov.style.removeProperty('--main-style');
    ov.style.removeProperty('--main-weight');
  }
  const smallFontChoice = $('smallFontSelect')?.value || '';
  if (smallFontChoice && FONT_CSS_MAP[smallFontChoice]) {
    const [sff, sfst, swt] = FONT_CSS_MAP[smallFontChoice];
    ov.classList.add('has-custom-small-font');
    ov.style.setProperty('--small-font', sff);
    ov.style.setProperty('--small-style', sfst);
    ov.style.setProperty('--small-weight', swt);
  } else {
    ov.classList.remove('has-custom-small-font');
    ov.style.removeProperty('--small-font');
    ov.style.removeProperty('--small-style');
    ov.style.removeProperty('--small-weight');
  }
  if ($('customColorToggle')?.checked) {
    ov.style.setProperty('--accent', $('accentColor').value);
    $('hookOverlay')?.style.setProperty('--accent', $('accentColor').value);
  } else {
    ov.style.removeProperty('--accent');
    $('hookOverlay')?.style.removeProperty('--accent');
  }
  $('posYVal').textContent = $('posY').value + '%';
  if (animate) animateOverlay(selectedStyle);
}

$('linesGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('linesGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedLines = Number(btn.dataset.lines || 2);
    syncOverlay(true);
    markDirtyAfterRender();
  });
});

$('hookStyleGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('hookStyleGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedHookStyle = btn.dataset.hstyle || 'pill-white';
    const ho = $('hookOverlay');
    if (ho) ho.className = 'hook-overlay hook-' + selectedHookStyle;
    markDirtyAfterRender();
  });
});

// Make Hook Title draggable vertically inside the phone preview
(() => {
  const ho = $('hookOverlay'), frame = $('previewWrap');
  if (!ho || !frame) return;
  let dragging = false, startY = 0, origPct = 16;
  ho.addEventListener('pointerdown', (e) => {
    dragging = true;
    ho.setPointerCapture(e.pointerId);
    startY = e.clientY;
    origPct = selectedHookY;
    e.preventDefault();
  });
  ho.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const rect = frame.getBoundingClientRect();
    if (!rect.height) return;
    const dy = ((e.clientY - startY) / rect.height) * 100;
    selectedHookY = Math.round(Math.max(8, Math.min(55, origPct + dy)));
    ho.style.top = selectedHookY + '%';
    ho.dataset.hy = String(selectedHookY);
    markDirtyAfterRender();
  });
  const stop = () => { dragging = false; };
  ho.addEventListener('pointerup', stop);
  ho.addEventListener('pointercancel', stop);
})();

// Direct on-preview drag (height) + 2-finger pinch (size) + A-/A+ buttons for captions
(() => {
  const ov = $('liveOverlay'), frame = $('previewWrap');
  if (!ov || !frame) return;
  const badge = $('pvLiveBadge');
  let badgeTimer = null;
  function flashBadge(txt) {
    if (!badge) return;
    badge.textContent = txt;
    clearTimeout(badgeTimer);
    badgeTimer = setTimeout(() => { badge.textContent = '↕ Pinça'; }, 1400);
  }
  function setScalePct(nextPct) {
    const clamped = Math.round(Math.max(65, Math.min(135, nextPct)));
    if ($('capScale')) $('capScale').value = String(clamped);
    syncOverlay(false);
    markDirtyAfterRender();
    flashBadge(`${clamped}% · ${$('posY').value}%`);
  }

  $('pvSizeDown')?.addEventListener('click', (e) => {
    e.stopPropagation();
    setScalePct(Number($('capScale')?.value || 100) - 5);
  });
  $('pvSizeUp')?.addEventListener('click', (e) => {
    e.stopPropagation();
    setScalePct(Number($('capScale')?.value || 100) + 5);
  });

  const ptrs = new Map();
  let dragStartY = 0, origPosY = 74;
  let pinchStartDist = 0, origScale = 100;

  function dist2(a, b) {
    return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  }

  ov.addEventListener('pointerdown', (e) => {
    ptrs.set(e.pointerId, e);
    try { ov.setPointerCapture(e.pointerId); } catch {}
    if (ptrs.size === 1) {
      dragStartY = e.clientY;
      origPosY = Number($('posY')?.value || 74);
    } else if (ptrs.size === 2) {
      const [p1, p2] = [...ptrs.values()];
      pinchStartDist = Math.max(10, dist2(p1, p2));
      origScale = Number($('capScale')?.value || 100);
    }
    e.preventDefault();
  });

  frame.addEventListener('pointerdown', (e) => {
    if (e.target === ov || ov.contains(e.target)) return;
    ptrs.set(e.pointerId, e);
    if (ptrs.size === 2) {
      const [p1, p2] = [...ptrs.values()];
      pinchStartDist = Math.max(10, dist2(p1, p2));
      origScale = Number($('capScale')?.value || 100);
    }
  });

  window.addEventListener('pointermove', (e) => {
    if (!ptrs.has(e.pointerId)) return;
    ptrs.set(e.pointerId, e);
    if (ptrs.size >= 2) {
      const [p1, p2] = [...ptrs.values()];
      const d = dist2(p1, p2);
      if (pinchStartDist > 0) {
        setScalePct(origScale * (d / pinchStartDist));
      }
      return;
    }
    if (ptrs.size === 1 && (e.target === ov || ov.contains(e.target) || ov.hasPointerCapture?.(e.pointerId))) {
      const rect = frame.getBoundingClientRect();
      if (!rect.height) return;
      const dy = ((e.clientY - dragStartY) / rect.height) * 100;
      const nextY = Math.round(Math.max(18, Math.min(86, origPosY + dy)));
      if ($('posY')) $('posY').value = String(nextY);
      syncOverlay(false);
      markDirtyAfterRender();
      flashBadge(`${$('capScale')?.value || 100}% · ${nextY}%`);
    }
  });

  const endPtr = (e) => {
    ptrs.delete(e.pointerId);
    if (ptrs.size === 1) {
      const [rem] = [...ptrs.values()];
      dragStartY = rem.clientY;
      origPosY = Number($('posY')?.value || 74);
    }
  };
  window.addEventListener('pointerup', endPtr);
  window.addEventListener('pointercancel', endPtr);
})();

$('customColorToggle')?.addEventListener('change', () => {
  $('accentColor').disabled = !$('customColorToggle').checked;
  syncOverlay(false);
  markDirtyAfterRender();
});

$('catTabs').querySelectorAll('.cat-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $('catTabs').querySelectorAll('.cat-tab').forEach((t) => t.classList.remove('is-active'));
    tab.classList.add('is-active');
    const cat = tab.dataset.cat;
    $('styleGrid').querySelectorAll('.style-pill').forEach((p) => {
      p.hidden = (p.dataset.cat !== cat);
    });
  });
});

$('styleGrid').querySelectorAll('.style-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('styleGrid').querySelectorAll('.style-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedStyle = btn.dataset.style;
    syncOverlay(true);
    markDirtyAfterRender();
  });
});

$('cutsToggle').addEventListener('change', () => {
  $('rhythmBox').hidden = !$('cutsToggle').checked;
});

$('rhythmGrid').querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('rhythmGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedRhythm = btn.dataset.rhythm;
  });
});

function renderBrollList() {
  const list = $('brollList');
  if (!list) return;
  list.replaceChildren();
  $('brollHint').hidden = !selectedBrolls.length;
  selectedBrolls.forEach((b, idx) => {
    const row = document.createElement('div');
    row.className = 'media-item';
    const lbl = document.createElement('span');
    lbl.className = 'media-name';
    lbl.textContent = `🎞️ B${idx + 1} · ${b.name}`;
    const sel = document.createElement('select');
    sel.className = 'media-sel';
    [['auto', 'Automático'], ['top', 'Topo (dividida)'], ['bottom', 'Baixo (dividida)'], ['full', 'Tela cheia']].forEach(([val, txt]) => {
      const o = document.createElement('option');
      o.value = val; o.textContent = txt;
      if (b.layout === val) o.selected = true;
      sel.append(o);
    });
    sel.addEventListener('change', () => { b.layout = sel.value; markDirtyAfterRender(); });
    const del = document.createElement('button');
    del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => {
      selectedBrolls.splice(idx, 1);
      renderBrollList();
      if (!$('reviewCard').hidden) renderCaptionEditor(currentCaptions);
      markDirtyAfterRender();
    });
    const times = document.createElement('div');
    times.className = 'media-times';
    const inS = document.createElement('input');
    inS.type = 'number'; inS.step = '0.5'; inS.min = '0'; inS.placeholder = 'Auto';
    inS.className = 'media-time-in';
    if (b.start !== undefined && b.start !== '') inS.value = b.start;
    inS.addEventListener('input', () => { b.start = inS.value; markDirtyAfterRender(); });
    const inE = document.createElement('input');
    inE.type = 'number'; inE.step = '0.5'; inE.min = '0'; inE.placeholder = 'Auto';
    inE.className = 'media-time-in';
    if (b.end !== undefined && b.end !== '') inE.value = b.end;
    inE.addEventListener('input', () => { b.end = inE.value; markDirtyAfterRender(); });
    const sTxt1 = document.createElement('span'); sTxt1.textContent = 'Início (s):';
    const sTxt2 = document.createElement('span'); sTxt2.textContent = 'Fim (s):';
    times.append(sTxt1, inS, sTxt2, inE);

    row.append(lbl, sel, del, times);
    list.append(row);
  });
}

function renderCardList() {
  const list = $('cardList');
  if (!list) return;
  list.replaceChildren();
  $('cardHint').hidden = !selectedCards.length;
  selectedCards.forEach((c, idx) => {
    const row = document.createElement('div');
    row.className = 'media-item';
    const img = document.createElement('img');
    img.className = 'media-thumb';
    img.src = c.url || (`/api/cards/${c.id}`);
    img.alt = c.name;
    const lbl = document.createElement('span');
    lbl.className = 'media-name';
    lbl.textContent = `C${idx + 1} · ${c.name}`;
    const sel = document.createElement('select');
    sel.className = 'media-sel';
    [
      ['auto', 'Automático'],
      ['side-right', 'Lateral Direita'],
      ['side-left', 'Lateral Esquerda'],
      ['corner-top', 'Canto Superior'],
    ].forEach(([val, txt]) => {
      const o = document.createElement('option');
      o.value = val; o.textContent = txt;
      if (c.anim === val) o.selected = true;
      sel.append(o);
    });
    sel.addEventListener('change', () => { c.anim = sel.value; markDirtyAfterRender(); });
    const del = document.createElement('button');
    del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => {
      selectedCards.splice(idx, 1);
      renderCardList();
      if (!$('reviewCard').hidden) renderCaptionEditor(currentCaptions);
      markDirtyAfterRender();
    });
    row.append(img, lbl, sel, del);
    list.append(row);
  });
}

$('sfxToggle')?.addEventListener('change', () => {
  if ($('sfxBankBox')) $('sfxBankBox').hidden = !$('sfxToggle').checked;
  markDirtyAfterRender();
});
$('sfxStyleSelect')?.addEventListener('change', () => markDirtyAfterRender());
$('sfxAllToggle')?.addEventListener('change', () => markDirtyAfterRender());
$('colorGradeToggle')?.addEventListener('change', () => markDirtyAfterRender());

$('brollFile')?.addEventListener('change', async (e) => {
  const files = [...(e.target.files || [])];
  if (!files.length) return;
  $('brollStatus').textContent = `⏳ Enviando ${files.length} B-roll(s)…`;
  for (const f of files) {
    try {
      const fd = new FormData();
      fd.append('broll', f, f.name || 'broll.mp4');
      const res = await fetch('/api/upload_broll', { method: 'POST', body: fd });
      const data = await safeJson(res);
      if (data.error || !data.broll_id) throw new Error(data.error || 'Erro');
      selectedBrolls.push({ id: data.broll_id, name: f.name || 'B-roll', layout: 'auto', start: '', end: '' });
    } catch {}
  }
  e.target.value = '';
  $('brollStatus').textContent = '＋ Adicionar vídeo(s) ou imagem(ns) B-roll';
  renderBrollList();
  if (!$('reviewCard').hidden) renderCaptionEditor(currentCaptions);
  markDirtyAfterRender();
});

$('cardFile')?.addEventListener('change', async (e) => {
  const files = [...(e.target.files || [])];
  if (!files.length) return;
  $('cardStatus').textContent = `⏳ Preparando ${files.length} imagem(ns)…`;
  for (const f of files) {
    try {
      const fd = new FormData();
      fd.append('card', f, f.name || 'card.png');
      fd.append('remove_bg', $('cardRemoveBgToggle')?.checked ? '1' : '0');
      const res = await fetch('/api/upload_card', { method: 'POST', body: fd });
      const data = await safeJson(res);
      if (data.error || !data.card_id) throw new Error(data.error || 'Erro');
      selectedCards.push({ id: data.card_id, name: f.name || 'Card', url: data.url, anim: 'auto' });
    } catch {}
  }
  e.target.value = '';
  $('cardStatus').textContent = '＋ Adicionar card(s) / imagens flutuantes';
  renderCardList();
  if (!$('reviewCard').hidden) renderCaptionEditor(currentCaptions);
  markDirtyAfterRender();
});

$('resGrid').querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('resGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedResolution = btn.dataset.res;
    updateResTagDisplay();
  });
});

$('accentColor').addEventListener('input', () => { syncOverlay(false); markDirtyAfterRender(); });
$('posY').addEventListener('input', () => { syncOverlay(false); markDirtyAfterRender(); });
$('capScale')?.addEventListener('input', () => { syncOverlay(false); markDirtyAfterRender(); });
$('fontSelect')?.addEventListener('change', () => { syncOverlay(true); markDirtyAfterRender(); });
$('smallFontSelect')?.addEventListener('change', () => { syncOverlay(true); markDirtyAfterRender(); });

// Initialize accent color input state on load (customColorToggle starts checked)
(function initColorToggle() {
  const toggle = $('customColorToggle');
  const colorInput = $('accentColor');
  if (toggle && colorInput) {
    colorInput.disabled = !toggle.checked;
  }
})();

syncOverlay(false);

const SAFE_MODES = [
  { id: 'off', label: '📱 Área segura', bottom: '' },
  { id: 'reels', label: '📱 Reels', bottom: 'Botões / Legenda Reels' },
  { id: 'tiktok', label: '🎵 TikTok', bottom: 'Descrição / Som TikTok' },
  { id: 'shorts', label: '▶ Shorts', bottom: 'Título / Canal Shorts' },
];
let safeModeIdx = 0;
$('safeZoneBtn')?.addEventListener('click', () => {
  safeModeIdx = (safeModeIdx + 1) % SAFE_MODES.length;
  const mode = SAFE_MODES[safeModeIdx];
  const sz = $('safeZones');
  const on = mode.id !== 'off';
  sz.hidden = !on;
  if (on) {
    sz.dataset.platform = mode.id;
    const btm = sz.querySelector('.sz-bottom');
    if (btm) btm.textContent = mode.bottom;
  }
  $('safeZoneBtn').textContent = mode.label;
  $('safeZoneBtn').classList.toggle('is-on', on);
});

$('hookTitleInput')?.addEventListener('input', () => {
  const val = $('hookTitleInput').value.trim();
  const ho = $('hookOverlay');
  ho.textContent = val;
  ho.hidden = !val;
  $('hookStylesBox').hidden = !val;
  ho.className = 'hook-overlay hook-' + selectedHookStyle;
  ho.style.top = selectedHookY + '%';
});

$('videoFile').addEventListener('change', (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  selectedFile = f;
  currentJobId = '';
  cachedVideoBlob = null;
  currentCaptions = [];
  window.EuEditoMotion?.reset();
  flowStage = 'transcribe';
  $('reviewCard').hidden = true;
  $('generateBtn').textContent = '1. Transcrever & Revisar Legendas →';
  setStickyVisible(true);
  $('uploadTitle').textContent = f.name || 'Vídeo selecionado';
  $('uploadSub').textContent = ((f.size || 0) / (1024 * 1024)).toFixed(1) + ' MB · Pronto para enviar';
  try {
    const vid = $('previewVideo');
    vid.src = URL.createObjectURL(f);
    vid.muted = true; // must be muted for autoplay first-frame trick on mobile
    vid.hidden = false;
    $('emptyStage').hidden = true;
    // Force first video frame to render immediately (no black screen before play)
    vid.addEventListener('loadedmetadata', () => {
      try {
        vid.currentTime = 0.001;
        // On mobile, autoplay muted briefly then pause to paint first frame
        vid.play().then(() => {
          setTimeout(() => { vid.pause(); vid.muted = false; vid.currentTime = 0.001; }, 80);
        }).catch(() => {
          vid.muted = false;
          try { if (vid.currentTime < 0.05) vid.currentTime = 0.05; } catch {}
        });
      } catch {}
    }, { once: true });
    vid.load();
  } catch {}
  $('liveOverlay').hidden = false;
  $('resultBox').hidden = true;
  $('errorMsg').hidden = true;
  $('generateBtn').disabled = false;
});

$('shareBtn').addEventListener('click', async () => {
  if (!lastVideoUrl) return;
  const btn = $('shareBtn');
  const origTxt = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Preparando vídeo…';
  try {
    const blob = await getVideoBlob();
    const file = new File([blob], `eu-edito-${currentJobId || 'pronto'}.mp4`, { type: 'video/mp4' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: 'Vídeo Pronto · Eu Edito' });
    } else {
      triggerBlobDownload(blob, `eu-edito-${currentJobId || 'pronto'}.mp4`);
    }
  } catch (err) {
    if (err && err.name !== 'AbortError') {
      try {
        const blob = await getVideoBlob();
        triggerBlobDownload(blob, `eu-edito-${currentJobId || 'pronto'}.mp4`);
      } catch {}
    }
  } finally {
    btn.textContent = origTxt;
    btn.disabled = false;
  }
});

$('downloadMp4')?.addEventListener('click', async (e) => {
  if (!lastVideoUrl) return;
  e.preventDefault();
  const btn = $('downloadMp4');
  const origTxt = btn.textContent;
  btn.textContent = '⏳ Baixando vídeo…';
  btn.style.pointerEvents = 'none';
  try {
    const blob = await getVideoBlob();
    triggerBlobDownload(blob, `eu-edito-${currentJobId || 'pronto'}.mp4`);
  } catch {
    // Fallback without leaving standalone PWA window
    window.open(lastVideoUrl + '?dl=1', '_blank', 'noopener');
  } finally {
    btn.textContent = origTxt;
    btn.style.pointerEvents = '';
  }
});

$('downloadSrt')?.addEventListener('click', async (e) => {
  const href = $('downloadSrt')?.getAttribute('href');
  if (!href || href === '#') return;
  e.preventDefault();
  try {
    const blob = await fetch(href).then((r) => r.blob());
    triggerBlobDownload(blob, `eu-edito-${currentJobId || 'legendas'}.srt`);
  } catch {
    window.open(href, '_blank', 'noopener');
  }
});

async function safeJson(res) {
  const txt = await res.text();
  try {
    return JSON.parse(txt);
  } catch {
    throw new Error(`Servidor ocupado (HTTP ${res.status}). Tente novamente com um vídeo menor ou aguarde 30s.`);
  }
}

function uploadWithProgress(file) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload', true);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.min(25, Math.max(5, Math.round((e.loaded / e.total) * 25)));
        $('progressText').textContent = `Enviando vídeo… (${Math.round((e.loaded / e.total) * 100)}%)`;
        $('progressPct').textContent = pct + '%';
        $('progressFill').style.width = pct + '%';
      }
    };
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText || '{}');
        if (xhr.status >= 200 && xhr.status < 300 && !data.error) resolve(data);
        else reject(new Error(data.error || `Erro ao enviar vídeo (HTTP ${xhr.status}).`));
      } catch {
        reject(new Error(`Servidor reiniciando (HTTP ${xhr.status}). Aguarde alguns segundos e tente de novo.`));
      }
    };
    xhr.onerror = () => reject(new Error('Falha de rede ao enviar vídeo.'));
    const fd = new FormData();
    fd.append('video', file, (file && file.name) ? file.name : 'video.mp4');
    xhr.send(fd);
  });
}

function guessDefaultMainIdx(tokens) {
  if (!tokens.length) return 0;
  let best = 0, bestLen = -1;
  tokens.forEach((t, i) => {
    const cleanLen = t.replace(/[^\p{L}\p{N}]/gu, '').length;
    if (cleanLen > bestLen) { bestLen = cleanLen; best = i; }
  });
  return best;
}

function renderCaptionEditor(captions) {
  currentCaptions = (captions || []).map((c) => ({ ...c }));
  const list = $('captionEditorList');
  list.replaceChildren();
  currentCaptions.forEach((cap, idx) => {
    const row = document.createElement('div');
    row.className = 'cap-edit-row';
    const topBar = document.createElement('div');
    topBar.className = 'cap-edit-top';
    const playBtn = document.createElement('button');
    playBtn.type = 'button';
    playBtn.className = 'cap-edit-play';
    playBtn.textContent = '▶';
    playBtn.title = 'Ouvir este trecho';
    playBtn.addEventListener('click', () => {
      const vid = $('previewVideo');
      if (!vid) return;
      vid.muted = false;
      vid.currentTime = Math.max(0, Number(cap.orig_s ?? cap.s ?? 0) - 0.15);
      vid.play().catch(() => {});
    });
    const tm = document.createElement('span');
    tm.className = 'cap-edit-time';
    tm.textContent = Number(cap.s || 0).toFixed(1) + 's';
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.className = 'cap-edit-input';
    inp.value = cap.text || '';

    const chipsBox = document.createElement('div');
    chipsBox.className = 'cap-word-chips';
    function renderChips() {
      const toks = (inp.value || '').trim().split(/\s+/).filter(Boolean);
      chipsBox.replaceChildren();
      if (!toks.length) return;
      let activeIdx = currentCaptions[idx].main_idx;
      if (activeIdx == null || activeIdx < 0 || activeIdx >= toks.length) {
        activeIdx = guessDefaultMainIdx(toks);
      }
      toks.forEach((tok, wIdx) => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'cap-word-chip' + (wIdx === activeIdx ? ' is-main' : '');
        chip.textContent = tok;
        chip.title = 'Tocar para destacar esta palavra';
        chip.addEventListener('click', () => {
          currentCaptions[idx].main_idx = wIdx;
          renderChips();
          markDirtyAfterRender();
        });
        chipsBox.append(chip);
      });
      const SFX_CYCLE = [false, 'auto', 'pop', 'whoosh', 'impact', 'chime', 'click'];
      const SFX_LABELS = { auto: '🔊 Auto', pop: '🔊 Pop', whoosh: '🔊 Whoosh', impact: '🔊 Impacto', chime: '🔊 Brilho', click: '🔊 Clique' };
      const curSfx = currentCaptions[idx].sfx || false;
      const sfxBtn = document.createElement('button');
      sfxBtn.type = 'button';
      sfxBtn.className = 'cap-chip-sfx' + (curSfx ? ' is-on' : '');
      sfxBtn.textContent = curSfx ? (SFX_LABELS[curSfx] || '🔊 SFX') : '🔊 SFX';
      sfxBtn.title = 'Tocar para alternar efeito sonoro (Auto / Pop / Whoosh / Impacto / Brilho / Clique)';
      sfxBtn.addEventListener('click', () => {
        const pos = SFX_CYCLE.indexOf(currentCaptions[idx].sfx || false);
        currentCaptions[idx].sfx = SFX_CYCLE[(pos + 1) % SFX_CYCLE.length];
        renderChips();
        markDirtyAfterRender();
      });
      chipsBox.append(sfxBtn);

      if (selectedBrolls.length) {
        const curBid = currentCaptions[idx].broll_id || '';
        const bIdx = selectedBrolls.findIndex((b) => b.id === curBid);
        const bBtn = document.createElement('button');
        bBtn.type = 'button';
        bBtn.className = 'cap-chip-broll' + (bIdx >= 0 ? ' is-on' : '');
        bBtn.textContent = bIdx >= 0 ? `🎞️ B${bIdx + 1}` : '🎞️ B-roll';
        bBtn.title = 'Escolher qual B-roll entra neste momento';
        bBtn.addEventListener('click', () => {
          const nextIdx = bIdx + 1;
          currentCaptions[idx].broll_id = nextIdx < selectedBrolls.length ? selectedBrolls[nextIdx].id : '';
          renderChips();
          markDirtyAfterRender();
        });
        chipsBox.append(bBtn);
      }

      selectedCards.forEach((crd, cIdx) => {
        const ids = Array.isArray(currentCaptions[idx].card_ids) ? currentCaptions[idx].card_ids : [];
        const active = ids.includes(crd.id);
        const cBtn = document.createElement('button');
        cBtn.type = 'button';
        cBtn.className = 'cap-chip-card' + (active ? ' is-on' : '');
        cBtn.textContent = `🖼️ C${cIdx + 1}`;
        cBtn.title = `Ativar Card ${cIdx + 1} (${crd.name}) neste momento`;
        cBtn.addEventListener('click', () => {
          const cur = Array.isArray(currentCaptions[idx].card_ids) ? [...currentCaptions[idx].card_ids] : [];
          const i = cur.indexOf(crd.id);
          if (i >= 0) cur.splice(i, 1);
          else cur.push(crd.id);
          currentCaptions[idx].card_ids = cur;
          renderChips();
          markDirtyAfterRender();
        });
        chipsBox.append(cBtn);
      });
    }
    renderChips();

    inp.addEventListener('input', () => {
      currentCaptions[idx].text = inp.value;
      renderChips();
      markDirtyAfterRender();
    });
    const cutBtn = document.createElement('button');
    cutBtn.type = 'button';
    cutBtn.className = 'cap-edit-cut';
    cutBtn.textContent = cap.cut ? 'Voltar' : '✂️';
    cutBtn.title = 'Remover esta fala do vídeo';
    cutBtn.addEventListener('click', () => {
      currentCaptions[idx].cut = !currentCaptions[idx].cut;
      row.classList.toggle('is-cut', !!currentCaptions[idx].cut);
      cutBtn.textContent = currentCaptions[idx].cut ? 'Voltar' : '✂️';
      markDirtyAfterRender();
    });
    topBar.append(playBtn, tm, inp, cutBtn);
    row.append(topBar, chipsBox);
    list.append(row);
  });
}

$('newVideoBtn')?.addEventListener('click', () => {
  selectedFile = null;
  lastVideoUrl = '';
  cachedVideoBlob = null;
  currentJobId = '';
  currentCaptions = [];
  window.EuEditoMotion?.reset();
  flowStage = 'transcribe';
  $('videoFile').value = '';
  $('uploadTitle').textContent = 'Escolher vídeo do celular';
  $('uploadSub').textContent = 'Toque para abrir sua galeria (iPhone ou Android)';
  $('previewVideo').hidden = true;
  $('emptyStage').hidden = false;
  $('liveOverlay').hidden = false;
  $('reviewCard').hidden = true;
  $('resultBox').hidden = true;
  $('errorMsg').hidden = true;
  $('generateBtn').textContent = '1. Transcrever & Revisar Legendas →';
  $('generateBtn').disabled = true;
  setStickyVisible(true);
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('generateBtn').addEventListener('click', async () => {
  if (!selectedFile) return;
  $('generateBtn').disabled = true;
  $('errorMsg').hidden = true;
  $('resultBox').hidden = true;
  $('progressBox').hidden = false;
  $('progressBox').scrollIntoView({ behavior: 'smooth', block: 'center' });

  try {
    if (flowStage === 'transcribe') {
      $('progressText').textContent = 'Enviando vídeo do celular…';
      $('progressPct').textContent = '5%';
      $('progressFill').style.width = '5%';

      const up = await uploadWithProgress(selectedFile);
      currentJobId = up.job_id;
      const trRes = await fetch('/api/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: currentJobId,
          cuts: $('cutsToggle').checked,
          rhythm: selectedRhythm,
        }),
      });
      const tr = await safeJson(trRes);
      if (tr.error) throw new Error(tr.error);

      while (true) {
        await new Promise((r) => setTimeout(r, 1200));
        const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
        $('progressText').textContent = st.message || 'Transcrevendo…';
        $('progressPct').textContent = (st.progress || 0) + '%';
        $('progressFill').style.width = (st.progress || 0) + '%';

        if (st.status === 'review') {
          renderCaptionEditor(st.captions || []);
          $('progressBox').hidden = true;
          $('reviewCard').hidden = false;
          $('reviewCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
          flowStage = 'render';
          $('generateBtn').textContent = '2. Gerar Vídeo Pronto →';
          $('generateBtn').disabled = false;
          return;
        }
        if (st.status === 'error') throw new Error(st.message || 'Erro na transcrição.');
      }
    }

    // Stage 2: Render video with edited captions (with transparent auto-recovery if server restarted)
    async function sendRenderRequest(jid) {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jid,
          captions: currentCaptions,
          style: selectedStyle,
          accent_color: $('customColorToggle')?.checked ? $('accentColor').value : '',
          pos_y: Number($('posY').value),
          caption_scale: Number($('capScale')?.value || 100),
          main_font: $('fontSelect')?.value || '',
          small_font: $('smallFontSelect')?.value || '',
          caption_lines: selectedLines,
          zoom: $('zoomToggle').checked,
          studio_audio: $('studioAudioToggle').checked,
          sfx: $('sfxToggle') ? $('sfxToggle').checked : true,
          sfx_style: $('sfxStyleSelect')?.value || 'auto',
          sfx_all_highlights: $('sfxAllToggle') ? $('sfxAllToggle').checked : true,
          color_grade: $('colorGradeToggle') ? $('colorGradeToggle').checked : false,
          brolls: selectedBrolls.map((b) => ({ id: b.id, layout: b.layout, start: b.start, end: b.end })),
          cards: selectedCards.map((c) => ({ id: c.id, anim: c.anim })),
          motion_layers: window.EuEditoMotion ? window.EuEditoMotion.getLayers() : [],
          hook_title: ($('hookTitleInput')?.value || '').trim(),
          hook_style: selectedHookStyle,
          hook_y: selectedHookY,
          resolution: selectedResolution,
        }),
      });
      return { status: res.status, data: await safeJson(res) };
    }

    $('progressText').textContent = 'Aplicando legendas revisadas…';
    $('progressPct').textContent = '60%';
    $('progressFill').style.width = '60%';

    let { status: renStatus, data: ren } = await sendRenderRequest(currentJobId);
    if ((renStatus === 404 || /não encontrado/i.test(ren.error || '')) && selectedFile) {
      $('progressText').textContent = 'Reconectando vídeo ao servidor…';
      const up2 = await uploadWithProgress(selectedFile);
      currentJobId = up2.job_id;
      const tr2 = await safeJson(await fetch('/api/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: currentJobId, cuts: $('cutsToggle').checked, rhythm: selectedRhythm }),
      }));
      if (tr2.error) throw new Error(tr2.error);
      while (true) {
        await new Promise((r) => setTimeout(r, 1200));
        const st0 = await safeJson(await fetch('/api/jobs/' + currentJobId));
        if (st0.status === 'review') break;
        if (st0.status === 'error') throw new Error(st0.message || 'Erro ao reconectar vídeo.');
      }
      ({ status: renStatus, data: ren } = await sendRenderRequest(currentJobId));
    }
    if (ren.error) throw new Error(ren.error);

    while (true) {
      await new Promise((r) => setTimeout(r, 1400));
      const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
      $('progressText').textContent = st.message || 'Renderizando…';
      $('progressPct').textContent = (st.progress || 0) + '%';
      $('progressFill').style.width = (st.progress || 0) + '%';

      if (st.status === 'done') {
        lastVideoUrl = st.video_url;
        cachedVideoBlob = null;
        getVideoBlob().catch(() => {});
        $('previewVideo').src = st.video_url;
        $('previewVideo').muted = false;
        $('previewVideo').hidden = false;
        $('emptyStage').hidden = true;
        $('liveOverlay').hidden = true;
        $('downloadMp4').href = st.video_url + '?dl=1';
        $('downloadSrt').href = st.srt_url;
        $('shareBtn').hidden = !navigator.share;
        $('transcriptText').textContent = st.transcript || '';
        $('statsRow').innerHTML = `
          <div class="stat-pill"><strong>${st.stats.resolution || '1080p'}</strong><small>Qualidade</small></div>
          <div class="stat-pill"><strong>${st.stats.duration}s</strong><small>Duração</small></div>
          <div class="stat-pill"><strong>${st.stats.removed_seconds}s</strong><small>Cortados</small></div>
        `;
        $('progressBox').hidden = true;
        $('resultBox').hidden = false;
        $('resultBox').scrollIntoView({ behavior: 'smooth', block: 'start' });
        $('generateBtn').disabled = false;
        setStickyVisible(false);
        break;
      }
      if (st.status === 'error') throw new Error(st.message || 'Erro ao renderizar o vídeo.');
    }
  } catch (err) {
    $('progressBox').hidden = true;
    $('errorMsg').textContent = err?.message || 'Falha no processamento.';
    $('errorMsg').hidden = false;
    $('errorMsg').scrollIntoView({ behavior: 'smooth', block: 'center' });
    $('generateBtn').disabled = false;
  }
});
