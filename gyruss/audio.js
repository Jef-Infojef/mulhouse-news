// ═══════════════════════════════════════════════════════════════
// GYRUSS HTML5 - Audio Engine
// Lecture du fichier Gyruss.sid (C64) via émulateur SID 6581 JS
// Fallback sur synthèse Web Audio si le .sid ne peut pas charger
// ═══════════════════════════════════════════════════════════════

const Audio = (() => {
  let ctx = null;
  let masterGain = null;
  let sfxGain    = null;
  let musicGain  = null;
  let muted      = false;
  let sidNode    = null;      // ScriptProcessorNode pour le SID
  let sidEngine  = null;      // instance SIDEngine
  let sidLoaded  = false;
  let currentTrack = null;

  // ── INIT ──────────────────────────────────────────────────────
  function init() {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    masterGain = ctx.createGain(); masterGain.gain.value = 0.8; masterGain.connect(ctx.destination);
    musicGain  = ctx.createGain(); musicGain.gain.value  = 0.9; musicGain.connect(masterGain);
    sfxGain    = ctx.createGain(); sfxGain.gain.value    = 0.6; sfxGain.connect(masterGain);
    // Charger le fichier SID
    loadSIDFile('Gyruss.sid');
  }

  function resume() { if (ctx && ctx.state === 'suspended') ctx.resume(); }

  // ── CHARGEMENT DU FICHIER .SID ────────────────────────────────
  function loadSIDFile(url) {
    fetch(url)
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer(); })
      .then(buf => {
        sidEngine = new SIDEngine(new Uint8Array(buf), ctx.sampleRate);
        if (sidEngine.valid) {
          sidLoaded = true;
          createSIDNode();
          console.log('[SID] Chargé :', sidEngine.title, '—', sidEngine.author);
          // Démarrer la musique si playMusic() a déjà été appelé
          if (currentTrack) {
            const songs = sidEngine.songs || 1;
            const subtune = (currentTrack === 'title') ? 0 : (songs > 1 ? 1 : 0);
            sidEngine.play(subtune);
          }
        } else {
          console.warn('[SID] Fichier invalide, fallback synthèse');
        }
      })
      .catch(e => console.warn('[SID] Impossible de charger le .sid :', e.message));
  }

  // ScriptProcessorNode qui alimente le SID sample par sample
  function createSIDNode() {
    if (sidNode) { try { sidNode.disconnect(); } catch(e){} }
    const bufSize = 4096;
    sidNode = ctx.createScriptProcessor(bufSize, 1, 1);
    sidNode.onaudioprocess = (ev) => {
      const out = ev.outputBuffer.getChannelData(0);
      if (!sidEngine || !sidEngine.playing || muted) { out.fill(0); return; }
      for (let i = 0; i < out.length; i++) {
        out[i] = sidEngine.clock() / 32767;
      }
    };
    // ScriptProcessorNode doit avoir une source connectée pour fonctionner
    const silence = ctx.createConstantSource();
    silence.offset.value = 0;
    silence.connect(sidNode);
    silence.start();
    sidNode.connect(musicGain);
    // resume le contexte si suspendu
    if (ctx.state === 'suspended') ctx.resume();
  }

  // ── SFX ───────────────────────────────────────────────────────
  function noise(startTime, duration, gainVal, dest) {
    const bufSize = Math.ceil(ctx.sampleRate * duration);
    const buf  = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1;
    const src  = ctx.createBufferSource();
    const gain = ctx.createGain();
    const filt = ctx.createBiquadFilter();
    filt.type = 'bandpass'; filt.frequency.value = 200; filt.Q.value = 1;
    src.buffer = buf;
    src.connect(filt); filt.connect(gain); gain.connect(dest);
    gain.gain.setValueAtTime(gainVal, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
    src.start(startTime); src.stop(startTime + duration);
  }

  function osc(freq, start, dur, type, g, dest) {
    const o  = ctx.createOscillator();
    const gn = ctx.createGain();
    o.type = type; o.frequency.value = freq;
    o.connect(gn); gn.connect(dest);
    gn.gain.setValueAtTime(0, start);
    gn.gain.linearRampToValueAtTime(g, start + 0.005);
    gn.gain.setValueAtTime(g, start + dur * 0.75);
    gn.gain.linearRampToValueAtTime(0, start + dur);
    o.start(start); o.stop(start + dur + 0.01);
  }

  function sfxShoot() {
    if (!ctx || muted) return;
    const t = ctx.currentTime;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = 'square';
    o.frequency.setValueAtTime(880, t);
    o.frequency.exponentialRampToValueAtTime(1760, t + 0.06);
    g.gain.setValueAtTime(0.15, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
    o.connect(g); g.connect(sfxGain);
    o.start(t); o.stop(t + 0.1);
  }

  function sfxEnemyExplode() {
    if (!ctx || muted) return;
    const t = ctx.currentTime;
    noise(t, 0.25, 0.5, sfxGain);
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(300, t);
    o.frequency.exponentialRampToValueAtTime(40, t + 0.25);
    g.gain.setValueAtTime(0.3, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
    o.connect(g); g.connect(sfxGain); o.start(t); o.stop(t + 0.28);
  }

  function sfxPlayerDeath() {
    if (!ctx || muted) return;
    const t = ctx.currentTime;
    noise(t, 0.8, 0.8, sfxGain);
    for (let i = 0; i < 3; i++) {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sawtooth';
      o.frequency.setValueAtTime(200 - i*30, t + i*0.12);
      o.frequency.exponentialRampToValueAtTime(30, t + 0.7);
      g.gain.setValueAtTime(0.25, t + i*0.12); g.gain.exponentialRampToValueAtTime(0.001, t + 0.8);
      o.connect(g); g.connect(sfxGain); o.start(t + i*0.12); o.stop(t + 0.85);
    }
  }

  function sfxEnemyShoot() {
    if (!ctx || muted) return;
    const t = ctx.currentTime;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(500, t); o.frequency.exponentialRampToValueAtTime(150, t + 0.1);
    g.gain.setValueAtTime(0.1, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
    o.connect(g); g.connect(sfxGain); o.start(t); o.stop(t + 0.15);
  }

  function sfxLevelUp() {
    if (!ctx || muted) return;
    const t = ctx.currentTime;
    [523, 659, 784, 1047].forEach((f, i) => osc(f, t + i*0.12, 0.15, 'square', 0.25, sfxGain));
    [1047,1319,1568].forEach(f => osc(f, t + 0.5, 0.35, 'square', 0.18, sfxGain));
  }

  function sfxGameOver() {
    if (!ctx || muted) return;
    const t = ctx.currentTime;
    [392,349,330,294,262,220].forEach((f,i) => osc(f, t + i*0.18, 0.2, 'square', 0.25, sfxGain));
  }

  // ── CONTRÔLE MUSIQUE ─────────────────────────────────────────
  function playMusic(trackName) {
    if (!ctx) return;
    if (currentTrack === trackName) return;
    currentTrack = trackName;
    if (sidLoaded && sidEngine) {
      // Gyruss.sid : sous-tune 0 = musique principale
      // Si plusieurs sous-tunes, 'title' = 0, 'play' = 1 (si dispo)
      const songs = sidEngine.songs || 1;
      const subtune = (trackName === 'title') ? 0 : (songs > 1 ? 1 : 0);
      sidEngine.play(subtune);
    }
  }

  function stopMusic() {
    currentTrack = null;
    if (sidEngine) sidEngine.stop();
  }

  function toggleMute() {
    muted = !muted;
    if (masterGain) masterGain.gain.value = muted ? 0 : 0.8;
    return muted;
  }

  return {
    init, resume, playMusic, stopMusic, toggleMute,
    sfxShoot, sfxEnemyExplode, sfxPlayerDeath, sfxEnemyShoot,
    sfxLevelUp, sfxGameOver,
    isMuted: () => muted
  };
})();
