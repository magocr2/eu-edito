if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
let selectedFile = null;
let selectedStyle = 'classic';
let selectedRhythm = 'natural';
let selectedResolution = '1080p';
let deferredPrompt = null;
let lastVideoUrl = '';

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
  ov.className = 'live-overlay style-' + selectedStyle;
  ov.innerHTML = EXAMPLES[selectedStyle] || EXAMPLES.classic;
  ov.style.top = $('posY').value + '%';
  ov.style.setProperty('--accent', $('accentColor').value);
  $('posYVal').textContent = $('posY').value + '%';
  if (animate) animateOverlay(selectedStyle);
}

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
    $('resTag').textContent = selectedResolution === '4k' ? '4K UHD' : selectedResolution === '1080p' ? '1080p HD' : 'Original';
  });
});

$('accentColor').addEventListener('input', () => syncOverlay(false));
$('posY').addEventListener('input', () => syncOverlay(false));
syncOverlay(false);

$('videoFile').addEventListener('change', (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  selectedFile = f;
  $('uploadTitle').textContent = f.name || 'Vídeo selecionado';
  $('uploadSub').textContent = ((f.size || 0) / (1024 * 1024)).toFixed(1) + ' MB · Pronto para enviar';
  try {
    $('previewVideo').src = URL.createObjectURL(f);
    $('previewVideo').hidden = false;
    $('emptyStage').hidden = true;
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

$('newVideoBtn')?.addEventListener('click', () => {
  selectedFile = null;
  lastVideoUrl = '';
  $('videoFile').value = '';
  $('uploadTitle').textContent = 'Escolher vídeo do celular';
  $('uploadSub').textContent = 'Toque para abrir sua galeria (iPhone ou Android)';
  $('previewVideo').hidden = true;
  $('emptyStage').hidden = false;
  $('liveOverlay').hidden = false;
  $('resultBox').hidden = true;
  $('errorMsg').hidden = true;
  $('generateBtn').disabled = true;
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('generateBtn').addEventListener('click', async () => {
  if (!selectedFile) return;
  $('generateBtn').disabled = true;
  $('errorMsg').hidden = true;
  $('resultBox').hidden = true;
  $('progressBox').hidden = false;
  $('progressText').textContent = 'Enviando vídeo do celular…';
  $('progressPct').textContent = '5%';
  $('progressFill').style.width = '5%';
  $('progressBox').scrollIntoView({ behavior: 'smooth', block: 'center' });

  try {
    const up = await uploadWithProgress(selectedFile);
    const procRes = await fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: up.job_id,
        style: selectedStyle,
        accent_color: $('accentColor').value,
        pos_y: Number($('posY').value),
        cuts: $('cutsToggle').checked,
        rhythm: selectedRhythm,
        zoom: $('zoomToggle').checked,
        resolution: selectedResolution,
      }),
    });
    const proc = await safeJson(procRes);
    if (proc.error) throw new Error(proc.error);

    while (true) {
      await new Promise((r) => setTimeout(r, 1400));
      const stRes = await fetch('/api/jobs/' + up.job_id);
      const st = await safeJson(stRes);
      $('progressText').textContent = st.message || 'Processando…';
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
        break;
      }
      if (st.status === 'error') {
        throw new Error(st.message || 'Erro ao processar o vídeo.');
      }
    }
  } catch (err) {
    $('errorMsg').textContent = err?.message || 'Falha no processamento.';
    $('errorMsg').hidden = false;
    $('generateBtn').disabled = false;
  }
});
