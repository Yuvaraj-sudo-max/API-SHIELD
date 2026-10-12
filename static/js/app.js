/**
 * app.js - Quantum Command Center Orchestrator for API Shield
 * Handles Web Audio FX, 60 FPS Oscilloscope, Interactive Topology,
 * Mission Control Salvo Dispatches, 5-Stage Decision Tracing, and Policy Studio.
 */

document.addEventListener('DOMContentLoaded', () => {
  // -------------------------------------------------------------
  // 1. INITIALIZE 3D QUANTUM SHIELD VISUALIZER
  // -------------------------------------------------------------
  let visualizer = null;
  if (typeof Shield3DVisualizer !== 'undefined') {
    visualizer = new Shield3DVisualizer('shield-3d-canvas-container');
  }

  // -------------------------------------------------------------
  // 2. SYNTHESIZED WEB AUDIO FX ENGINE
  // -------------------------------------------------------------
  let audioCtx = null;
  let soundEnabled = false;

  function initAudio() {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }

  function playTone(freq, duration = 0.08, type = 'sine', gainVal = 0.1) {
    if (!soundEnabled || !audioCtx) return;
    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(gainVal, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
      // Audio autoplay policy fallback
    }
  }

  function playAllowedSound() {
    playTone(587.33, 0.06, 'sine', 0.08); // D5
    setTimeout(() => playTone(880.00, 0.08, 'sine', 0.06), 40); // A5
  }

  function playLimitedSound() {
    playTone(340, 0.12, 'sawtooth', 0.09);
    setTimeout(() => playTone(220, 0.15, 'sawtooth', 0.08), 60);
  }

  function playBlockedSound() {
    playTone(160, 0.25, 'square', 0.12);
    setTimeout(() => playTone(120, 0.35, 'sawtooth', 0.14), 100);
  }

  const soundBtn = document.getElementById('btn-sound-toggle');
  const soundIconOn = document.getElementById('icon-sound-on');
  const soundIconOff = document.getElementById('icon-sound-off');
  const soundStateText = document.getElementById('sound-state-text');

  if (soundBtn) {
    soundBtn.addEventListener('click', () => {
      initAudio();
      soundEnabled = !soundEnabled;
      soundBtn.classList.toggle('active', soundEnabled);
      if (soundIconOn && soundIconOff) {
        soundIconOn.classList.toggle('d-none', !soundEnabled);
        soundIconOff.classList.toggle('d-none', soundEnabled);
      }
      if (soundStateText) {
        soundStateText.textContent = soundEnabled ? 'SFX: ON' : 'SFX: OFF';
      }
      if (soundEnabled) {
        playAllowedSound();
      }
    });
  }

  // -------------------------------------------------------------
  // 3. AMBIENT CYBER BACKGROUND CANVAS
  // -------------------------------------------------------------
  const bgCanvas = document.getElementById('cyber-bg-canvas');
  if (bgCanvas) {
    const bgCtx = bgCanvas.getContext('2d');
    let bgNodes = [];

    const resizeBg = () => {
      bgCanvas.width = window.innerWidth;
      bgCanvas.height = window.innerHeight;
      bgNodes = [];
      const count = Math.floor((bgCanvas.width * bgCanvas.height) / 25000);
      for (let i = 0; i < count; i++) {
        bgNodes.push({
          x: Math.random() * bgCanvas.width,
          y: Math.random() * bgCanvas.height,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
          radius: Math.random() * 1.5 + 0.5,
        });
      }
    };
    resizeBg();
    window.addEventListener('resize', resizeBg);

    const renderBg = () => {
      bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
      bgCtx.fillStyle = 'rgba(0, 242, 254, 0.4)';
      bgCtx.strokeStyle = 'rgba(0, 242, 254, 0.04)';
      bgCtx.lineWidth = 1;

      for (let i = 0; i < bgNodes.length; i++) {
        const n = bgNodes[i];
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0) n.x = bgCanvas.width;
        if (n.x > bgCanvas.width) n.x = 0;
        if (n.y < 0) n.y = bgCanvas.height;
        if (n.y > bgCanvas.height) n.y = 0;

        bgCtx.beginPath();
        bgCtx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        bgCtx.fill();

        for (let j = i + 1; j < bgNodes.length; j++) {
          const n2 = bgNodes[j];
          const dist = Math.hypot(n.x - n2.x, n.y - n2.y);
          if (dist < 120) {
            bgCtx.beginPath();
            bgCtx.moveTo(n.x, n.y);
            bgCtx.lineTo(n2.x, n2.y);
            bgCtx.stroke();
          }
        }
      }
      requestAnimationFrame(renderBg);
    };
    renderBg();
  }

  // -------------------------------------------------------------
  // 4. 60 FPS LIVE TRAFFIC OSCILLOSCOPE
  // -------------------------------------------------------------
  const oscCanvas = document.getElementById('oscilloscope-canvas');
  let oscCtx = null;
  const oscHistory = new Array(80).fill(0);
  let oscTargetSpike = 0;

  if (oscCanvas) {
    oscCtx = oscCanvas.getContext('2d');
    const resizeOsc = () => {
      oscCanvas.width = oscCanvas.parentElement.clientWidth;
      oscCanvas.height = oscCanvas.parentElement.clientHeight;
    };
    resizeOsc();
    window.addEventListener('resize', resizeOsc);

    let phase = 0;
    const renderOscilloscope = () => {
      requestAnimationFrame(renderOscilloscope);
      const w = oscCanvas.width;
      const h = oscCanvas.height;
      const mid = h / 2;

      oscCtx.fillStyle = 'rgba(6, 11, 25, 0.45)';
      oscCtx.fillRect(0, 0, w, h);

      // Cyber Grid
      oscCtx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      oscCtx.lineWidth = 1;
      for (let x = 0; x < w; x += 30) {
        oscCtx.beginPath();
        oscCtx.moveTo(x, 0);
        oscCtx.lineTo(x, h);
        oscCtx.stroke();
      }
      for (let y = 0; y < h; y += 20) {
        oscCtx.beginPath();
        oscCtx.moveTo(0, y);
        oscCtx.lineTo(w, y);
        oscCtx.stroke();
      }

      // Shift History
      oscHistory.shift();
      oscHistory.push(oscTargetSpike);
      oscTargetSpike *= 0.88; // decay

      phase += 0.05;

      // Draw Waveform
      oscCtx.beginPath();
      const step = w / (oscHistory.length - 1);
      for (let i = 0; i < oscHistory.length; i++) {
        const x = i * step;
        const val = oscHistory[i];
        // Ambient sine wave + traffic spike
        const wave = Math.sin(phase + i * 0.15) * 4;
        const y = mid - (val * (mid * 0.75)) + wave;
        if (i === 0) oscCtx.moveTo(x, y);
        else oscCtx.lineTo(x, y);
      }

      // Dynamic color based on latest value
      const latestVal = oscHistory[oscHistory.length - 1];
      let strokeStyle = '#00f2fe';
      if (latestVal > 0.85) strokeStyle = '#ff0055';
      else if (latestVal > 0.45) strokeStyle = '#ffb300';
      else if (latestVal > 0.1) strokeStyle = '#00f5a0';

      oscCtx.strokeStyle = strokeStyle;
      oscCtx.lineWidth = 2.5;
      oscCtx.shadowColor = strokeStyle;
      oscCtx.shadowBlur = 10;
      oscCtx.stroke();
      oscCtx.shadowBlur = 0;
    };
    renderOscilloscope();
  }

  function registerOscilloscopePulse(type) {
    if (type === 'BLOCKED') oscTargetSpike = 1.0;
    else if (type === 'LIMITED') oscTargetSpike = 0.75;
    else oscTargetSpike = 0.4;
  }

  // -------------------------------------------------------------
  // 5. APPLICATION STATE
  // -------------------------------------------------------------
  const state = {
    selectedMethod: 'GET',
    totalRequests: 0,
    allowedRequests: 0,
    limitedRequests: 0,
    blockedRequests: 0,
    activePolicy: null,
    policies: [],
    logs: [],
    currentLogFilter: 'ALL',
    autoBotRunning: false,
    autoBotInterval: null,
    autoBotSpeed: 1000,
  };

  // DOM Elements
  const endpointSelect = document.getElementById('endpoint-select');
  const apiKeyInput = document.getElementById('api-key-input');
  const maskedKeyPreview = document.getElementById('masked-key-preview');
  const jsonBodyInput = document.getElementById('json-body-input');
  const jsonValidBadge = document.getElementById('json-valid-badge');
  const curlDisplay = document.getElementById('curl-display');
  const btnCopyCurl = document.getElementById('btn-copy-curl');
  const curlBtnText = document.getElementById('curl-btn-text');

  // Dispatch Buttons
  const btnSendSingle = document.getElementById('btn-send-single');
  const btnSendBurst = document.getElementById('btn-send-burst');
  const btnSendAttack = document.getElementById('btn-send-attack');
  const btnGenKey = document.getElementById('btn-gen-key');
  const btnPardonClient = document.getElementById('btn-pardon-client');
  const btnResetCounters = document.getElementById('btn-reset-counters');

  // Auto Bot Elements
  const btnBotToggle = document.getElementById('btn-bot-toggle');
  const botIndicator = document.getElementById('bot-indicator');
  const botLabel = document.getElementById('bot-label');
  const speedBtns = document.querySelectorAll('.speed-btn');

  // 3D Controls
  const btnModeHolo = document.getElementById('btn-mode-holo');
  const btnModeWire = document.getElementById('btn-mode-wire');
  const btnModeQuantum = document.getElementById('btn-mode-quantum');
  const btnResetCamera = document.getElementById('btn-reset-camera');

  // Stage HUD
  const hudBarrierIntegrity = document.getElementById('hud-barrier-integrity');
  const hudActiveAlgorithm = document.getElementById('hud-active-algorithm');
  const hudDefenseState = document.getElementById('hud-defense-state');
  const hudLatency = document.getElementById('hud-latency');
  const hudDefendedRate = document.getElementById('hud-defended-rate');

  // Decision Pipeline Steps
  const pipeStep1 = document.getElementById('pipe-step-1');
  const pipeStep2 = document.getElementById('pipe-step-2');
  const pipeStep3 = document.getElementById('pipe-step-3');
  const pipeStep4 = document.getElementById('pipe-step-4');
  const pipeStep5 = document.getElementById('pipe-step-5');
  const pipeTotalTime = document.getElementById('pipeline-total-time');

  // Quota Dial & Response Card
  const dialProgressBar = document.getElementById('dial-progress-bar');
  const dialRemainingCount = document.getElementById('dial-remaining-count');
  const quotaLimitVal = document.getElementById('quota-limit-val');
  const quotaWindowVal = document.getElementById('quota-window-val');
  const quotaAlgoVal = document.getElementById('quota-algo-val');
  const quotaUsedVal = document.getElementById('quota-used-val');

  const responseStatusPill = document.getElementById('response-status-pill');
  const responseStatusText = document.getElementById('response-status-text');
  const respCodeVal = document.getElementById('resp-code-val');
  const respHdrLimit = document.getElementById('resp-hdr-limit');
  const respHdrRemaining = document.getElementById('resp-hdr-remaining');
  const respHdrRetry = document.getElementById('resp-hdr-retry');
  const respHdrRtt = document.getElementById('resp-hdr-rtt');
  const respJsonViewer = document.getElementById('resp-json-viewer');

  // Policy Grid & Modal
  const policyCardGrid = document.getElementById('policy-card-grid');
  const btnOpenCreatePolicy = document.getElementById('btn-open-create-policy');
  const modalCreatePolicy = document.getElementById('modal-create-policy');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelPolicy = document.getElementById('btn-cancel-policy');
  const formCreatePolicy = document.getElementById('form-create-policy');

  // Audit Logs
  const auditTableBody = document.getElementById('audit-table-body');
  const filterChips = document.querySelectorAll('.filter-chip');
  const btnExportLogs = document.getElementById('btn-export-logs');
  const btnClearLogs = document.getElementById('btn-clear-logs');

  // -------------------------------------------------------------
  // 6. MASKING & CURL GENERATOR HELPERS
  // -------------------------------------------------------------
  function maskKey(key) {
    if (!key) return 'Anonymous IP';
    if (key.length <= 8) return key.slice(0, 3) + '...';
    return key.slice(0, 6) + '...' + key.slice(-3);
  }

  function updateKeyMaskDisplay() {
    const key = apiKeyInput.value.trim();
    maskedKeyPreview.textContent = `MASK: ${maskKey(key)}`;
  }

  function updateCurlCommand() {
    const method = state.selectedMethod;
    const path = endpointSelect.value;
    const key = apiKeyInput.value.trim();
    const body = jsonBodyInput.value.trim();
    const clientTierSelect = document.getElementById('client-tier-select');
    const tier = clientTierSelect ? clientTierSelect.value : 'free';

    let cmd = `curl -X ${method} "http://127.0.0.1:5000${path}"`;
    if (key) {
      cmd += ` \\\n  -H "X-API-Key: ${key}"`;
    }
    if (tier && tier !== 'free') {
      cmd += ` \\\n  -H "X-Client-Tier: ${tier}"`;
    }
    if ((method === 'POST' || method === 'PUT') && body) {
      cmd += ` \\\n  -H "Content-Type: application/json" \\\n  -d '${body}'`;
    }
    curlDisplay.textContent = cmd;
  }

  // -------------------------------------------------------------
  // 7. TOPOLOGY PACKET ANIMATOR
  // -------------------------------------------------------------
  function triggerTopologyPulse(decisionType) {
    const topoClientId = document.getElementById('topo-client-id');
    const topoEndpointName = document.getElementById('topo-endpoint-name');
    const circuitFlowStatus = document.getElementById('circuit-flow-status');

    if (topoClientId) topoClientId.textContent = maskKey(apiKeyInput.value.trim());
    if (topoEndpointName) topoEndpointName.textContent = endpointSelect.value;

    if (circuitFlowStatus) {
      if (decisionType === 'ALLOWED') {
        circuitFlowStatus.textContent = 'FLOW // EGRESS 200';
        circuitFlowStatus.style.color = 'var(--neon-emerald)';
      } else if (decisionType === 'LIMITED') {
        circuitFlowStatus.textContent = 'DROPPED // 429 LIMIT';
        circuitFlowStatus.style.color = 'var(--neon-amber)';
      } else {
        circuitFlowStatus.textContent = 'BLOCKED // THREAT INTERCEPT';
        circuitFlowStatus.style.color = 'var(--neon-crimson)';
      }
    }

    const spark1 = document.getElementById('spark-1');
    const spark2 = document.getElementById('spark-2');
    const spark3 = document.getElementById('spark-3');

    [spark1, spark2, spark3].forEach((s) => s && s.classList.remove('fire'));

    if (spark1) {
      spark1.classList.add('fire');
      setTimeout(() => {
        if (spark2) spark2.classList.add('fire');
      }, 150);
      if (decisionType === 'ALLOWED') {
        setTimeout(() => {
          if (spark3) spark3.classList.add('fire');
        }, 300);
      }
    }
  }

  // -------------------------------------------------------------
  // 8. 5-STAGE DECISION PIPELINE VISUAL TRACER
  // -------------------------------------------------------------
  function resetPipeline() {
    [pipeStep1, pipeStep2, pipeStep3, pipeStep4, pipeStep5].forEach((s) => {
      if (s) {
        s.className = 'pipe-step';
        s.querySelector('.step-state').textContent = 'IDLE';
      }
    });
  }

  function setPipelineStage(stageNum, stateName, detailText, isError = false) {
    const stepEl = document.getElementById(`pipe-step-${stageNum}`);
    const detailEl = document.getElementById(`pipe-detail-${stageNum}`);
    if (!stepEl) return;

    stepEl.className = `pipe-step ${isError ? 'blocked' : 'active'}`;
    const badgeState = stepEl.querySelector('.step-state');
    if (badgeState) badgeState.textContent = stateName;
    if (detailEl && detailText) detailEl.textContent = detailText;
  }

  // -------------------------------------------------------------
  // 9. API DISPATCH ENGINE
  // -------------------------------------------------------------
  async function dispatchRequest() {
    initAudio();
    const method = state.selectedMethod;
    const endpoint = endpointSelect.value;
    const apiKey = apiKeyInput.value.trim();
    const headers = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    const clientTierSelect = document.getElementById('client-tier-select');
    const tier = clientTierSelect ? clientTierSelect.value : 'free';
    if (tier && tier !== 'free') {
      headers['X-Client-Tier'] = tier;
    }

    // Step 1: Identity Resolution
    resetPipeline();
    const startTime = performance.now();
    setPipelineStage(1, 'IDENTIFIED', `Resolved: ${maskKey(apiKey)}`);

    let bodyData = undefined;
    if (method === 'POST' || method === 'PUT') {
      try {
        bodyData = jsonBodyInput.value.trim() ? JSON.parse(jsonBodyInput.value.trim()) : {};
        headers['Content-Type'] = 'application/json';
      } catch (e) {
        bodyData = {};
      }
    }

    try {
      // Step 2: Policy Match
      setPipelineStage(2, 'MATCHING', `Endpoint: ${endpoint}`);

      // Step 3: Block Check
      setPipelineStage(3, 'VERIFYING', 'Checking abuse registry...');

      // Fire fetch
      const res = await fetch(endpoint, {
        method: method,
        headers: headers,
        body: bodyData ? JSON.stringify(bodyData) : undefined,
      });

      const rttMs = Math.round(performance.now() - startTime);
      const limitHeader = res.headers.get('X-RateLimit-Limit');
      const remainingHeader = res.headers.get('X-RateLimit-Remaining');
      const retryAfterHeader = res.headers.get('Retry-After');
      const data = await res.json().catch(() => ({}));

      // Interpret Decision
      let decisionType = 'ALLOWED';
      if (res.status === 429) {
        if (data.details && data.details.includes('temporarily blocked')) {
          decisionType = 'BLOCKED';
        } else {
          decisionType = 'LIMITED';
        }
      }

      // Step 4 & 5 Pipeline completion
      if (decisionType === 'BLOCKED') {
        setPipelineStage(3, 'BLOCKED', `Client in penalty box (${retryAfterHeader || '300'}s)`, true);
        setPipelineStage(4, 'HALTED', 'Execution dropped before counter check', true);
        setPipelineStage(5, 'EGRESS 429', 'Injected Retry-After header', true);
        playBlockedSound();
      } else if (decisionType === 'LIMITED') {
        setPipelineStage(4, 'EXCEEDED', `Quota 0/${limitHeader || '5'} reached`, true);
        setPipelineStage(5, 'EGRESS 429', 'Rate limit ceiling reached', true);
        playLimitedSound();
      } else {
        setPipelineStage(4, 'COMPUTED', `Remaining: ${remainingHeader}/${limitHeader || '10'}`);
        setPipelineStage(5, 'EGRESS 200', 'Headers injected & request passed');
        pipeStep5.classList.add('success');
        playAllowedSound();
      }

      pipeTotalTime.textContent = `COMPLETED // ${rttMs}ms`;

      // Update 3D Stage & Oscilloscope & Topology
      if (visualizer) {
        visualizer.fireRequestPulse(decisionType, { rtt: rttMs });
      }
      registerOscilloscopePulse(decisionType);
      triggerTopologyPulse(decisionType);

      // Update Response HUD & Quota Gauge
      updateResponseCard(res.status, limitHeader, remainingHeader, retryAfterHeader, rttMs, data, decisionType);
      updateQuotaGauge(limitHeader, remainingHeader);

      // Refresh Stats, Audit Logs & Redis Storage Telemetry
      fetchStats();
      fetchLogs();
      fetchRedisTelemetry();
    } catch (err) {
      console.error('Request dispatch failed:', err);
      setPipelineStage(5, 'ERROR', err.message, true);
    }
  }

  function updateResponseCard(statusCode, limit, remaining, retryAfter, rttMs, data, decisionType) {
    respCodeVal.textContent = statusCode;
    respHdrLimit.textContent = limit || '--';
    respHdrRemaining.textContent = remaining !== null ? remaining : '--';
    respHdrRetry.textContent = retryAfter ? `${retryAfter}s` : '0s';
    respHdrRtt.textContent = `${rttMs} ms`;
    hudLatency.textContent = `${rttMs} ms`;

    responseStatusPill.className = `response-status-badge ${decisionType.toLowerCase()}`;
    if (decisionType === 'ALLOWED') {
      responseStatusText.textContent = '200 OK // TRAFFIC ALLOWED';
      hudDefenseState.textContent = 'PASSED // VERIFIED';
      hudDefenseState.className = 'stat-val text-emerald';
    } else if (decisionType === 'LIMITED') {
      responseStatusText.textContent = '429 TOO MANY REQUESTS // LIMITED';
      hudDefenseState.textContent = 'RATE-LIMIT CEILING HIT';
      hudDefenseState.className = 'stat-val text-amber';
    } else {
      responseStatusText.textContent = '429 TEMPORARY CLIENT BLOCK // ACTIVE';
      hudDefenseState.textContent = 'THREAT ISOLATED // PENALTY ACTIVE';
      hudDefenseState.className = 'stat-val text-crimson';
    }

    respJsonViewer.textContent = JSON.stringify(data, null, 2);
  }

  function updateQuotaGauge(limit, remaining) {
    const l = parseInt(limit, 10);
    const r = parseInt(remaining, 10);

    if (isNaN(l) || isNaN(r)) {
      dialRemainingCount.textContent = remaining || '--';
      return;
    }

    dialRemainingCount.textContent = r;
    quotaLimitVal.textContent = l;

    const opt = endpointSelect.selectedOptions[0];
    if (opt) {
      quotaWindowVal.textContent = `${opt.dataset.window || '60'}s`;
      if (opt.dataset.algo === 'token_bucket') {
        quotaAlgoVal.textContent = 'Token Bucket (BURST/REFILL)';
        hudActiveAlgorithm.textContent = 'TOKEN BUCKET';
      } else if (opt.dataset.algo === 'sliding_window') {
        quotaAlgoVal.textContent = 'Sliding Window (ZSET)';
        hudActiveAlgorithm.textContent = 'SLIDING WINDOW';
      } else {
        quotaAlgoVal.textContent = 'Fixed Window (INCR)';
        hudActiveAlgorithm.textContent = 'FIXED WINDOW';
      }
    }

    const pct = Math.max(0, Math.min(1, r / l));
    const offset = 314 * (1 - pct);
    dialProgressBar.style.strokeDashoffset = offset;

    const usedPct = Math.round((1 - pct) * 100);
    quotaUsedVal.textContent = `${usedPct}%`;

    // Dynamic color shift
    if (pct < 0.2) {
      dialProgressBar.style.stroke = 'var(--neon-crimson)';
      hudBarrierIntegrity.textContent = '15.0% [CRITICAL]';
      hudBarrierIntegrity.className = 'stat-val text-crimson';
    } else if (pct < 0.5) {
      dialProgressBar.style.stroke = 'var(--neon-amber)';
      hudBarrierIntegrity.textContent = `${Math.round(pct * 100)}% [CONSUMED]`;
      hudBarrierIntegrity.className = 'stat-val text-amber';
    } else {
      dialProgressBar.style.stroke = 'var(--neon-cyan)';
      hudBarrierIntegrity.textContent = '100.0% [NOMINAL]';
      hudBarrierIntegrity.className = 'stat-val text-cyan';
    }
  }

  // -------------------------------------------------------------
  // 10. SALVO CONTROLS (BURST & ATTACK SIM)
  // -------------------------------------------------------------
  btnSendSingle.addEventListener('click', dispatchRequest);

  btnSendBurst.addEventListener('click', async () => {
    for (let i = 0; i < 5; i++) {
      await dispatchRequest();
      await new Promise((r) => setTimeout(r, 120));
    }
  });

  btnSendAttack.addEventListener('click', async () => {
    for (let i = 0; i < 15; i++) {
      await dispatchRequest();
      await new Promise((r) => setTimeout(r, 60));
    }
  });

  // Auto-Traffic Bot
  btnBotToggle.addEventListener('click', () => {
    state.autoBotRunning = !state.autoBotRunning;
    btnBotToggle.classList.toggle('active', state.autoBotRunning);
    botLabel.textContent = state.autoBotRunning ? 'Auto-Traffic Bot: ON' : 'Auto-Traffic Bot: OFF';

    if (state.autoBotRunning) {
      state.autoBotInterval = setInterval(dispatchRequest, state.autoBotSpeed);
    } else {
      clearInterval(state.autoBotInterval);
    }
  });

  speedBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      speedBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.autoBotSpeed = parseInt(btn.dataset.speed, 10);
      if (state.autoBotRunning) {
        clearInterval(state.autoBotInterval);
        state.autoBotInterval = setInterval(dispatchRequest, state.autoBotSpeed);
      }
    });
  });

  // Generate Key
  btnGenKey.addEventListener('click', () => {
    const rand = 'key_' + Math.random().toString(36).substring(2, 8) + '_' + Math.floor(Math.random() * 900 + 100);
    apiKeyInput.value = rand;
    updateKeyMaskDisplay();
    updateCurlCommand();
  });

  // Pardon Client
  btnPardonClient.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim();
    try {
      const res = await fetch('/api/unblock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: key }),
      });
      const data = await res.json();
      alert(`Client ${maskKey(key)} pardoned. Violation counter and temporary block reset!`);
      fetchLogs();
      fetchStats();
    } catch (e) {
      alert('Failed to pardon client: ' + e.message);
    }
  });

  // Reset Counters
  btnResetCounters.addEventListener('click', async () => {
    try {
      await fetch('/api/reset-counters', { method: 'POST' });
      alert('All Redis rate-limiting keys and counters have been reset.');
      fetchLogs();
      fetchStats();
    } catch (e) {
      alert('Failed to reset counters: ' + e.message);
    }
  });

  // Copy cURL
  btnCopyCurl.addEventListener('click', () => {
    navigator.clipboard.writeText(curlDisplay.textContent).then(() => {
      curlBtnText.textContent = 'Copied!';
      setTimeout(() => (curlBtnText.textContent = 'Copy'), 1500);
    });
  });

  // Method Selector
  const methodBtns = document.querySelectorAll('.method-btn');
  methodBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      methodBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedMethod = btn.dataset.method;
      updateCurlCommand();
    });
  });

  // Identity Presets Chips
  const identityChips = document.querySelectorAll('.identity-chip');
  identityChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      identityChips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      apiKeyInput.value = chip.dataset.key;
      updateKeyMaskDisplay();
      updateCurlCommand();
    });
  });

  apiKeyInput.addEventListener('input', () => {
    updateKeyMaskDisplay();
    updateCurlCommand();
  });

  endpointSelect.addEventListener('change', () => {
    const opt = endpointSelect.selectedOptions[0];
    if (opt && opt.dataset.method) {
      methodBtns.forEach((b) => {
        b.classList.toggle('active', b.dataset.method === opt.dataset.method);
      });
      state.selectedMethod = opt.dataset.method;
    }
    if (endpointSelect.value === '/api/ai/chat') {
      jsonBodyInput.value = JSON.stringify({ prompt: "Analyze how API Shield defends against LLM token depletion." }, null, 2);
    }
    updateCurlCommand();
  });

  jsonBodyInput.addEventListener('input', () => {
    try {
      JSON.parse(jsonBodyInput.value.trim());
      jsonValidBadge.textContent = 'VALID JSON';
      jsonValidBadge.className = 'json-status text-emerald';
    } catch (e) {
      jsonValidBadge.textContent = 'INVALID JSON';
      jsonValidBadge.className = 'json-status text-crimson';
    }
    updateCurlCommand();
  });

  // -------------------------------------------------------------
  // 11. 3D STAGE CONTROLS
  // -------------------------------------------------------------
  if (btnModeHolo && visualizer) {
    btnModeHolo.addEventListener('click', () => {
      [btnModeHolo, btnModeWire, btnModeQuantum].forEach((b) => b.classList.remove('active'));
      btnModeHolo.classList.add('active');
      visualizer.setMode('hologram');
    });
  }
  if (btnModeWire && visualizer) {
    btnModeWire.addEventListener('click', () => {
      [btnModeHolo, btnModeWire, btnModeQuantum].forEach((b) => b.classList.remove('active'));
      btnModeWire.classList.add('active');
      visualizer.setMode('wireframe');
    });
  }
  if (btnModeQuantum && visualizer) {
    btnModeQuantum.addEventListener('click', () => {
      [btnModeHolo, btnModeWire, btnModeQuantum].forEach((b) => b.classList.remove('active'));
      btnModeQuantum.classList.add('active');
      visualizer.setMode('quantum');
    });
  }
  if (btnResetCamera && visualizer) {
    btnResetCamera.addEventListener('click', () => visualizer.resetCamera());
  }

  // -------------------------------------------------------------
  // 12. POLICY MANAGEMENT STUDIO
  // -------------------------------------------------------------
  async function fetchPolicies() {
    try {
      const res = await fetch('/api/policies');
      const data = await res.json();
      state.policies = data.policies || [];
      renderPolicies();
    } catch (e) {
      console.error('Failed to load policies:', e);
    }
  }

  function renderPolicies() {
    if (!policyCardGrid) return;
    policyCardGrid.innerHTML = '';

    state.policies.forEach((p) => {
      const tile = document.createElement('div');
      tile.className = `policy-tile ${p.active ? '' : 'inactive'}`;
      tile.innerHTML = `
        <div class="tile-head">
          <div>
            <div class="tile-name">${escapeHtml(p.name)}</div>
            <div class="tile-endpoint font-mono">${escapeHtml(p.endpoint)}</div>
          </div>
          <label class="switch-wrapper" title="Toggle Active / Inactive">
            <input type="checkbox" class="switch-input policy-toggle" data-name="${escapeHtml(p.name)}" ${p.active ? 'checked' : ''}>
            <span class="switch-slider"></span>
          </label>
        </div>
        <div class="tile-metrics">
          <div class="t-m-item">
            <span class="t-m-k">LIMIT</span>
            <span class="t-m-v">${p.limit} req</span>
          </div>
          <div class="t-m-item">
            <span class="t-m-k">WINDOW</span>
            <span class="t-m-v">${p.window}s</span>
          </div>
          <div class="t-m-item">
            <span class="t-m-k">STATUS</span>
            <span class="t-m-v" style="color: ${p.active ? 'var(--neon-emerald)' : 'var(--text-muted)'}">${p.active ? 'ACTIVE' : 'MUTED'}</span>
          </div>
        </div>
        <div class="tile-footer">
          <span class="algo-badge font-mono">${p.algorithm === 'sliding_window' ? 'SLIDING LOG' : 'FIXED INCR'}</span>
          <button class="btn-delete-policy" data-name="${escapeHtml(p.name)}" title="Delete policy">
            <svg class="icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;
      policyCardGrid.appendChild(tile);
    });

    // Wire up toggles
    document.querySelectorAll('.policy-toggle').forEach((toggle) => {
      toggle.addEventListener('change', async (e) => {
        const name = e.target.dataset.name;
        const action = e.target.checked ? 'activate' : 'deactivate';
        try {
          await fetch(`/api/policies/${encodeURIComponent(name)}/${action}`, { method: 'POST' });
          fetchPolicies();
        } catch (err) {
          alert('Toggle failed: ' + err.message);
        }
      });
    });

    // Wire up delete
    document.querySelectorAll('.btn-delete-policy').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const name = btn.dataset.name;
        if (confirm(`Delete policy "${name}"?`)) {
          try {
            await fetch(`/api/policies/${encodeURIComponent(name)}`, { method: 'DELETE' });
            fetchPolicies();
          } catch (err) {
            alert('Delete failed: ' + err.message);
          }
        }
      });
    });
  }

  // Modal handlers
  if (btnOpenCreatePolicy && modalCreatePolicy) {
    btnOpenCreatePolicy.addEventListener('click', () => modalCreatePolicy.classList.add('open'));
    btnCloseModal.addEventListener('click', () => modalCreatePolicy.classList.remove('open'));
    btnCancelPolicy.addEventListener('click', () => modalCreatePolicy.classList.remove('open'));
  }

  if (formCreatePolicy) {
    formCreatePolicy.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('input-policy-name').value.trim();
      const endpoint = document.getElementById('input-policy-endpoint').value.trim();
      const limit = parseInt(document.getElementById('input-policy-limit').value, 10);
      const windowSec = parseInt(document.getElementById('input-policy-window').value, 10);
      const algorithm = document.getElementById('select-policy-algo').value;

      try {
        const res = await fetch('/api/policies', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, endpoint, limit, window: windowSec, algorithm }),
        });
        const data = await res.json();
        if (res.ok) {
          modalCreatePolicy.classList.remove('open');
          formCreatePolicy.reset();
          fetchPolicies();
        } else {
          alert('Failed: ' + (data.message || 'Unknown error'));
        }
      } catch (err) {
        alert('Failed to deploy policy: ' + err.message);
      }
    });
  }

  // -------------------------------------------------------------
  // 13. AUDIT LOGS & EVENT LEDGER
  // -------------------------------------------------------------
  async function fetchLogs() {
    try {
      const res = await fetch('/api/logs');
      const data = await res.json();
      state.logs = data.logs || [];
      renderAuditLogs();
    } catch (e) {
      console.error('Failed to load logs:', e);
    }
  }

  function renderAuditLogs() {
    if (!auditTableBody) return;
    const filter = state.currentLogFilter;
    const filtered = state.logs.filter((log) => {
      if (filter === 'ALL') return true;
      return log.status === filter;
    });

    if (filtered.length === 0) {
      auditTableBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-row">No events matching "${filter}". Trigger requests using the Mission Control above.</td>
        </tr>
      `;
      return;
    }

    auditTableBody.innerHTML = '';
    // Display newest events first
    [...filtered].reverse().forEach((log) => {
      const tr = document.createElement('tr');
      const statusClass = log.status === 'ALLOWED' ? 'allowed' : log.status === 'LIMITED' ? 'limited' : 'blocked';
      const timeStr = log.timestamp || new Date().toLocaleTimeString();

      tr.innerHTML = `
        <td>${escapeHtml(timeStr)}</td>
        <td><span class="font-mono text-cyan">${escapeHtml(log.client || '--')}</span></td>
        <td><span class="font-mono">${escapeHtml(log.endpoint || '--')}</span></td>
        <td>
          <span class="audit-status-badge ${statusClass}">
            ${escapeHtml(log.status)}
          </span>
        </td>
        <td>${log.remaining !== undefined ? log.remaining : '--'}</td>
        <td>${escapeHtml(log.reason || (log.retry_after ? `Retry in ${log.retry_after}s` : 'Standard pass'))}</td>
      `;
      auditTableBody.appendChild(tr);
    });
  }

  filterChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      filterChips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      state.currentLogFilter = chip.dataset.filter;
      renderAuditLogs();
    });
  });

  if (btnClearLogs) {
    btnClearLogs.addEventListener('click', async () => {
      try {
        await fetch('/api/logs', { method: 'DELETE' });
        state.logs = [];
        renderAuditLogs();
      } catch (e) {
        alert('Failed to clear logs');
      }
    });
  }

  if (btnExportLogs) {
    btnExportLogs.addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(state.logs, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `api-shield-audit-log-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  // -------------------------------------------------------------
  // 14. TELEMETRY STATS POLLER & AI METRICS
  // -------------------------------------------------------------
  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      if (data) {
        if (data.total_requests > 0) {
          const passRate = Math.round((data.allowed_requests / data.total_requests) * 100);
          hudDefendedRate.textContent = `${passRate}%`;
        }
        const aiModelEl = document.getElementById('hud-ai-model');
        if (aiModelEl && data.ai_provider) {
          aiModelEl.textContent = `${data.ai_provider.toUpperCase()} [${data.ai_key_masked || 'ACTIVE'}]`;
        }
        const aiKeyDisplay = document.getElementById('ai-key-display-text');
        if (aiKeyDisplay && data.ai_key_masked) {
          aiKeyDisplay.textContent = `KEY: ${data.ai_key_masked} (${(data.ai_status || 'active').toUpperCase()})`;
        }
      }
    } catch (e) {
      // Telemetry fallback
    }
  }

  // -------------------------------------------------------------
  // 14b. DEEPSEEK AI COPILOT & THREAT AUDITOR
  // -------------------------------------------------------------
  const btnRunAiThreat = document.getElementById('btn-run-ai-threat');
  const aiThreatReadout = document.getElementById('ai-threat-readout');
  if (btnRunAiThreat && aiThreatReadout) {
    btnRunAiThreat.addEventListener('click', async () => {
      aiThreatReadout.textContent = '>> Querying DeepSeek AI Threat Engine with recent traffic audit logs...';
      try {
        const res = await fetch('/api/ai/analyze-threat', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
          aiThreatReadout.textContent = `[THREAT LEVEL: ${data.threat_level}]\n` +
            `Inspected: ${data.total_inspected} reqs | Blocked/Limited: ${data.blocked_count} | Allowed: ${data.allowed_count}\n` +
            `DeepSeek Analysis:\n${data.ai_analysis}`;
        } else {
          aiThreatReadout.textContent = `Error: ${data.message || 'Threat analysis failed'}`;
        }
      } catch (err) {
        aiThreatReadout.textContent = `Connection error: ${err.message}`;
      }
    });
  }

  const btnGenAiPolicy = document.getElementById('btn-gen-ai-policy');
  const aiPolicyIntentInput = document.getElementById('ai-policy-intent-input');
  const aiPolicyReadout = document.getElementById('ai-policy-readout');
  if (btnGenAiPolicy && aiPolicyReadout) {
    btnGenAiPolicy.addEventListener('click', async () => {
      const intent = (aiPolicyIntentInput ? aiPolicyIntentInput.value.trim() : '') || 'Protect API from abuse';
      aiPolicyReadout.textContent = `>> Consulting DeepSeek AI for policy synthesis...`;
      try {
        const res = await fetch('/api/ai/generate-policy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intent }),
        });
        const data = await res.json();
        if (res.ok && data.policy) {
          const p = data.policy;
          aiPolicyReadout.textContent = `[Generated Policy: "${p.name}"]\n` +
            `Endpoint: ${p.endpoint} | Limit: ${p.limit} req / ${p.window}s | Engine: ${p.algorithm}\n` +
            `Click "+ Deploy New Policy" in Policy Studio to register or edit.`;
          const inputName = document.getElementById('input-policy-name');
          const inputEndpoint = document.getElementById('input-policy-endpoint');
          const inputLimit = document.getElementById('input-policy-limit');
          const inputWindow = document.getElementById('input-policy-window');
          const selectAlgo = document.getElementById('select-policy-algo');
          if (inputName) inputName.value = p.name || '';
          if (inputEndpoint) inputEndpoint.value = p.endpoint || '';
          if (inputLimit) inputLimit.value = p.limit || 10;
          if (inputWindow) inputWindow.value = p.window || 60;
          if (selectAlgo) selectAlgo.value = p.algorithm || 'sliding_window';
        } else {
          aiPolicyReadout.textContent = `Error: ${data.message || 'Generation failed'}`;
        }
      } catch (err) {
        aiPolicyReadout.textContent = `Connection error: ${err.message}`;
      }
    });
  }

  // -------------------------------------------------------------
  // 14c. REDIS DATA STORE & CLIENT TELEMETRY CONTROLLER
  // -------------------------------------------------------------
  let redisTelemetryState = {
    requests: [],
    keys: [],
    serverInfo: {},
    currentFilter: 'ALL',
    searchIp: '',
  };

  const rmTotalReqs = document.getElementById('rm-total-reqs');
  const rmUnknownUsers = document.getElementById('rm-unknown-users');
  const rmUsedMemory = document.getElementById('rm-used-memory');
  const rmActiveKeys = document.getElementById('rm-active-keys');
  const rmLatency = document.getElementById('rm-latency');
  const rmStatus = document.getElementById('rm-status');
  const redisTelemetryBody = document.getElementById('redis-telemetry-body');
  const redisKeysBody = document.getElementById('redis-keys-body');
  const btnProbeRedisLatency = document.getElementById('btn-probe-redis-latency');
  const btnRefreshRedisTelemetry = document.getElementById('btn-refresh-redis-telemetry');
  const btnFlushRedisRateKeys = document.getElementById('btn-flush-redis-rate-keys');
  const inputSearchRedisIp = document.getElementById('input-search-redis-ip');
  const redisFilterChips = document.querySelectorAll('[data-redis-filter]');

  async function fetchRedisTelemetry() {
    try {
      const res = await fetch('/api/redis/telemetry');
      if (!res.ok) return;
      const data = await res.json();
      redisTelemetryState.requests = data.requests || [];
      redisTelemetryState.keys = data.keys || [];
      redisTelemetryState.serverInfo = data.server_info || {};

      if (rmTotalReqs) rmTotalReqs.textContent = data.total_requests || 0;
      if (rmUnknownUsers) rmUnknownUsers.textContent = data.unknown_users_count || 0;
      if (rmUsedMemory) rmUsedMemory.textContent = data.server_info?.used_memory_human || '--';
      if (rmActiveKeys) rmActiveKeys.textContent = data.total_keys || 0;
      if (rmLatency && data.server_info?.latency_ms !== undefined) {
        rmLatency.textContent = `${data.server_info.latency_ms} ms`;
      }
      if (rmStatus) {
        rmStatus.textContent = data.server_info?.connected ? 'ONLINE' : 'OFFLINE';
        rmStatus.className = `rm-value font-mono ${data.server_info?.connected ? 'text-emerald' : 'text-crimson'}`;
      }

      renderRedisTelemetry();
      renderRedisKeys();
    } catch (err) {
      console.warn('Failed to sync Redis telemetry:', err);
    }
  }

  function renderRedisTelemetry() {
    if (!redisTelemetryBody) return;
    const filter = redisTelemetryState.currentFilter;
    const search = (redisTelemetryState.searchIp || '').toLowerCase().trim();

    let items = redisTelemetryState.requests.filter((r) => {
      if (filter === 'UNKNOWN' && !r.is_unknown_user) return false;
      if (filter === 'IDENTIFIED' && r.is_unknown_user) return false;
      if (filter === 'BLOCKED' && r.status !== 'BLOCKED') return false;
      if (search && !String(r.sender_ip || '').toLowerCase().includes(search) && !String(r.client_id || '').toLowerCase().includes(search)) {
        return false;
      }
      return true;
    });

    if (items.length === 0) {
      redisTelemetryBody.innerHTML = `
        <tr>
          <td colspan="13" class="empty-row">
            No client request telemetry matching "${filter}". Trigger test traffic from Mission Control above to view live Redis data.
          </td>
        </tr>
      `;
      return;
    }

    redisTelemetryBody.innerHTML = '';
    items.forEach((item) => {
      const tr = document.createElement('tr');
      const isUnknown = item.is_unknown_user;
      const statusClass = item.status === 'ALLOWED' ? 'allowed' : item.status === 'LIMITED' ? 'limited' : 'blocked';
      const tierClass = (item.tier || 'free').toLowerCase();

      tr.innerHTML = `
        <td>${escapeHtml(item.timestamp || '--')}</td>
        <td>
          <div style="display:flex; flex-direction:column; gap:2px;">
            <span class="font-mono text-cyan" style="font-weight:700;">${escapeHtml(item.sender_ip || '--')}</span>
            <span class="badge-user-type ${isUnknown ? 'unknown' : 'identified'}">
              ${isUnknown ? 'UNKNOWN USER' : 'IDENTIFIED'}
            </span>
          </div>
        </td>
        <td><span class="font-mono text-muted">${escapeHtml(item.receiver_ip || '127.0.0.1:5000')}</span></td>
        <td><span class="font-mono">${escapeHtml(item.client_id || '--')}</span></td>
        <td><span class="badge-tier ${tierClass}">${escapeHtml((item.tier || 'free').toUpperCase())}</span></td>
        <td><span class="font-mono">${escapeHtml(item.endpoint || '--')}</span></td>
        <td><span class="font-mono" style="font-size:0.75rem; color:#c084fc;">${escapeHtml(item.redis_key || '--')}</span></td>
        <td><span class="badge-key-type">${escapeHtml((item.redis_type || 'string').toUpperCase())}</span></td>
        <td><span class="font-mono" style="font-weight:700;">${item.remaining !== undefined ? item.remaining : '--'} / ${item.limit || '--'}</span></td>
        <td><span class="font-mono text-emerald">${item.ttl !== undefined ? item.ttl + 's' : '--'}</span></td>
        <td>
          <span class="font-mono" style="color:${item.violations > 0 ? 'var(--neon-crimson)' : 'var(--text-muted)'}">
            ${item.violations || 0} violation(s)
          </span>
        </td>
        <td>
          <span class="audit-status-badge ${statusClass}">
            ${escapeHtml(item.status || 'ALLOWED')}
          </span>
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            <button type="button" class="btn-hud-ghost mini" onclick="window.unblockClientDirect('${escapeHtml(item.client_id)}')">Unblock</button>
          </div>
        </td>
      `;
      redisTelemetryBody.appendChild(tr);
    });
  }

  function renderRedisKeys() {
    if (!redisKeysBody) return;
    const keys = redisTelemetryState.keys || [];
    if (keys.length === 0) {
      redisKeysBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-row">
            No active rate limit keys in Redis DB 0. Dispatch requests above to write keys to Redis.
          </td>
        </tr>
      `;
      return;
    }

    redisKeysBody.innerHTML = '';
    keys.forEach((k) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="font-mono text-cyan" style="font-weight:700;">${escapeHtml(k.key)}</span></td>
        <td><span class="badge-key-type" style="background:rgba(56,189,248,0.15); color:#38bdf8;">${escapeHtml((k.category || '').toUpperCase())}</span></td>
        <td><span class="badge-key-type">${escapeHtml((k.type || '').toUpperCase())}</span></td>
        <td><span class="font-mono text-emerald">${k.ttl > 0 ? k.ttl + 's' : (k.ttl === -1 ? 'NO EXPIRY' : 'EXPIRED')}</span></td>
        <td><span class="font-mono text-muted" style="font-size:0.75rem;">${escapeHtml(k.value_preview || '--')}</span></td>
        <td>
          <button type="button" class="btn-hud-ghost mini text-crimson" onclick="window.deleteRedisKeyDirect('${escapeHtml(k.key)}')">Purge</button>
        </td>
      `;
      redisKeysBody.appendChild(tr);
    });
  }

  window.unblockClientDirect = async function(clientId) {
    if (!clientId) return;
    try {
      const res = await fetch('/api/unblock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: clientId }),
      });
      alert(`Client ${clientId} unblocked. Key and violation counters cleared in Redis.`);
      fetchRedisTelemetry();
      fetchLogs();
      fetchStats();
    } catch (e) {
      alert('Error unblocking client: ' + e.message);
    }
  };

  window.deleteRedisKeyDirect = async function(keyName) {
    if (!keyName) return;
    try {
      const res = await fetch('/api/redis/delete-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: keyName }),
      });
      fetchRedisTelemetry();
    } catch (e) {
      alert('Error deleting key: ' + e.message);
    }
  };

  if (btnProbeRedisLatency) {
    btnProbeRedisLatency.addEventListener('click', async () => {
      btnProbeRedisLatency.classList.add('loading');
      try {
        const res = await fetch('/api/redis/test', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          alert(`Redis Probe Verified:\nHost: ${data.host}:${data.port}\nLatency: ${data.latency_ms} ms\nBackend: ${data.backend.toUpperCase()} [Verified OK]`);
        } else {
          alert(`Redis Probe Error: ${data.error || 'Check server connection'}`);
        }
        fetchRedisTelemetry();
      } catch (e) {
        alert('Latency probe failed: ' + e.message);
      } finally {
        btnProbeRedisLatency.classList.remove('loading');
      }
    });
  }

  if (btnRefreshRedisTelemetry) {
    btnRefreshRedisTelemetry.addEventListener('click', () => {
      fetchRedisTelemetry();
    });
  }

  if (btnFlushRedisRateKeys) {
    btnFlushRedisRateKeys.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to flush all API Shield rate limit keys from Redis DB?')) return;
      try {
        const res = await fetch('/api/redis/clear', { method: 'POST' });
        const data = await res.json();
        alert(data.message || 'Rate limit keys flushed.');
        fetchRedisTelemetry();
        fetchStats();
      } catch (e) {
        alert('Error flushing keys: ' + e.message);
      }
    });
  }

  if (inputSearchRedisIp) {
    inputSearchRedisIp.addEventListener('input', () => {
      redisTelemetryState.searchIp = inputSearchRedisIp.value;
      renderRedisTelemetry();
    });
  }

  redisFilterChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      redisFilterChips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      redisTelemetryState.currentFilter = chip.dataset.redisFilter;
      renderRedisTelemetry();
    });
  });

  // Nav Tab Pill Active State Switching
  const navTabPills = document.querySelectorAll('.nav-tab-pill');
  navTabPills.forEach((pill) => {
    pill.addEventListener('click', (e) => {
      navTabPills.forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      const targetId = pill.getAttribute('href');
      if (targetId && targetId.startsWith('#')) {
        const targetEl = document.querySelector(targetId);
        if (targetEl) {
          e.preventDefault();
          targetEl.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // -------------------------------------------------------------
  // 15. INITIAL HYDRATION
  // -------------------------------------------------------------
  const authUserStr = localStorage.getItem('api_shield_auth_user');
  const navLoginText = document.getElementById('nav-login-text');
  if (authUserStr && navLoginText) {
    try {
      const authUser = JSON.parse(authUserStr);
      if (authUser && authUser.user) {
        navLoginText.textContent = `${authUser.user.toUpperCase()} // CLEARANCE`;
      }
    } catch (e) {}
  }

  const clientTierSelect = document.getElementById('client-tier-select');
  const tierMultiplierPreview = document.getElementById('tier-multiplier-preview');
  if (clientTierSelect && tierMultiplierPreview) {
    clientTierSelect.addEventListener('change', () => {
      const val = clientTierSelect.value;
      if (val === 'enterprise') {
        tierMultiplierPreview.textContent = '10.0x QUOTA MULTIPLIER';
        tierMultiplierPreview.style.color = '#c084fc';
      } else if (val === 'pro') {
        tierMultiplierPreview.textContent = '3.0x QUOTA MULTIPLIER';
        tierMultiplierPreview.style.color = '#38bdf8';
      } else {
        tierMultiplierPreview.textContent = '1.0x BASE QUOTA';
        tierMultiplierPreview.style.color = '#34d399';
      }
      updateCurlCommand();
    });
  }

  updateKeyMaskDisplay();
  updateCurlCommand();
  fetchPolicies();
  fetchLogs();
  fetchStats();
  fetchRedisTelemetry();
  setInterval(fetchStats, 5000);
  setInterval(fetchRedisTelemetry, 4000);
});

