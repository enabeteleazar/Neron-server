(function () {
  'use strict';

  var BAR_COUNT = 15;
  var FETCH_TIMEOUT_MS = 90000;
  var voiceState = 'idle';
  var mediaRecorder = null;
  var audioChunks = [];
  var audioStream = null;
  var waveformAnimId = null;
  var waveformBarsData = [];

  var orbBtn       = document.getElementById('orbBtn');
  var orbIcon      = document.getElementById('orbIcon');
  var statusLabel  = document.getElementById('statusLabel');
  var waveformBars = document.getElementById('waveformBars');
  var conversation = document.getElementById('conversation');
  var header       = document.getElementById('header');
  var settingsBtn  = document.getElementById('settingsBtn');
  var settingsModal = document.getElementById('settingsModal');
  var settingsClose = document.getElementById('settingsClose');
  var coreUrlInput = document.getElementById('coreUrlInput');
  var sttUrlInput  = document.getElementById('sttUrlInput');
  var saveSettings = document.getElementById('saveSettings');

  var ICON_MIC = '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>';
  var ICON_LOADER = '<line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>';
  var ICON_VOLUME = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>';

  var STATUS = {
    idle:       'Appuyer pour parler',
    listening:  'Enregistrement en cours...',
    processing: 'Neron reflechit...',
    speaking:   'Neron parle'
  };

  function setState(newState) {
    document.body.classList.remove('state-' + voiceState);
    voiceState = newState;
    document.body.classList.add('state-' + voiceState);
    statusLabel.textContent = STATUS[voiceState];
    updateOrbIcon();
    if (newState === 'listening') startWaveform();
    else stopWaveform();
  }

  function updateOrbIcon() {
    var icons = { idle: ICON_MIC, listening: ICON_MIC, processing: ICON_LOADER, speaking: ICON_VOLUME };
    orbIcon.innerHTML = icons[voiceState];
  }

  function initWaveform() {
    waveformBars.innerHTML = '';
    waveformBarsData = [];
    for (var i = 0; i < BAR_COUNT; i++) {
      var bar = document.createElement('div');
      bar.className = 'waveform-bar';
      waveformBars.appendChild(bar);
      waveformBarsData.push({ el: bar, target: 4, current: 4, phase: Math.random() * Math.PI * 2 });
    }
  }

  function startWaveform() {
    stopWaveform();
    function animate() {
      waveformBarsData.forEach(function(b, i) {
        b.phase += 0.08 + Math.random() * 0.04;
        var maxH = 8 + Math.sin(b.phase + i * 0.4) * 14 + Math.random() * 8;
        b.target = Math.max(4, maxH);
        b.current += (b.target - b.current) * 0.15;
        b.el.style.height = b.current + 'px';
      });
      waveformAnimId = requestAnimationFrame(animate);
    }
    waveformAnimId = requestAnimationFrame(animate);
  }

  function stopWaveform() {
    if (waveformAnimId) { cancelAnimationFrame(waveformAnimId); waveformAnimId = null; }
    waveformBarsData.forEach(function(b) { b.current = 4; b.el.style.height = '4px'; });
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function addMessage(type, label, text) {
    var msgEl = document.createElement('div');
    msgEl.className = 'message ' + type;
    msgEl.innerHTML = '<span class="message-label">' + label + '</span><div class="message-bubble"><p class="message-text">' + escapeHtml(text) + '</p></div>';
    conversation.appendChild(msgEl);
    conversation.scrollTop = conversation.scrollHeight;
    header.classList.add('dimmed');
  }

  function startRecording() {
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream) {
      audioStream = stream;
      var mimeTypes = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
      var mimeType = mimeTypes.find(function(m) { return MediaRecorder.isTypeSupported(m); }) || '';
      try {
        mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType: mimeType }) : new MediaRecorder(stream);
      } catch(e) {
        mediaRecorder = new MediaRecorder(stream);
      }
      audioChunks = [];
      mediaRecorder.ondataavailable = function(e) { if (e.data.size > 0) audioChunks.push(e.data); };
      mediaRecorder.start(100);
      return true;
    }).catch(function(e) {
      console.error('getUserMedia error:', e);
      return false;
    });
  }

  function stopRecording() {
    return new Promise(function(resolve) {
      if (!mediaRecorder || !audioStream) { resolve(null); return; }
      mediaRecorder.onstop = function() {
        var mimeType = mediaRecorder.mimeType || 'audio/mp4';
        var blob = new Blob(audioChunks, { type: mimeType });
        audioStream.getTracks().forEach(function(t) { t.stop(); });
        mediaRecorder = null; audioStream = null; audioChunks = [];
        resolve(blob);
      };
      mediaRecorder.stop();
    });
  }

  function withTimeout(promise, ms) {
    var timeout = new Promise(function(_, reject) {
      setTimeout(function() { reject(new Error('Timeout ' + ms / 1000 + 's')); }, ms);
    });
    return Promise.race([promise, timeout]);
  }

  function sendToSTT(blob) {
    var formData = new FormData();
    var ext = blob.type.includes('mp4') ? 'mp4' : blob.type.includes('ogg') ? 'ogg' : 'webm';
    formData.append('file', blob, 'audio.wav');
    return withTimeout(fetch('/api/stt', { method: 'POST', body: formData }), FETCH_TIMEOUT_MS)
      .then(function(response) {
        if (!response.ok) return response.json().then(function(d) { throw new Error(d.error || 'STT ' + response.status); });
        return response.json();
      })
      .then(function(data) { return (data.text || '').trim(); });
  }

  function sendToCore(text) {
    return withTimeout(fetch('/api/core', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    }), FETCH_TIMEOUT_MS)
      .then(function(response) {
        if (!response.ok) return response.json().then(function(d) { throw new Error(d.error || 'Core ' + response.status); });
        return response.json();
      })
      .then(function(data) { return (data.response || '').trim(); });
  }

  function speakText(text) {
    return new Promise(function(resolve) {
      if (!window.speechSynthesis) { resolve(); return; }
      speechSynthesis.cancel();
      var utter = new SpeechSynthesisUtterance(text);
      utter.lang = 'fr-FR';
      utter.rate = 0.95;
      utter.pitch = 0.9;
      var voices = speechSynthesis.getVoices();
      var fr = voices.find(function(v) { return v.lang.startsWith('fr'); });
      if (fr) utter.voice = fr;
      utter.onend = resolve;
      utter.onerror = resolve;
      speechSynthesis.speak(utter);
    });
  }

  function loadConfig() {
    fetch('/api/config').then(function(r) { return r.json(); }).then(function(data) {
      if (coreUrlInput) coreUrlInput.value = data.coreUrl || '';
      if (sttUrlInput) sttUrlInput.value = data.sttUrl || '';
    }).catch(function() {});
  }

  function openSettings() { loadConfig(); settingsModal.classList.add('open'); }
  function closeSettings() { settingsModal.classList.remove('open'); }

  function saveSettingsHandler() {
    var newCore = coreUrlInput.value.trim().replace(/\/$/, '');
    var newStt = sttUrlInput.value.trim().replace(/\/$/, '');
    fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ coreUrl: newCore, sttUrl: newStt })
    }).catch(function() {});
    closeSettings();
  }

  function handleOrbPress() {
    if (voiceState === 'speaking') {
      if (window.speechSynthesis) speechSynthesis.cancel();
      setState('idle');
      return;
    }
    if (voiceState === 'processing') return;

    if (voiceState === 'idle') {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        addMessage('error', 'Systeme', 'Microphone non supporte par ce navigateur.');
        return;
      }
      startRecording().then(function(started) {
        if (!started) { addMessage('error', 'Systeme', 'Acces microphone refuse.'); return; }
        setState('listening');
      });
      return;
    }

    if (voiceState === 'listening') {
      setState('processing');
      stopRecording().then(function(blob) {
        if (!blob) { addMessage('error', 'Systeme', 'Enregistrement echoue.'); setState('idle'); return; }
        return sendToSTT(blob).then(function(transcription) {
          if (!transcription) { addMessage('error', 'Systeme', 'Transcription vide.'); setState('idle'); return; }
          addMessage('user', 'Vous', transcription);
          return sendToCore(transcription).then(function(reply) {
            if (!reply) { setState('idle'); return; }
            addMessage('neron', 'Neron', reply);
            setState('speaking');
            return speakText(reply).then(function() { setState('idle'); });
          });
        });
      }).catch(function(e) {
        addMessage('error', 'Neron', e.message || 'Erreur inconnue');
        setState('idle');
      });
    }
  }

  orbBtn.addEventListener('click', handleOrbPress);
  settingsBtn.addEventListener('click', openSettings);
  settingsClose.addEventListener('click', closeSettings);
  saveSettings.addEventListener('click', saveSettingsHandler);
  settingsModal.addEventListener('click', function(e) { if (e.target === settingsModal) closeSettings(); });
  document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeSettings(); });
  [coreUrlInput, sttUrlInput].forEach(function(input) {
    if (input) input.addEventListener('keydown', function(e) { if (e.key === 'Enter') saveSettingsHandler(); });
  });

  if (window.speechSynthesis) {
    speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = function() { speechSynthesis.getVoices(); };
  }

  initWaveform();
  setState('idle');
  loadConfig();

})();
