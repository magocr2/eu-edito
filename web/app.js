if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

const $ = (id) => document.getElementById(id);
let selectedFile = null;
let selectedStyle = 'dynamic-bold';
let selectedResolution = '1080p';
let deferredPrompt = null;
let lastVideoUrl = '';

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

function syncOverlay() {
  const ov = $('liveOverlay');
  ov.style.top = $('posY').value + '%';
  ov.style.setProperty('--accent', $('accentColor').value);
  $('posYVal').textContent = $('posY').value + '%';
  const small = ov.querySelector('small');
  const strong = ov.querySelector('strong');
  if (selectedStyle === 'editorial-serif') {
    strong.style.fontFamily = 'Georgia, serif';
    strong.style.fontStyle = 'italic';
    strong.textContent = 'faria diferente';
    small.textContent = 'Só que eu';
  } else if (selectedStyle === 'clean-minimal') {
    strong.style.fontFamily = 'inherit';
    strong.style.fontStyle = 'normal';
    strong.textContent = 'faria diferente';
    small.textContent = 'só que eu';
  } else {
    strong.style.fontFamily = 'inherit';
    strong.style.fontStyle = 'normal';
    strong.textContent = 'FARIA DIFERENTE';
    small.textContent = 'SÓ QUE EU';
  }
}

$('styleGrid').querySelectorAll('.style-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('styleGrid').querySelectorAll('.style-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedStyle = btn.dataset.style;
    syncOverlay();
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

$('accentColor').addEventListener('input', syncOverlay);
$('posY').addEventListener('input', syncOverlay);
syncOverlay();

$('videoFile').addEventListener('change', (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  selectedFile = f;
  $('uploadTitle').textContent = f.name;
  $('uploadSub').textContent = (f.size / (1024 * 1024)).toFixed(1) + ' MB · Pronto para processar';
  $('previewVideo').src = URL.createObjectURL(f);
  $('previewWrap').hidden = false;
  $('liveOverlay').hidden = false;
  $('resultBox').hidden = true;
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

function uploadWithProgress(file) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload');
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
        else reject(new Error(data.error || 'Falha ao enviar vídeo.'));
      } catch {
        reject(new Error('Resposta inválida ao enviar vídeo.'));
      }
    };
    xhr.onerror = () => reject(new Error('Sem conexão com o servidor.'));
    const fd = new FormData();
    fd.append('video', file);
    xhr.send(fd);
  });
}

$('newVideoBtn')?.addEventListener('click', () => {
  selectedFile = null;
  lastVideoUrl = '';
  $('videoFile').value = '';
  $('uploadTitle').textContent = 'Escolher vídeo do celular';
  $('uploadSub').textContent = 'Toque para abrir sua galeria (iPhone ou Android)';
  $('previewWrap').hidden = true;
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
    const proc = await fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: up.job_id,
        style: selectedStyle,
        accent_color: $('accentColor').value,
        pos_y: Number($('posY').value),
        cuts: $('cutsToggle').checked,
        zoom: $('zoomToggle').checked,
        resolution: selectedResolution,
      }),
    }).then((r) => r.json());
    if (proc.error) throw new Error(proc.error);

    while (true) {
      await new Promise((r) => setTimeout(r, 1200));
      const st = await fetch('/api/jobs/' + up.job_id).then((r) => r.json());
      $('progressText').textContent = st.message || 'Processando…';
      $('progressPct').textContent = (st.progress || 0) + '%';
      $('progressFill').style.width = (st.progress || 0) + '%';

      if (st.status === 'done') {
        lastVideoUrl = st.video_url;
        $('previewVideo').src = st.video_url;
        $('previewVideo').muted = false;
        $('previewWrap').hidden = false;
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
    $('errorMsg').textContent = err.message || 'Falha no processamento.';
    $('errorMsg').hidden = false;
    $('generateBtn').disabled = false;
  }
});
