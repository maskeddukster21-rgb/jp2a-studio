(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);

  const el = {
    dropzone: $('dropzone'),
    dropzoneInner: $('dropzoneInner'),
    fileInput: $('fileInput'),
    thumb: $('thumb'),
    sourceHint: $('sourceHint'),
    urlInput: $('urlInput'),
    urlFetchBtn: $('urlFetchBtn'),

    widthRange: $('widthRange'),
    widthVal: $('widthVal'),
    heightToggle: $('heightToggle'),
    heightNum: $('heightNum'),

    optColors: $('optColors'),
    optFill: $('optFill'),
    optInvert: $('optInvert'),
    optBorder: $('optBorder'),
    optFlipX: $('optFlipX'),
    optFlipY: $('optFlipY'),

    optEdges: $('optEdges'),
    edgeRange: $('edgeRange'),
    edgeVal: $('edgeVal'),

    charPreset: $('charPreset'),
    customChars: $('customChars'),

    resetBtn: $('resetBtn'),

    termTitle: $('termTitle'),
    copyBtn: $('copyBtn'),
    downloadTxtBtn: $('downloadTxtBtn'),
    downloadHtmlBtn: $('downloadHtmlBtn'),
    emptyState: $('emptyState'),
    asciiOutput: $('asciiOutput'),
    busyIndicator: $('busyIndicator'),
    commandLine: $('commandLine'),
    metaLine: $('metaLine'),
    jp2aStatus: $('jp2aStatus'),
    toast: $('toast'),
  };

  const DEFAULTS = {
    width: 100, heightOn: false, height: 40,
    colors: true, fill: false, invert: false, border: false, flipx: false, flipy: false,
    edges: false, edgeThreshold: 3,
    charPreset: 'default', customChars: '',
  };

  let source = null;       // { kind: 'upload'|'url', dataUrl?: string, url?: string, label: string }
  let lastResult = null;   // last successful /api/convert payload
  let debounceTimer = null;
  let inFlightController = null;

  // ---------- toast ----------
  let toastTimer = null;
  function toast(msg, isErr = false) {
    el.toast.textContent = msg;
    el.toast.classList.toggle('err', isErr);
    el.toast.hidden = false;
    requestAnimationFrame(() => el.toast.classList.add('show'));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.toast.classList.remove('show');
      setTimeout(() => { el.toast.hidden = true; }, 200);
    }, 2600);
  }

  // ---------- health check ----------
  fetch('/api/health').then(r => r.json()).then(d => {
    el.jp2aStatus.classList.add(d.jp2a ? 'ok' : 'bad');
    el.jp2aStatus.innerHTML = `<span class="dot"></span> ${d.jp2a ? 'jp2a ready' : 'jp2a not found on PATH'}`;
  }).catch(() => {
    el.jp2aStatus.classList.add('bad');
    el.jp2aStatus.innerHTML = `<span class="dot"></span> server unreachable`;
  });

  // ---------- collecting current options ----------
  function currentOpts() {
    return {
      width: parseInt(el.widthRange.value, 10),
      height: el.heightToggle.checked ? parseInt(el.heightNum.value, 10) : null,
      colors: el.optColors.checked,
      fill: el.optColors.checked && el.optFill.checked,
      invert: el.optInvert.checked,
      border: el.optBorder.checked,
      flipx: el.optFlipX.checked,
      flipy: el.optFlipY.checked,
      edgesOnly: el.optEdges.checked,
      edgeThreshold: parseFloat(el.edgeRange.value),
      charPreset: el.charPreset.value,
      customChars: el.customChars.value,
    };
  }

  // ---------- UI <-> state wiring ----------
  function syncDisplays() {
    el.widthVal.textContent = el.widthRange.value;
    el.edgeVal.textContent = parseFloat(el.edgeRange.value).toFixed(1);
    el.heightNum.disabled = !el.heightToggle.checked;
    el.optFill.disabled = !el.optColors.checked;
    el.customChars.hidden = el.charPreset.value !== 'custom';
  }

  function scheduleConvert() {
    syncDisplays();
    if (!source) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runConvert, 160);
  }

  [
    el.widthRange, el.heightToggle, el.heightNum,
    el.optColors, el.optFill, el.optInvert, el.optBorder, el.optFlipX, el.optFlipY,
    el.optEdges, el.edgeRange, el.charPreset, el.customChars,
  ].forEach(input => {
    input.addEventListener('input', scheduleConvert);
    input.addEventListener('change', scheduleConvert);
  });

  el.resetBtn.addEventListener('click', () => {
    el.widthRange.value = DEFAULTS.width;
    el.heightToggle.checked = DEFAULTS.heightOn;
    el.heightNum.value = DEFAULTS.height;
    el.optColors.checked = DEFAULTS.colors;
    el.optFill.checked = DEFAULTS.fill;
    el.optInvert.checked = DEFAULTS.invert;
    el.optBorder.checked = DEFAULTS.border;
    el.optFlipX.checked = DEFAULTS.flipx;
    el.optFlipY.checked = DEFAULTS.flipy;
    el.optEdges.checked = DEFAULTS.edges;
    el.edgeRange.value = DEFAULTS.edgeThreshold;
    el.charPreset.value = DEFAULTS.charPreset;
    el.customChars.value = DEFAULTS.customChars;
    scheduleConvert();
  });

  // ---------- image sources ----------
  function setSourceFromFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      toast('That is not an image file.', true);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      source = { kind: 'upload', dataUrl: reader.result, label: file.name };
      el.thumb.src = reader.result;
      el.thumb.hidden = false;
      el.dropzoneInner.style.display = 'none';
      el.sourceHint.textContent = `Loaded: ${file.name}`;
      el.termTitle.textContent = file.name;
      runConvert();
    };
    reader.readAsDataURL(file);
  }

  el.dropzone.addEventListener('click', () => el.fileInput.click());
  el.dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.fileInput.click(); }
  });
  el.fileInput.addEventListener('change', () => {
    if (el.fileInput.files[0]) setSourceFromFile(el.fileInput.files[0]);
  });

  ['dragenter', 'dragover'].forEach(ev =>
    el.dropzone.addEventListener(ev, (e) => { e.preventDefault(); el.dropzone.classList.add('dragover'); }));
  ['dragleave', 'dragend', 'drop'].forEach(ev =>
    el.dropzone.addEventListener(ev, (e) => { e.preventDefault(); el.dropzone.classList.remove('dragover'); }));
  el.dropzone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) setSourceFromFile(file);
  });

  window.addEventListener('paste', (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) { setSourceFromFile(file); toast('Pasted image from clipboard.'); }
        return;
      }
    }
  });

  el.urlFetchBtn.addEventListener('click', fetchFromUrl);
  el.urlInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') fetchFromUrl(); });

  function fetchFromUrl() {
    const url = el.urlInput.value.trim();
    if (!url) return;
    source = { kind: 'url', url, label: url.split('/').pop() || url };
    el.thumb.src = url;
    el.thumb.hidden = false;
    el.thumb.onerror = () => { el.thumb.hidden = true; };
    el.dropzoneInner.style.display = 'none';
    el.sourceHint.textContent = `Fetching: ${url}`;
    el.termTitle.textContent = source.label;
    runConvert();
  }

  // ---------- conversion ----------
  async function runConvert() {
    if (!source) return;
    if (inFlightController) inFlightController.abort();
    inFlightController = new AbortController();

    el.busyIndicator.hidden = false;
    const opts = currentOpts();
    const payload = { opts };
    if (source.kind === 'upload') { payload.source = 'upload'; payload.dataUrl = source.dataUrl; }
    else { payload.source = 'url'; payload.url = source.url; }

    try {
      const res = await fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: inFlightController.signal,
      });
      const data = await res.json();
      renderResult(data);
    } catch (err) {
      if (err.name !== 'AbortError') {
        toast('Request failed: ' + err.message, true);
      }
    } finally {
      el.busyIndicator.hidden = true;
    }
  }

  function renderResult(data) {
    if (!data.ok) {
      toast(data.error || 'Conversion failed.', true);
      el.metaLine.textContent = 'error';
      return;
    }
    lastResult = data;
    el.emptyState.hidden = true;
    el.asciiOutput.hidden = false;

    if (data.mode === 'html') {
      el.asciiOutput.innerHTML = data.output;
    } else {
      const pre = document.createElement('pre');
      pre.textContent = data.output;
      el.asciiOutput.innerHTML = '';
      el.asciiOutput.appendChild(pre);
    }

    el.commandLine.textContent = '$ ' + data.command;
    const dims = data.sourceSize && data.sourceSize.width
      ? `source ${data.sourceSize.width}×${data.sourceSize.height}px`
      : '';
    el.metaLine.textContent = dims;
    el.sourceHint.textContent = source.kind === 'upload'
      ? `Loaded: ${source.label}`
      : `Fetched: ${source.label}`;
  }

  // ---------- output actions ----------
  el.copyBtn.addEventListener('click', async () => {
    if (!lastResult) return toast('Nothing to copy yet.', true);
    try {
      await navigator.clipboard.writeText(lastResult.plain_for_copy || '');
      toast('Copied to clipboard.');
    } catch {
      toast('Clipboard copy failed.', true);
    }
  });

  function download(filename, content, type) {
    const blob = new Blob([content], { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  el.downloadTxtBtn.addEventListener('click', () => {
    if (!lastResult) return toast('Nothing to download yet.', true);
    download('ascii-art.txt', lastResult.plain_for_copy || '', 'text/plain');
  });

  el.downloadHtmlBtn.addEventListener('click', () => {
    if (!lastResult) return toast('Nothing to download yet.', true);
    if (lastResult.mode !== 'html') return toast('Enable Color to export HTML.', true);
    const doc = `<!doctype html><html><head><meta charset="utf-8"><title>ascii art</title>
<style>body{background:#0a0c11;margin:24px;} .art{font-family:'JetBrains Mono',monospace;font-size:9px;line-height:1.05;display:inline-block;}</style>
</head><body><div class="art">${lastResult.output}</div></body></html>`;
    download('ascii-art.html', doc, 'text/html');
  });

  syncDisplays();
})();
