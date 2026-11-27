if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
let selectedFile = null;
let selectedStyle = 'classic';
let selectedLines = 3;
let selectedRhythm = 'natural';
let selectedResolution = '1080p';
let selectedBrolls = []; // [{ id, name, layout, start, end, previewUrl, isImage }]
let selectedCards = [];  // [{ id, name, url, anim }]
let activePreviewBrollIdx = -1;
let activePreviewCardIdx = -1;
let deferredPrompt = null;
let lastVideoUrl = '';
let cachedVideoBlob = null;
let cachedShareFile = null;
let currentJobId = '';
let currentCaptions = [];
let flowStage = 'transcribe'; // 'transcribe' -> 'render'
let maxExportRes = '1080p';
let currentStep = 1;
let videoUnlocked = false;

function goToStep(step) {
  const s = Math.max(1, Math.min(7, Number(step) || 1));
  if (s > 1 && !videoUnlocked) return;
  currentStep = s;

  // Hide preview in Step 1; show live preview from Step 2 onwards
  const pvCard = $('previewCard');
  if (pvCard) pvCard.hidden = (s === 1 || !videoUnlocked);

  document.querySelectorAll('.wizard-step').forEach((sec) => {
    sec.hidden = Number(sec.dataset.step) !== s;
  });
  document.querySelectorAll('#wizardStepper .ws-pill').forEach((pill) => {
    const ps = Number(pill.dataset.step);
    pill.disabled = ps > 1 && !videoUnlocked;
    pill.classList.toggle('is-active', ps === s);
    pill.classList.toggle('is-done', videoUnlocked && ps < s);
  });

  // Sticky CTA visible only in Step 7 (or when captions review / edit dirty)
  const inFinalStep = (s === 7);
  setStickyVisible(inFinalStep && !$('resultBox').hidden ? ($('reviewCard') && !$('reviewCard').hidden) : inFinalStep);

  // When entering Step 7 and there is a configured B-roll/card, preview cleanly
  if (s !== 7 && $('resultBox').hidden) {
    clearMediaPreview();
  }
  if ($('pvStageHint')) {
    $('pvStageHint').textContent = s === 7
      ? 'Prévia ao vivo de legendas, B-rolls e cards'
      : 'Arraste a legenda ou use A-/A+';
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('#wizardStepper .ws-pill').forEach((pill) => {
  pill.addEventListener('click', () => goToStep(Number(pill.dataset.step)));
});
document.querySelectorAll('[data-next]').forEach((btn) => {
  btn.addEventListener('click', () => goToStep(Number(btn.dataset.next)));
});
document.querySelectorAll('[data-prev]').forEach((btn) => {
  btn.addEventListener('click', () => goToStep(Number(btn.dataset.prev)));
});

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
  cachedShareFile = new File([cachedVideoBlob], `eu-edito-${currentJobId || 'pronto'}.mp4`, { type: 'video/mp4' });
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
  const cta = $('stickyCta');
  if (cta) cta.hidden = !vis;
}

function updateResTagDisplay() {
  let label = selectedResolution === '4k' ? '4K UHD' : selectedResolution === '1080p' ? '1080p HD' : 'Original';
  if (maxExportRes === '720p' && (selectedResolution === '1080p' || selectedResolution === '4k')) {
    label = '720p HD';
  }
  if ($('resTag')) $('resTag').textContent = label;
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
  'classic': '<small>só que eu</small><strong>FARIA DIFERENTE</strong><small>neste vídeo</small>',
  'model-07': '<small>disputar a</small><strong>ATENÇÃO</strong><small>do público</small>',
  'clean-9': '<small>leitura limpa e</small><strong>FLUIDA</strong><small>no vídeo</small>',
  'clean-10': '<small>se eu fosse</small><strong>COMEÇAR</strong><small>agora mesmo</small>',
  'clean-12': '<small>ritmo dinâmico</small><strong>EM MOVIMENTO</strong><small>na tela</small>',
  'clean-lavish': '<small>Essa</small><strong>CAMPANHA</strong><small>tem força</small>',
  'kinetic-tracking': '<small>isso o que eu mostro</small><strong>EXATAMENTE</strong><small>no treino</small>',
  'kinetic-clip': '<small>mas a</small><strong>VERDADE</strong><small>não é essa</small>',
  'kinetic-blurgrid': '<small>era sobre encaixar</small><strong>CORTES</strong><small>sem perder ritmo</small>',
  'drawn-circle': '<small>se eles tiverem</small><strong>localização</strong><small>estratégica</small>',
  'drawn-strike': '<small>isso fica dentro</small><strong>da comunidade</strong><small>todos os dias</small>',
  'drawn-bar': '<small>um treino bem</small><strong>direcionado</strong><small>para você</small>',
};

const STYLE_DEFAULT_FX = {
  'drawn-circle': 'circle',
  'drawn-strike': 'strike',
  'drawn-bar': 'bar',
};

function resolveHighlightFx() {
  const manual = $('highlightFxSelect')?.value || 'auto';
  return manual === 'auto' ? (STYLE_DEFAULT_FX[selectedStyle] || 'none') : manual;
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  $('installBtn').hidden = false;
});
$('installBtn')?.addEventListener('click', async () => {
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
  $('closeIosHint')?.addEventListener('click', () => { $('iosHint').hidden = true; });
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
    if (style === 'kinetic-tracking' && isMain) {
      frames = [{ opacity: 0, letterSpacing: '0.38em' }, { opacity: 1, letterSpacing: '0.01em' }];
      dur = 430;
    } else if ((style === 'kinetic-clip' || style === 'drawn-strike') && isMain) {
      frames = [{ clipPath: 'inset(0 100% 0 0)', opacity: 0.4 }, { clipPath: 'inset(0 0% 0 0)', opacity: 1 }];
      dur = 400;
    } else if (style === 'kinetic-blurgrid' || style === 'drawn-circle' || style === 'clean-9') {
      frames = [{ opacity: 0, transform: 'scale(.88)', filter: 'blur(6px)' }, { opacity: 1, transform: 'scale(1)', filter: 'blur(0)' }];
      dur = 300;
    } else if (style === 'drawn-bar' && isMain) {
      frames = [{ opacity: 0, transform: 'translateX(-26px)' }, { opacity: 1, transform: 'translateX(0)' }];
      dur = 260;
    } else if (style === 'clean-12' || style === 'model-07') {
      frames = isMain
        ? [{ opacity: 0, transform: 'scale(.76)' }, { opacity: 1, transform: 'scale(1.05)', offset: 0.72 }, { opacity: 1, transform: 'scale(1)' }]
        : [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }];
      dur = 360;
    } else if (style === 'clean-lavish') {
      frames = [{ opacity: 0, transform: 'translateX(16px)' }, { opacity: 1, transform: 'translateX(0)' }];
    }
    try { node.animate(frames, { duration: dur, delay, fill: 'both', easing: 'cubic-bezier(.16,1,.3,1)' }); } catch {}
  });
}

function syncOverlay(animate = false) {
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
  const activeFx = resolveHighlightFx();
  const fxCls = activeFx !== 'none' ? ` has-fx-${activeFx}` : '';
  const modeCls = (lineMode === 1 ? ' is-one-line' : (lineMode === 2 ? ' is-two-line' : '')) + (isBold ? ' is-bold' : '') + fxCls;
  ov.className = 'live-overlay style-' + selectedStyle + modeCls;
  ov.innerHTML = EXAMPLES[selectedStyle] || EXAMPLES.classic;

  // Inject synced drawn highlight graphics (circle / strike / bar) onto the highlighted word
  const mainNode = ov.querySelector('strong, em');
  if (mainNode && activeFx === 'circle') {
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'hl-svg-circle');
    svg.setAttribute('viewBox', '0 0 120 56');
    svg.setAttribute('preserveAspectRatio', 'none');
    const el = document.createElementNS(svgNS, 'ellipse');
    el.setAttribute('cx', '60'); el.setAttribute('cy', '28');
    el.setAttribute('rx', '56'); el.setAttribute('ry', '24');
    svg.appendChild(el);
    mainNode.appendChild(svg);
  } else if (mainNode && activeFx === 'strike') {
    const ln = document.createElement('span');
    ln.className = 'hl-strike-line';
    mainNode.appendChild(ln);
  } else if (mainNode && activeFx === 'bar') {
    const bg = document.createElement('span');
    bg.className = 'hl-bar-bg';
    mainNode.appendChild(bg);
  }
  // Rule: in 2-line mode, avoid leaving an orphan short tail word on row 3 by combining or balancing cleanly
  if (lineMode === 2 && ov.children.length === 3) {
    const thirdTxt = ov.children[2].textContent.trim();
    const firstNode = ov.children[0];
    if (thirdTxt.split(/\s+/).length <= 1 && firstNode.textContent.trim().split(/\s+/).length >= 1) {
      ov.children[2].remove();
    } else {
      const wrap = document.createElement('div');
      wrap.className = 'row-wrap';
      wrap.append(ov.children[1], ov.children[2]);
      ov.append(wrap);
    }
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
    ov.style.setProperty('--main-weight', '800'); // Highlighted words are ALWAYS bold
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
    ov.style.setProperty('--small-weight', isBold ? '800' : swt);
  } else {
    ov.classList.remove('has-custom-small-font');
    ov.style.removeProperty('--small-font');
    ov.style.removeProperty('--small-style');
    ov.style.removeProperty('--small-weight');
  }
  if ($('customColorToggle')?.checked) {
    ov.style.setProperty('--accent', $('accentColor').value);
  } else {
    ov.style.removeProperty('--accent');
  }
  $('posYVal').textContent = $('posY').value + '%';
  if (animate) animateOverlay(selectedStyle);
}

/* ---------- Live Preview for B-rolls (w/ gradient split mask) & Floating Cards ---------- */
function clearMediaPreview() {
  activePreviewBrollIdx = -1;
  activePreviewCardIdx = -1;
  const wrap = $('previewWrap');
  if (wrap) {
    wrap.classList.remove('split-top', 'split-bottom');
  }
  const bl = $('pvBrollLayer');
  const bv = $('pvBrollVid');
  const bi = $('pvBrollImg');
  if (bv) { try { bv.pause(); } catch {} bv.hidden = true; bv.removeAttribute('src'); }
  if (bi) { bi.hidden = true; bi.removeAttribute('src'); }
  if (bl) bl.hidden = true;
  const cs = $('pvCardStage');
  if (cs) { cs.hidden = true; cs.classList.remove('is-floating'); }
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = true;
}

$('clearPreviewMediaBtn')?.addEventListener('click', clearMediaPreview);

function previewBrollInStage(idx) {
  const b = selectedBrolls[idx];
  const wrap = $('previewWrap');
  const bl = $('pvBrollLayer');
  const bi = $('pvBrollImg');
  const bv = $('pvBrollVid');
  if (!b || !wrap || !bl) return;
  activePreviewBrollIdx = idx;
  let lay = (b.layout || 'auto').toLowerCase();
  if (lay === 'auto') {
    const cycle = ['top', 'pip-rounded', 'bottom', 'center-frame', 'full'];
    lay = cycle[idx % cycle.length];
  }
  wrap.classList.remove('split-top', 'split-bottom');
  if (lay === 'top') wrap.classList.add('split-top');
  else if (lay === 'bottom') wrap.classList.add('split-bottom');

  bl.dataset.layout = lay;
  bl.hidden = false;
  if (b.isImage) {
    bv.hidden = true;
    try { bv.pause(); } catch {}
    bi.src = b.previewUrl;
    bi.hidden = false;
  } else {
    bi.hidden = true;
    bv.src = b.previewUrl;
    bv.hidden = false;
    bv.currentTime = 0;
    bv.play().catch(() => {});
  }
  try {
    const kf = lay === 'triptych-strips'
      ? [{ transform: 'translateX(90px)', opacity: 0 }, { transform: 'translateX(0)', opacity: 1 }]
      : [{ opacity: 0, transform: 'scale(.95)' }, { opacity: 1, transform: 'scale(1)' }];
    bl.animate(kf, { duration: 300, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' });
  } catch {}
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
}

function previewCardInStage(idx) {
  const c = selectedCards[idx];
  const cs = $('pvCardStage');
  const ci = $('pvCardImg');
  if (!c || !cs || !ci) return;
  activePreviewCardIdx = idx;
  let anim = (c.anim || 'auto').toLowerCase();
  if (anim === 'auto') {
    const cycle = ['side-right', 'side-left', 'corner-top'];
    anim = cycle[idx % cycle.length];
  }
  cs.dataset.anim = anim;
  ci.src = c.url;
  cs.hidden = false;
  cs.classList.add('is-floating');
  cs.getAnimations?.().forEach((a) => a.cancel());
  let kf;
  if (anim === 'side-left') {
    kf = [
      { opacity: 0, transform: 'translateX(-72px) scale(.92)' },
      { opacity: 1, transform: 'translateX(0) scale(1)' },
    ];
  } else if (anim === 'corner-top') {
    kf = [
      { opacity: 0, transform: 'translateY(-64px) scale(.90)' },
      { opacity: 1, transform: 'translateY(0) scale(1)' },
    ];
  } else {
    kf = [
      { opacity: 0, transform: 'translateX(72px) scale(.92)' },
      { opacity: 1, transform: 'translateX(0) scale(1)' },
    ];
  }
  try {
    cs.animate(kf, { duration: 380, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' });
  } catch {}
  if ($('clearPreviewMediaBtn')) $('clearPreviewMediaBtn').hidden = false;
}

$('previewVideo')?.addEventListener('timeupdate', () => {
  const vid = $('previewVideo');
  if (!vid || vid.paused || currentStep !== 7 || !$('resultBox').hidden) return;
  const t = vid.currentTime || 0;
  // Sync timed B-rolls during playback if start/end were set
  const timedB = selectedBrolls.findIndex((b) => {
    const s = parseFloat(b.start);
    if (isNaN(s)) return false;
    const e = isNaN(parseFloat(b.end)) ? s + 3.5 : parseFloat(b.end);
    return t >= s && t <= e;
  });
  if (timedB >= 0 && activePreviewBrollIdx !== timedB) {
    previewBrollInStage(timedB);
  } else if (timedB < 0 && selectedBrolls.some((b) => b.start !== '' && b.start !== undefined) && activePreviewBrollIdx >= 0) {
    const bl = $('pvBrollLayer');
    if (bl) bl.hidden = true;
    $('previewWrap')?.classList.remove('split-top', 'split-bottom');
    activePreviewBrollIdx = -1;
  }
});

$('linesGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('linesGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedLines = Number(btn.dataset.lines || 2);
    syncOverlay(true);
    markDirtyAfterRender();
  });
});

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
$('boldToggle')?.addEventListener('change', () => {
  syncOverlay(false);
  markDirtyAfterRender();
});
$('highlightFxSelect')?.addEventListener('change', () => {
  syncOverlay(true);
  markDirtyAfterRender();
});

$('catTabs')?.querySelectorAll('.cat-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $('catTabs').querySelectorAll('.cat-tab').forEach((t) => t.classList.remove('is-active'));
    tab.classList.add('is-active');
    const cat = tab.dataset.cat;
    $('styleGrid').querySelectorAll('.style-pill').forEach((p) => {
      p.hidden = (p.dataset.cat !== cat);
    });
  });
});

$('styleGrid')?.querySelectorAll('.style-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('styleGrid').querySelectorAll('.style-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedStyle = btn.dataset.style;
    syncOverlay(true);
    markDirtyAfterRender();
  });
});

$('cutsToggle')?.addEventListener('change', () => {
  $('rhythmBox').hidden = !$('cutsToggle').checked;
});

$('rhythmGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
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

    const pvBtn = document.createElement('button');
    pvBtn.type = 'button'; pvBtn.className = 'media-preview-btn';
    pvBtn.textContent = '👁️ Prévia';
    pvBtn.addEventListener('click', () => previewBrollInStage(idx));

    const sel = document.createElement('select');
    sel.className = 'media-sel';
    [
      ['auto', 'Automático'],
      ['top', 'Topo (dividida c/ máscara)'],
      ['bottom', 'Baixo (dividida c/ máscara)'],
      ['pip-rounded', 'Janela Arredondada (Canto)'],
      ['center-frame', 'Quadro Central Estúdio'],
      ['triptych-strips', 'Faixa Horizontal Deslizante'],
      ['full', 'Tela cheia'],
    ].forEach(([val, txt]) => {
      const o = document.createElement('option');
      o.value = val; o.textContent = txt;
      if (b.layout === val) o.selected = true;
      sel.append(o);
    });
    sel.addEventListener('change', () => {
      b.layout = sel.value;
      previewBrollInStage(idx);
      markDirtyAfterRender();
    });

    const del = document.createElement('button');
    del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => {
      selectedBrolls.splice(idx, 1);
      if (activePreviewBrollIdx === idx) clearMediaPreview();
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

    row.append(lbl, pvBtn, sel, del, times);
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

    const pvBtn = document.createElement('button');
    pvBtn.type = 'button'; pvBtn.className = 'media-preview-btn';
    pvBtn.textContent = '👁️ Animar';
    pvBtn.addEventListener('click', () => previewCardInStage(idx));

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
    sel.addEventListener('change', () => {
      c.anim = sel.value;
      previewCardInStage(idx);
      markDirtyAfterRender();
    });

    const del = document.createElement('button');
    del.type = 'button'; del.className = 'media-del'; del.textContent = '✕';
    del.addEventListener('click', () => {
      selectedCards.splice(idx, 1);
      if (activePreviewCardIdx === idx) clearMediaPreview();
      renderCardList();
      if (!$('reviewCard').hidden) renderCaptionEditor(currentCaptions);
      markDirtyAfterRender();
    });
    row.append(img, lbl, pvBtn, sel, del);
    list.append(row);
  });
}

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
      selectedBrolls.push({
        id: data.broll_id,
        name: f.name || 'B-roll',
        layout: 'top',
        start: '',
        end: '',
        previewUrl: URL.createObjectURL(f),
        isImage: (f.type || '').startsWith('image/'),
      });
    } catch {}
  }
  e.target.value = '';
  $('brollStatus').textContent = '＋ Adicionar vídeo(s) ou imagem(ns) B-roll';
  renderBrollList();
  if (selectedBrolls.length) previewBrollInStage(selectedBrolls.length - 1);
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
      selectedCards.push({ id: data.card_id, name: f.name || 'Card', url: data.url, anim: 'side-right' });
    } catch {}
  }
  e.target.value = '';
  $('cardStatus').textContent = '＋ Adicionar card(s) / imagens flutuantes';
  renderCardList();
  if (selectedCards.length) previewCardInStage(selectedCards.length - 1);
  if (!$('reviewCard').hidden) renderCaptionEditor(currentCaptions);
  markDirtyAfterRender();
});

$('resGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('resGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedResolution = btn.dataset.res;
    updateResTagDisplay();
  });
});

$('accentColor')?.addEventListener('input', () => { syncOverlay(false); markDirtyAfterRender(); });
$('posY')?.addEventListener('input', () => { syncOverlay(false); markDirtyAfterRender(); });
$('capScale')?.addEventListener('input', () => { syncOverlay(false); markDirtyAfterRender(); });
$('fontSelect')?.addEventListener('change', () => { syncOverlay(true); markDirtyAfterRender(); });
$('smallFontSelect')?.addEventListener('change', () => { syncOverlay(true); markDirtyAfterRender(); });

(function initColorToggle() {
  const toggle = $('customColorToggle');
  const colorInput = $('accentColor');
  if (toggle && colorInput) colorInput.disabled = !toggle.checked;
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

$('videoFile').addEventListener('change', (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  selectedFile = f;
  videoUnlocked = true;
  currentJobId = '';
  cachedVideoBlob = null;
  currentCaptions = [];
  flowStage = 'transcribe';
  clearMediaPreview();
  $('reviewCard').hidden = true;
  $('generateBtn').textContent = '1. Transcrever & Revisar Legendas →';
  $('uploadTitle').textContent = f.name || 'Vídeo selecionado';
  $('uploadSub').textContent = ((f.size || 0) / (1024 * 1024)).toFixed(1) + ' MB · Pronto!';
  if ($('step1Nav')) $('step1Nav').hidden = false;

  try {
    const vid = $('previewVideo');
    vid.src = URL.createObjectURL(f);
    vid.muted = true;
    vid.hidden = false;
    $('emptyStage').hidden = true;
    vid.addEventListener('loadedmetadata', () => {
      try {
        vid.currentTime = 0.001;
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

  // Automatically jump straight to Step 2 with live preview enabled
  goToStep(2);
});

$('shareBtn').addEventListener('click', async () => {
  if (!lastVideoUrl) return;
  const btn = $('shareBtn');
  const origTxt = btn.textContent;
  // Use pre-cached File synchronously inside user gesture so iOS "Save Video" never fails!
  if (cachedShareFile && navigator.canShare && navigator.canShare({ files: [cachedShareFile] })) {
    try {
      await navigator.share({ files: [cachedShareFile], title: 'Vídeo Pronto · Eu Edito' });
      return;
    } catch (err) {
      if (err && err.name === 'AbortError') return;
    }
  }
  btn.disabled = true;
  btn.textContent = '⏳ Preparando vídeo…';
  try {
    await getVideoBlob();
    if (cachedShareFile && navigator.canShare && navigator.canShare({ files: [cachedShareFile] })) {
      await navigator.share({ files: [cachedShareFile], title: 'Vídeo Pronto · Eu Edito' });
    } else if ($('downloadMp4')) {
      $('downloadMp4').click();
    }
  } catch (err) {
    if (err && err.name !== 'AbortError' && $('downloadMp4')) {
      $('downloadMp4').click();
    }
  } finally {
    btn.textContent = origTxt;
    btn.disabled = false;
  }
});

// Let native <a href="...?dl=1" download="eu-edito-....mp4"> trigger OS Download Manager cleanly on Android/desktop!
$('downloadMp4')?.addEventListener('click', () => {
  const btn = $('downloadMp4');
  if (!btn || !lastVideoUrl) return;
  btn.download = `eu-edito-${currentJobId || 'pronto'}.mp4`;
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
          if (currentCaptions[idx].broll_id) previewBrollInStage(nextIdx);
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
          else {
            cur.push(crd.id);
            previewCardInStage(cIdx);
          }
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
  videoUnlocked = false;
  lastVideoUrl = '';
  cachedVideoBlob = null;
  currentJobId = '';
  currentCaptions = [];
  selectedBrolls = [];
  selectedCards = [];
  renderBrollList();
  renderCardList();
  clearMediaPreview();
  flowStage = 'transcribe';
  $('videoFile').value = '';
  $('uploadTitle').textContent = 'Escolher vídeo do celular';
  $('uploadSub').textContent = 'Toque para abrir sua galeria (iPhone ou Android)';
  if ($('step1Nav')) $('step1Nav').hidden = true;
  $('previewVideo').hidden = true;
  $('emptyStage').hidden = false;
  $('liveOverlay').hidden = false;
  $('reviewCard').hidden = true;
  $('resultBox').hidden = true;
  $('errorMsg').hidden = true;
  $('generateBtn').textContent = '1. Transcrever & Revisar Legendas →';
  $('generateBtn').disabled = true;
  goToStep(1);
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
          setStickyVisible(true);
          return;
        }
        if (st.status === 'error') throw new Error(st.message || 'Erro na transcrição.');
      }
    }

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
          caption_bold: !!$('boldToggle')?.checked,
          highlight_fx: $('highlightFxSelect')?.value || 'auto',
          main_font: $('fontSelect')?.value || '',
          small_font: $('smallFontSelect')?.value || '',
          caption_lines: selectedLines,
          zoom: $('zoomToggle').checked,
          studio_audio: $('studioAudioToggle').checked,
          color_grade: $('colorGradeToggle') ? $('colorGradeToggle').checked : false,
          brolls: selectedBrolls.map((b) => ({ id: b.id, layout: b.layout, start: b.start, end: b.end })),
          cards: selectedCards.map((c) => ({ id: c.id, anim: c.anim })),
          resolution: selectedResolution,
        }),
      });
      return { status: res.status, data: await safeJson(res) };
    }

    $('progressText').textContent = 'Aplicando legendas, cortes e mídias…';
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
        clearMediaPreview();
        lastVideoUrl = st.video_url;
        cachedVideoBlob = null;
        cachedShareFile = null;
        getVideoBlob().catch(() => {});
        $('previewVideo').src = st.video_url;
        $('previewVideo').muted = false;
        $('previewVideo').hidden = false;
        $('emptyStage').hidden = true;
        $('liveOverlay').hidden = true;
        $('downloadMp4').href = st.video_url + '?dl=1';
        $('downloadMp4').download = `eu-edito-${currentJobId || 'pronto'}.mp4`;
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

// Initialize Wizard on Step 1 (no preview shown until user picks a video)
goToStep(1);
