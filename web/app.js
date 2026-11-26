if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
let selectedFile = null;
let selectedStyle = 'classic';
let selectedLines = 2;
let selectedHookStyle = 'pill-white';
let selectedHookY = 16;
let selectedRhythm = 'natural';
let selectedResolution = '1080p';
let deferredPrompt = null;
let lastVideoUrl = '';
let currentJobId = '';
let currentCaptions = [];
let flowStage = 'transcribe'; // 'transcribe' -> 'render'
let maxExportRes = '1080p';

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
    const delay = idx * 85;
    let frames = [{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }];
    let dur = 360;
    if (style === 'clean-14' || style === 'clean-12') {
      frames = isMain ? [{ opacity: 0, transform: 'scale(.1)' }, { opacity: 1, transform: 'scale(1)' }] : [{ opacity: 0, transform: 'translateX(18px)' }, { opacity: 1, transform: 'translateX(0)' }];
      dur = 420;
    } else if (style === 'clean-13' || style === 'clean' || style === 'clean-lavish') {
      frames = [{ opacity: 0, transform: 'translateX(20px)' }, { opacity: 1, transform: 'translateX(0)' }];
    } else if (style === 'clean-9') {
      frames = [{ opacity: 0, transform: 'translateY(-10px)' }, { opacity: 1, transform: 'translateY(0)' }];
    } else if (style === 'clean-11') {
      frames = [{ opacity: 0 }, { opacity: 1 }];
      dur = 180;
    }
    try { node.animate(frames, { duration: dur, delay, fill: 'both', easing: 'cubic-bezier(.16,1,.3,1)' }); } catch {}
  });
}

function syncOverlay(animate = false) {
  const ov = $('liveOverlay');
  ov.className = 'live-overlay style-' + selectedStyle + (selectedLines === 1 ? ' is-one-line' : '');
  ov.innerHTML = EXAMPLES[selectedStyle] || EXAMPLES.classic;
  ov.style.top = $('posY').value + '%';
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
  });
});

$('hookStyleGrid')?.querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('hookStyleGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedHookStyle = btn.dataset.hstyle || 'pill-white';
    const ho = $('hookOverlay');
    if (ho) ho.className = 'hook-overlay hook-' + selectedHookStyle;
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
  });
  const stop = () => { dragging = false; };
  ho.addEventListener('pointerup', stop);
  ho.addEventListener('pointercancel', stop);
})();

$('customColorToggle')?.addEventListener('change', () => {
  $('accentColor').disabled = !$('customColorToggle').checked;
  syncOverlay(false);
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
    if (flowStage === 'render' && !$('resultBox').hidden) {
      $('generateBtn').textContent = '🎨 Gerar novamente com este modelo →';
      setStickyVisible(true);
    }
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

$('resGrid').querySelectorAll('.res-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('resGrid').querySelectorAll('.res-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedResolution = btn.dataset.res;
    updateResTagDisplay();
  });
});

$('accentColor').addEventListener('input', () => syncOverlay(false));
$('posY').addEventListener('input', () => syncOverlay(false));

// Initialize accent color input state on load (customColorToggle starts checked)
(function initColorToggle() {
  const toggle = $('customColorToggle');
  const colorInput = $('accentColor');
  if (toggle && colorInput) {
    colorInput.disabled = !toggle.checked;
  }
})();

syncOverlay(false);

$('safeZoneBtn')?.addEventListener('click', () => {
  const sz = $('safeZones');
  const on = sz.hidden;
  sz.hidden = !on;
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
  currentCaptions = [];
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
  $('shareBtn').disabled = true;
  try {
    const blob = await fetch(lastVideoUrl).then((r) => r.blob());
    const file = new File([blob], 'eu-edito-pronto.mp4', { type: 'video/mp4' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: 'Vídeo Pronto · Eu Edito' });
    }
  } catch {}
  $('shareBtn').disabled = false;
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

function renderCaptionEditor(captions) {
  currentCaptions = (captions || []).map((c) => ({ ...c }));
  const list = $('captionEditorList');
  list.replaceChildren();
  currentCaptions.forEach((cap, idx) => {
    const row = document.createElement('div');
    row.className = 'cap-edit-row';
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
    inp.addEventListener('input', () => {
      currentCaptions[idx].text = inp.value;
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
    });
    row.append(playBtn, tm, inp, cutBtn);
    list.append(row);
  });
}

$('newVideoBtn')?.addEventListener('click', () => {
  selectedFile = null;
  lastVideoUrl = '';
  currentJobId = '';
  currentCaptions = [];
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

    // Stage 2: Render video with edited captions
    $('progressText').textContent = 'Aplicando legendas revisadas…';
    $('progressPct').textContent = '60%';
    $('progressFill').style.width = '60%';

    const renRes = await fetch('/api/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: currentJobId,
        captions: currentCaptions,
        style: selectedStyle,
        accent_color: $('customColorToggle')?.checked ? $('accentColor').value : '',
        pos_y: Number($('posY').value),
        caption_lines: selectedLines,
        zoom: $('zoomToggle').checked,
        studio_audio: $('studioAudioToggle').checked,
        hook_title: ($('hookTitleInput')?.value || '').trim(),
        hook_style: selectedHookStyle,
        hook_y: selectedHookY,
        resolution: selectedResolution,
      }),
    });
    const ren = await safeJson(renRes);
    if (ren.error) throw new Error(ren.error);

    while (true) {
      await new Promise((r) => setTimeout(r, 1400));
      const st = await safeJson(await fetch('/api/jobs/' + currentJobId));
      $('progressText').textContent = st.message || 'Renderizando…';
      $('progressPct').textContent = (st.progress || 0) + '%';
      $('progressFill').style.width = (st.progress || 0) + '%';

      if (st.status === 'done') {
        lastVideoUrl = st.video_url;
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
    $('errorMsg').textContent = err?.message || 'Falha no processamento.';
    $('errorMsg').hidden = false;
    $('generateBtn').disabled = false;
  }
});
