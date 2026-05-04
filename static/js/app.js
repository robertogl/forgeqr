// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
  });
});

// ── QR Type switching (static tab) ───────────────────────────────────────────
document.querySelectorAll('#type-grid .type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#type-grid .type-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.type-fields').forEach(f => f.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`fields-${btn.dataset.type}`).classList.add('active');
  });
});

// ── Social platform hint ──────────────────────────────────────────────────────
const socialPlatform = document.getElementById('social-platform');
const socialHint     = document.getElementById('social-hint');
const socialLabel    = document.getElementById('social-handle-label');
const socialHandle   = document.getElementById('social-handle');
if (socialPlatform) {
  socialPlatform.addEventListener('change', () => {
    const base = socialPlatform.value;
    if (base === 'whatsapp') {
      socialLabel.textContent = 'Phone Number';
      socialHandle.placeholder = '391234567890';
      socialHint.innerHTML = 'Include country code, no spaces or + (e.g. <strong>391234567890</strong> for +39 123 456 7890)';
    } else if (base) {
      socialLabel.textContent = 'Username / Handle';
      const domain = base.replace('https://', '').replace(/\/$/, '').replace(/@$/, '');
      socialHint.innerHTML = `e.g. ${domain}/<strong>yourhandle</strong>`;
      socialHandle.placeholder = 'yourhandle';
    } else {
      socialLabel.textContent = 'Profile URL';
      socialHandle.placeholder = 'https://example.com/yourprofile';
      socialHint.innerHTML = 'Paste the full profile URL';
    }
  });
}

// ── Edge line toggles ─────────────────────────────────────────────────────────
['static', 'dynamic', 'app'].forEach(prefix => {
  const cb      = document.getElementById(`${prefix}-edge-enable`);
  const controls = document.getElementById(`${prefix}-edge-controls`);
  const range   = document.getElementById(`${prefix}-edge-width`);
  const valSpan = document.getElementById(`${prefix}-edge-width-val`);
  if (!cb) return;
  cb.addEventListener('change', () => controls.classList.toggle('visible', cb.checked));
  range.addEventListener('input', () => { valSpan.textContent = range.value; });
});

// ── Effect grids ──────────────────────────────────────────────────────────────
document.querySelectorAll('.effect-grid').forEach(grid => {
  grid.querySelectorAll('.effect-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      grid.querySelectorAll('.effect-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});

function getActiveEffect(gridId) {
  return document.querySelector(`#${gridId} .effect-btn.active`)?.dataset.effect || 'flat';
}

// ── Shape grids (dot + container) ────────────────────────────────────────────
document.querySelectorAll('.shape-grid').forEach(grid => {
  grid.querySelectorAll('.shape-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      grid.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});

// ── Dot style grids ───────────────────────────────────────────────────────────
document.querySelectorAll('.dot-grid').forEach(grid => {
  grid.querySelectorAll('.dot-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      grid.querySelectorAll('.dot-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});

function getActiveDotStyle(gridId) {
  return document.querySelector(`#${gridId} .dot-btn.active`)?.dataset.style || 'square';
}

function getActiveEyeStyle(gridId) {
  return document.querySelector(`#${gridId} .dot-btn.active`)?.dataset.style || 'square';
}

function getActiveShapeStyle(gridId) {
  return document.querySelector(`#${gridId} .shape-btn.active`)?.dataset.style || 'square';
}

// ── Build static QR data string ───────────────────────────────────────────────
function buildStaticData() {
  const type = document.querySelector('#type-grid .type-btn.active')?.dataset.type || 'url';

  switch (type) {
    case 'url':
      return document.getElementById('url-input').value.trim();

    case 'text':
      return document.getElementById('text-input').value.trim();

    case 'wifi': {
      const ssid   = document.getElementById('wifi-ssid').value.trim();
      const pass   = document.getElementById('wifi-password').value;
      const sec    = document.getElementById('wifi-security').value;
      const hidden = document.getElementById('wifi-hidden').checked ? 'true' : 'false';
      return `WIFI:T:${sec};S:${ssid};P:${pass};H:${hidden};;`;
    }

    case 'email': {
      const addr    = document.getElementById('email-address').value.trim();
      const subject = encodeURIComponent(document.getElementById('email-subject').value.trim());
      const body    = encodeURIComponent(document.getElementById('email-body').value.trim());
      return `mailto:${addr}?subject=${subject}&body=${body}`;
    }

    case 'phone':
      return `tel:${document.getElementById('phone-number').value.trim()}`;

    case 'vcard': {
      const name = document.getElementById('vcard-name').value.trim();
      const tel  = document.getElementById('vcard-phone').value.trim();
      const mail = document.getElementById('vcard-email').value.trim();
      const org  = document.getElementById('vcard-org').value.trim();
      const url  = document.getElementById('vcard-url').value.trim();
      return `BEGIN:VCARD\nVERSION:3.0\nFN:${name}\nTEL:${tel}\nEMAIL:${mail}\nORG:${org}\nURL:${url}\nEND:VCARD`;
    }

    case 'social': {
      const base   = document.getElementById('social-platform').value;
      const handle = document.getElementById('social-handle').value.trim();
      if (!base) return handle;
      if (base === 'whatsapp') return `https://wa.me/${handle.replace(/\D/g, '')}`;
      return base + handle.replace(/^@/, '');
    }

    default:
      return '';
  }
}

// ── Logo upload helper ────────────────────────────────────────────────────────
function setupLogoUpload(inputId, zoneId, previewRowId, imgId, nameId, removeId) {
  const input      = document.getElementById(inputId);
  const zone       = document.getElementById(zoneId);
  const previewRow = document.getElementById(previewRowId);
  const img        = document.getElementById(imgId);
  const nameEl     = document.getElementById(nameId);
  const removeBtn  = document.getElementById(removeId);

  function showPreview(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
      img.src = e.target.result;
      nameEl.textContent = file.name;
      zone.style.display = 'none';
      previewRow.classList.add('visible');
    };
    reader.readAsDataURL(file);
  }

  input.addEventListener('change', () => showPreview(input.files[0]));

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      showPreview(file);
    }
  });

  removeBtn.addEventListener('click', () => {
    input.value = '';
    img.src = '';
    nameEl.textContent = '';
    previewRow.classList.remove('visible');
    zone.style.display = '';
  });
}

setupLogoUpload('static-logo-input',  'static-upload-zone',  'static-logo-preview',  'static-logo-img',  'static-logo-name',  'static-remove-logo');
setupLogoUpload('dynamic-logo-input', 'dynamic-upload-zone', 'dynamic-logo-preview', 'dynamic-logo-img', 'dynamic-logo-name', 'dynamic-remove-logo');
setupLogoUpload('app-logo-input',     'app-upload-zone',     'app-logo-preview',     'app-logo-img',     'app-logo-name',     'app-remove-logo');

// ── Reset colors ─────────────────────────────────────────────────────────────
document.querySelectorAll('.btn-reset-colors').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById(btn.dataset.fg).value = '#000000';
    document.getElementById(btn.dataset.bg).value = '#ffffff';
    const preview = document.getElementById(btn.dataset.btn)
      ?.closest('.tab-content')?.querySelector('.qr-preview');
    if (preview?.classList.contains('has-image'))
      document.getElementById(btn.dataset.btn)?.click();
  });
});

// ── Auto-regenerate on color/style change (if a QR was already shown) ─────────
function autoRegenIfActive(btnId) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  const preview = btn.closest('.tab-content')?.querySelector('.qr-preview');
  if (preview?.classList.contains('has-image')) btn.click();
}
['static-fg','static-bg'].forEach(id =>
  document.getElementById(id)?.addEventListener('change', () => autoRegenIfActive('static-generate-btn')));
['dynamic-fg','dynamic-bg'].forEach(id =>
  document.getElementById(id)?.addEventListener('change', () => autoRegenIfActive('dynamic-generate-btn')));
['app-fg','app-bg'].forEach(id =>
  document.getElementById(id)?.addEventListener('change', () => autoRegenIfActive('app-generate-btn')));

// ── UI helpers ────────────────────────────────────────────────────────────────
function showQRPreview(previewEl, dataUrl) {
  previewEl.innerHTML = `<img src="${dataUrl}" alt="QR Code">`;
  previewEl.classList.add('has-image');
}

function setLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Generating…';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.label;
  }
}

function downloadDataUrl(dataUrl, filename) {
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = filename;
  a.click();
}

// ── Static QR ─────────────────────────────────────────────────────────────────
const staticBtn      = document.getElementById('static-generate-btn');
const staticPreview  = document.getElementById('static-preview');
const staticDownload = document.getElementById('static-download-btn');
staticBtn.dataset.label = staticBtn.textContent;

staticBtn.addEventListener('click', async () => {
  const data = buildStaticData();
  if (!data) { alert('Please fill in the required field.'); return; }

  setLoading(staticBtn, true);

  const fd = new FormData();
  fd.append('data',       data);
  fd.append('fg_color',   document.getElementById('static-fg').value);
  fd.append('bg_color',   document.getElementById('static-bg').value);
  fd.append('container_shape',  getActiveShapeStyle('static-shape-grid'));
  fd.append('container_effect', getActiveEffect('static-effect-grid'));
  fd.append('dot_style',  getActiveDotStyle('static-dot-grid'));
  fd.append('eye_style',  getActiveEyeStyle('static-eye-grid'));
  fd.append('frame_text',  document.getElementById('static-frame-text').value);
  fd.append('frame_color', document.getElementById('static-frame-color').value);
  fd.append('frame_font',  document.getElementById('static-frame-font').value);
  fd.append('edge_line',   document.getElementById('static-edge-enable').checked ? '1' : '0');
  fd.append('edge_color', document.getElementById('static-edge-color').value);
  fd.append('edge_width', document.getElementById('static-edge-width').value);
  const logoFile = document.getElementById('static-logo-input').files[0];
  if (logoFile) fd.append('logo', logoFile);

  try {
    const res  = await fetch('/api/qr/static', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) { alert(json.detail || 'Error generating QR code.'); return; }
    showQRPreview(staticPreview, json.qr_image);
    staticDownload.classList.add('visible');
    staticDownload.onclick = () => downloadDataUrl(json.qr_image, 'qrcode.png');
  } catch {
    alert('Network error. Please try again.');
  } finally {
    setLoading(staticBtn, false);
  }
});

// ── Dynamic QR ────────────────────────────────────────────────────────────────
const dynamicBtn      = document.getElementById('dynamic-generate-btn');
const dynamicPreview  = document.getElementById('dynamic-preview');
const dynamicDownload = document.getElementById('dynamic-download-btn');
const resultBox       = document.getElementById('dynamic-result-box');
dynamicBtn.dataset.label = dynamicBtn.textContent;

dynamicBtn.addEventListener('click', async () => {
  const url = document.getElementById('dynamic-url').value.trim();
  if (!url) { alert('Please enter a destination URL.'); return; }

  setLoading(dynamicBtn, true);

  const fd = new FormData();
  fd.append('destination_url', url);
  fd.append('fg_color',        document.getElementById('dynamic-fg').value);
  fd.append('bg_color',        document.getElementById('dynamic-bg').value);
  fd.append('container_shape',  getActiveShapeStyle('dynamic-shape-grid'));
  fd.append('container_effect', getActiveEffect('dynamic-effect-grid'));
  fd.append('dot_style',        getActiveDotStyle('dynamic-dot-grid'));
  fd.append('eye_style',       getActiveEyeStyle('dynamic-eye-grid'));
  fd.append('frame_text',      document.getElementById('dynamic-frame-text').value);
  fd.append('frame_color',     document.getElementById('dynamic-frame-color').value);
  fd.append('frame_font',      document.getElementById('dynamic-frame-font').value);
  fd.append('edge_line',       document.getElementById('dynamic-edge-enable').checked ? '1' : '0');
  fd.append('edge_color',      document.getElementById('dynamic-edge-color').value);
  fd.append('edge_width',      document.getElementById('dynamic-edge-width').value);
  const logoFile = document.getElementById('dynamic-logo-input').files[0];
  if (logoFile) fd.append('logo', logoFile);

  try {
    const res  = await fetch('/api/qr/dynamic', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) { alert(json.detail || 'Error generating QR code.'); return; }
    showQRPreview(dynamicPreview, json.qr_image);
    dynamicDownload.classList.add('visible');
    dynamicDownload.onclick = () => downloadDataUrl(json.qr_image, `qr-${json.short_code}.png`);
    document.getElementById('result-redirect').value = json.redirect_url;
    document.getElementById('result-manage').value   = json.manage_url;
    resultBox.classList.add('visible');
  } catch {
    alert('Network error. Please try again.');
  } finally {
    setLoading(dynamicBtn, false);
  }
});

// ── App Store QR ──────────────────────────────────────────────────────────────
const appBtn      = document.getElementById('app-generate-btn');
const appPreview  = document.getElementById('app-preview');
const appDownload = document.getElementById('app-download-btn');
const appResult   = document.getElementById('app-result-box');
appBtn.dataset.label = appBtn.textContent;

appBtn.addEventListener('click', async () => {
  const ios     = document.getElementById('app-ios-url').value.trim();
  const android = document.getElementById('app-android-url').value.trim();
  if (!ios && !android) { alert('Please enter at least one store URL.'); return; }

  setLoading(appBtn, true);

  const fd = new FormData();
  fd.append('ios_url',      ios);
  fd.append('android_url',  android);
  fd.append('fallback_url', document.getElementById('app-fallback-url').value.trim());
  fd.append('fg_color',     document.getElementById('app-fg').value);
  fd.append('bg_color',     document.getElementById('app-bg').value);
  fd.append('container_shape',  getActiveShapeStyle('app-shape-grid'));
  fd.append('container_effect', getActiveEffect('app-effect-grid'));
  fd.append('dot_style',        getActiveDotStyle('app-dot-grid'));
  fd.append('eye_style',    getActiveEyeStyle('app-eye-grid'));
  fd.append('frame_text',   document.getElementById('app-frame-text').value);
  fd.append('frame_color',  document.getElementById('app-frame-color').value);
  fd.append('frame_font',   document.getElementById('app-frame-font').value);
  fd.append('edge_line',    document.getElementById('app-edge-enable').checked ? '1' : '0');
  fd.append('edge_color',   document.getElementById('app-edge-color').value);
  fd.append('edge_width',   document.getElementById('app-edge-width').value);
  const logoFile = document.getElementById('app-logo-input').files[0];
  if (logoFile) fd.append('logo', logoFile);

  try {
    const res  = await fetch('/api/qr/app', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) { alert(json.detail || 'Error generating QR code.'); return; }
    showQRPreview(appPreview, json.qr_image);
    appDownload.classList.add('visible');
    appDownload.onclick = () => downloadDataUrl(json.qr_image, `qr-app-${json.short_code}.png`);
    document.getElementById('app-result-url').value = json.redirect_url;
    appResult.classList.add('visible');
  } catch {
    alert('Network error. Please try again.');
  } finally {
    setLoading(appBtn, false);
  }
});

// ── Copy buttons ──────────────────────────────────────────────────────────────
document.querySelectorAll('.btn-copy[data-target]').forEach(btn => {
  btn.addEventListener('click', () => {
    const val = document.getElementById(btn.dataset.target).value;
    navigator.clipboard.writeText(val).then(() => {
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';
      btn.classList.add('copied');
      setTimeout(() => { btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="13" height="13" x="9" y="9" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'; btn.classList.remove('copied'); }, 2000);
    });
  });
});
