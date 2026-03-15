// ═══════════════════════════════════════════════════════════════
// GYRUSS HTML5 - shoot'em up en perspective cylindrique
// ═══════════════════════════════════════════════════════════════

const canvas = document.getElementById('gameCanvas');
const ctx    = canvas.getContext('2d');

const SIZE   = Math.min(window.innerWidth, window.innerHeight, 600);
canvas.width  = SIZE;
canvas.height = SIZE;
const CX      = SIZE / 2;
const CY      = SIZE / 2;
const ORBIT_R = SIZE * 0.42;

// ── CLAVIER ──────────────────────────────────────────────────────
const keys = {};
window.addEventListener('keydown', e => {
  keys[e.code] = true;
  e.preventDefault();
  // Initialiser l'audio au premier appui (règle autoplay navigateurs)
  Audio.init();
  Audio.resume();
});
window.addEventListener('keyup', e => { keys[e.code] = false; });

// Bouton mute (touche M)
window.addEventListener('keydown', e => {
  if (e.code === 'KeyM') {
    Audio.init();
    const m = Audio.toggleMute();
    muteLabel = m ? 'SOUND: OFF' : 'SOUND: ON';
    muteLabelTimer = 120;
  }
});
let muteLabel = '';
let muteLabelTimer = 0;

// ── PROGRESSION PLANÉTAIRE ───────────────────────────────────────
// Gyruss original : Neptune → Uranus → Saturne → Jupiter → Mars → Terre
// 2 warps (niveaux) par planète avant d'y arriver, + 1 niveau "at planet"
const PLANETS = [
  {
    name: 'NEPTUNE', warps: 3,
    color: '#4b70dd', glow: '#6699ff',
    ring: false,
    draw(cx, cy, r) {
      // Planète bleue profond avec bandes atmosphériques
      const g = ctx.createRadialGradient(cx-r*0.3, cy-r*0.3, r*0.1, cx, cy, r);
      g.addColorStop(0, '#aac4ff'); g.addColorStop(0.5, '#4b70dd'); g.addColorStop(1, '#1a2a6c');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
      // bandes
      for (let i = 0; i < 3; i++) {
        const by = cy - r*0.3 + i*r*0.3;
        ctx.beginPath(); ctx.ellipse(cx, by, r*0.95, r*0.08, 0, 0, Math.PI*2);
        ctx.fillStyle = 'rgba(100,140,255,0.18)'; ctx.fill();
      }
    }
  },
  {
    name: 'URANUS', warps: 3,
    color: '#7de8e8', glow: '#aaffff',
    ring: true, ringColor: 'rgba(150,230,230,0.35)',
    draw(cx, cy, r) {
      const g = ctx.createRadialGradient(cx-r*0.3, cy-r*0.3, r*0.05, cx, cy, r);
      g.addColorStop(0, '#cfffff'); g.addColorStop(0.6, '#7de8e8'); g.addColorStop(1, '#2a8888');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
      // anneaux inclinés (Uranus est couchée)
      ctx.beginPath(); ctx.ellipse(cx, cy, r*1.6, r*0.18, Math.PI*0.15, 0, Math.PI*2);
      ctx.strokeStyle = 'rgba(150,230,230,0.4)'; ctx.lineWidth = 4; ctx.stroke();
    }
  },
  {
    name: 'SATURNE', warps: 3,
    color: '#e8d59a', glow: '#ffe8a0',
    ring: true, ringColor: 'rgba(220,200,120,0.5)',
    draw(cx, cy, r) {
      // Anneau derrière
      ctx.beginPath(); ctx.ellipse(cx, cy, r*2.0, r*0.22, 0, Math.PI, Math.PI*2);
      ctx.strokeStyle = 'rgba(220,190,100,0.5)'; ctx.lineWidth = 10; ctx.stroke();
      ctx.beginPath(); ctx.ellipse(cx, cy, r*1.65, r*0.18, 0, Math.PI, Math.PI*2);
      ctx.strokeStyle = 'rgba(180,150,80,0.4)'; ctx.lineWidth = 6; ctx.stroke();
      // Planète
      const g = ctx.createRadialGradient(cx-r*0.3, cy-r*0.3, r*0.05, cx, cy, r);
      g.addColorStop(0, '#fff0c0'); g.addColorStop(0.5, '#e8d59a'); g.addColorStop(1, '#8a6a20');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
      // bandes
      for (let i = 0; i < 4; i++) {
        const by = cy - r*0.5 + i*r*0.32;
        ctx.beginPath(); ctx.ellipse(cx, by, r*0.98, r*0.07, 0, 0, Math.PI*2);
        ctx.fillStyle = 'rgba(160,120,40,0.2)'; ctx.fill();
      }
      // Anneau devant
      ctx.beginPath(); ctx.ellipse(cx, cy, r*2.0, r*0.22, 0, 0, Math.PI);
      ctx.strokeStyle = 'rgba(220,190,100,0.6)'; ctx.lineWidth = 10; ctx.stroke();
      ctx.beginPath(); ctx.ellipse(cx, cy, r*1.65, r*0.18, 0, 0, Math.PI);
      ctx.strokeStyle = 'rgba(180,150,80,0.5)'; ctx.lineWidth = 6; ctx.stroke();
    }
  },
  {
    name: 'JUPITER', warps: 3,
    color: '#c88b4a', glow: '#ffaa66',
    ring: false,
    draw(cx, cy, r) {
      const g = ctx.createRadialGradient(cx-r*0.3, cy-r*0.25, r*0.1, cx, cy, r);
      g.addColorStop(0, '#ffe0b0'); g.addColorStop(0.4, '#c88b4a'); g.addColorStop(1, '#5a3010');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
      // bandes caractéristiques
      const bands = [
        {y:-0.55,h:0.12,c:'rgba(180,100,40,0.35)'},{y:-0.35,h:0.08,c:'rgba(220,160,80,0.25)'},
        {y:-0.18,h:0.14,c:'rgba(160,80,30,0.4)'}, {y: 0.05,h:0.1, c:'rgba(200,130,60,0.3)'},
        {y: 0.22,h:0.15,c:'rgba(140,70,20,0.4)'},{y: 0.45,h:0.1, c:'rgba(190,110,50,0.25)'}
      ];
      for (const b of bands) {
        ctx.beginPath(); ctx.ellipse(cx, cy+b.y*r, r*0.99, r*b.h, 0, 0, Math.PI*2);
        ctx.fillStyle = b.c; ctx.fill();
      }
      // Grande Tache Rouge
      ctx.beginPath(); ctx.ellipse(cx+r*0.25, cy+r*0.12, r*0.22, r*0.13, -0.2, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(200,60,30,0.55)'; ctx.fill();
      ctx.beginPath(); ctx.ellipse(cx+r*0.25, cy+r*0.12, r*0.14, r*0.08, -0.2, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(230,100,60,0.4)'; ctx.fill();
    }
  },
  {
    name: 'MARS', warps: 3,
    color: '#c1440e', glow: '#ff6633',
    ring: false,
    draw(cx, cy, r) {
      const g = ctx.createRadialGradient(cx-r*0.3, cy-r*0.3, r*0.05, cx, cy, r);
      g.addColorStop(0, '#ff9966'); g.addColorStop(0.5, '#c1440e'); g.addColorStop(1, '#5a1a00');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
      // Calotte polaire nord
      ctx.beginPath(); ctx.ellipse(cx, cy-r*0.72, r*0.35, r*0.15, 0, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(255,240,230,0.7)'; ctx.fill();
      // Valles Marineris
      ctx.beginPath(); ctx.ellipse(cx+r*0.1, cy+r*0.1, r*0.5, r*0.06, 0.3, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(80,20,0,0.4)'; ctx.fill();
    }
  },
  {
    name: 'TERRE', warps: 0,
    color: '#2266cc', glow: '#44aaff',
    ring: false,
    draw(cx, cy, r) {
      // Océans
      const g = ctx.createRadialGradient(cx-r*0.3, cy-r*0.3, r*0.05, cx, cy, r);
      g.addColorStop(0, '#88ccff'); g.addColorStop(0.5, '#2266cc'); g.addColorStop(1, '#001040');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
      ctx.fillStyle = g; ctx.fill();
      // Continents (formes simplifiées)
      ctx.fillStyle = 'rgba(60,140,40,0.75)';
      // Amériques
      ctx.beginPath(); ctx.ellipse(cx-r*0.35, cy-r*0.1, r*0.22, r*0.45, -0.3, 0, Math.PI*2); ctx.fill();
      // Europe-Afrique
      ctx.beginPath(); ctx.ellipse(cx+r*0.15, cy-r*0.05, r*0.18, r*0.42, 0.15, 0, Math.PI*2); ctx.fill();
      // Asie
      ctx.beginPath(); ctx.ellipse(cx+r*0.42, cy-r*0.2, r*0.28, r*0.3, -0.2, 0, Math.PI*2); ctx.fill();
      // Nuages
      ctx.fillStyle = 'rgba(255,255,255,0.25)';
      ctx.beginPath(); ctx.ellipse(cx-r*0.1, cy-r*0.5, r*0.5, r*0.12, 0.4, 0, Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.ellipse(cx+r*0.2, cy+r*0.35, r*0.4, r*0.1, -0.3, 0, Math.PI*2); ctx.fill();
      // Halo atmosphérique
      const atm = ctx.createRadialGradient(cx, cy, r*0.92, cx, cy, r*1.12);
      atm.addColorStop(0, 'rgba(100,180,255,0.35)'); atm.addColorStop(1, 'rgba(100,180,255,0)');
      ctx.beginPath(); ctx.arc(cx, cy, r*1.12, 0, Math.PI*2);
      ctx.fillStyle = atm; ctx.fill();
    }
  }
];

// ── ÉTAT GLOBAL ──────────────────────────────────────────────────
let state        = 'title';  // title | playing | dead | warp | levelup | gameover | victory
let score        = 0;
let hiScore      = 0;
let lives        = 3;
let frameCount   = 0;
let stateTimer   = 0;
let flashTimer   = 0;
let wave         = 0;   // vague dans le niveau courant
const WAVES_PER_LEVEL = 3;

// Progression planétaire
let planetIdx    = 0;   // index dans PLANETS (0=Neptune … 5=Terre)
let warpIdx      = 0;   // warp courant dans la planète (0..warps-1)
// level global = numéro affiché (calculé)
function currentPlanet() { return PLANETS[planetIdx]; }
function getLevel() { return planetIdx * 3 + warpIdx + 1; }
function levelLabel() {
  const p = currentPlanet();
  if (p.warps === 0) return `${p.name}`;
  return `${p.name} - WARP ${warpIdx + 1}/${p.warps}`;
}

// Animation warp
let warpSpeed    = 0;
let warpParticles = [];

// ── ÉTOILES FILANTES (effet tunnel profondeur) ───────────────────
// Chaque étoile a une "profondeur" z (0=très loin, 1=proche joueur)
// Plus z est grand, plus l'étoile est rapide, grande, et forme un trait long
const STAR_COUNT = 220;
const stars = [];
(function initStars() {
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push(makestar());
  }
})();

function makestar(near = false) {
  const angle = Math.random() * Math.PI * 2;
  const dist  = near ? Math.random() * SIZE * 0.1 + SIZE * 0.02
                     : Math.random() * ORBIT_R * 0.95 + SIZE * 0.01;
  return {
    x:      CX + Math.cos(angle) * dist,
    y:      CY + Math.sin(angle) * dist,
    z:      Math.random(),          // profondeur 0=loin, 1=proche
    bright: Math.random() * 0.6 + 0.4,
    color:  Math.random() < 0.15 ? '#ffeedd'   // étoiles orangées
          : Math.random() < 0.08 ? '#ddeeff'   // étoiles bleutées
          : '#ffffff'
  };
}

function updateStars() {
  for (const s of stars) {
    const dx   = s.x - CX, dy = s.y - CY;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    // Vitesse proportionnelle à z (profondeur) ET distance au centre
    const spd  = (0.3 + s.z * 2.8) * (0.4 + dist / SIZE * 1.8);
    s.x += (dx / dist) * spd;
    s.y += (dy / dist) * spd;
    // Réinitialiser si hors écran
    if (s.x < -10 || s.x > SIZE + 10 || s.y < -10 || s.y > SIZE + 10) {
      Object.assign(s, makestar(true));
    }
  }
}

function drawStars() {
  for (const s of stars) {
    const dx    = s.x - CX, dy = s.y - CY;
    const dist  = Math.sqrt(dx * dx + dy * dy) || 1;
    const speed = (0.3 + s.z * 2.8) * (0.4 + dist / SIZE * 1.8);

    // Longueur du trait proportionnelle à la vitesse (illusion de mouvement)
    const trailLen = speed * (1 + s.z * 5);
    const nx = dx / dist, ny = dy / dist;  // direction radiale

    // Rayon du point : plus grand si proche (z élevé)
    const r     = 0.4 + s.z * 1.8;
    const alpha = s.bright * (0.3 + s.z * 0.7);

    if (trailLen > 1.5) {
      // Trait filant avec dégradé
      const x0 = s.x - nx * trailLen;
      const y0 = s.y - ny * trailLen;
      const grad = ctx.createLinearGradient(x0, y0, s.x, s.y);
      grad.addColorStop(0, `rgba(255,255,255,0)`);
      grad.addColorStop(1, s.color.replace(')', `,${alpha})`).replace('rgb', 'rgba'));
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(s.x, s.y);
      ctx.strokeStyle = grad;
      ctx.lineWidth   = r;
      ctx.stroke();
    }
    // Point lumineux à la tête
    ctx.fillStyle = `rgba(255,255,255,${alpha})`;
    ctx.beginPath();
    ctx.arc(s.x, s.y, r * 0.8, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ── POUSSIÈRE COSMIQUE (profondeur additionnelle) ─────────────────
const dust = [];
(function initDust() {
  for (let i = 0; i < 60; i++) {
    dust.push({
      x:     Math.random() * SIZE,
      y:     Math.random() * SIZE,
      r:     Math.random() * 1.2 + 0.3,
      vx:    (Math.random() - 0.5) * 0.15,
      vy:    (Math.random() - 0.5) * 0.15,
      alpha: Math.random() * 0.08 + 0.02,
      hue:   Math.floor(Math.random() * 60 + 200) // bleu-violet
    });
  }
})();

function updateDust() {
  for (const d of dust) {
    d.x += d.vx; d.y += d.vy;
    if (d.x < 0) d.x = SIZE; if (d.x > SIZE) d.x = 0;
    if (d.y < 0) d.y = SIZE; if (d.y > SIZE) d.y = 0;
  }
}

function drawDust() {
  for (const d of dust) {
    ctx.fillStyle = `hsla(${d.hue},60%,80%,${d.alpha})`;
    ctx.beginPath();
    ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ── EFFETS DE PROFONDEUR POST-PROCESS ────────────────────────────

// Vignettage circulaire : assombrit les bords, concentre le regard au centre
function drawVignette() {
  const grad = ctx.createRadialGradient(CX, CY, ORBIT_R * 0.55, CX, CY, SIZE * 0.72);
  grad.addColorStop(0, 'rgba(0,0,0,0)');
  grad.addColorStop(1, 'rgba(0,0,0,0.72)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, SIZE, SIZE);
}

// Brouillard de profondeur : halo sombre autour du centre (très lointain = sombre)
function drawDepthFog() {
  const p    = currentPlanet();
  // Halo intérieur sombre (simule la profondeur du tunnel)
  const grad = ctx.createRadialGradient(CX, CY, 0, CX, CY, ORBIT_R * 0.45);
  grad.addColorStop(0, 'rgba(0,0,0,0.55)');
  grad.addColorStop(0.6, 'rgba(0,0,0,0.18)');
  grad.addColorStop(1,   'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, SIZE, SIZE);
}

// Lueur orbitale : anneau lumineux sur l'orbite du joueur
function drawOrbitGlow() {
  const p    = currentPlanet();
  const grad = ctx.createRadialGradient(CX, CY, ORBIT_R * 0.88, CX, CY, ORBIT_R * 1.12);
  grad.addColorStop(0,   'rgba(0,0,0,0)');
  grad.addColorStop(0.4, p.glow + '18');
  grad.addColorStop(0.5, p.glow + '28');
  grad.addColorStop(0.6, p.glow + '18');
  grad.addColorStop(1,   'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, SIZE, SIZE);
}

// ── GRILLE DE PERSPECTIVE (TUNNEL CYLINDRIQUE) ───────────────────
// Reproduit l'effet visuel de Gyruss : lignes radiales + cercles concentriques
// qui donnent l'illusion d'un cylindre infini vu en perspective

function drawTunnelGrid() {
  const p          = currentPlanet();
  const gridColor  = p.glow;
  const NUM_LINES  = 16;   // rayons
  const NUM_RINGS  = 6;    // cercles concentriques
  const MAX_R      = ORBIT_R * 1.05;

  // Anneaux concentriques animés (se déplacent vers l'extérieur = impression de mouvement vers joueur)
  const ringPhase = (frameCount * 0.012) % 1;
  for (let i = 0; i < NUM_RINGS; i++) {
    const t     = ((i / NUM_RINGS) + ringPhase) % 1; // 0=centre, 1=bord
    const r     = t * MAX_R;
    const alpha = t * 0.22;  // plus l'anneau est loin du centre, plus il est visible
    const lw    = t * 1.2;
    ctx.beginPath();
    ctx.arc(CX, CY, r, 0, Math.PI * 2);
    ctx.strokeStyle = gridColor + Math.floor(alpha * 255).toString(16).padStart(2, '0');
    ctx.lineWidth   = lw;
    ctx.stroke();
  }

  // Lignes radiales (du centre vers l'orbite)
  for (let i = 0; i < NUM_LINES; i++) {
    const angle  = (i / NUM_LINES) * Math.PI * 2;
    const x1     = CX + Math.cos(angle) * MAX_R * 0.04;
    const y1     = CY + Math.sin(angle) * MAX_R * 0.04;
    const x2     = CX + Math.cos(angle) * MAX_R;
    const y2     = CY + Math.sin(angle) * MAX_R;
    const grad   = ctx.createLinearGradient(x1, y1, x2, y2);
    grad.addColorStop(0,   gridColor + '00');
    grad.addColorStop(0.6, gridColor + '18');
    grad.addColorStop(1,   gridColor + '38');
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = grad;
    ctx.lineWidth   = 0.8;
    ctx.stroke();
  }

  // Orbite du joueur : cercle lumineux distinct
  ctx.beginPath();
  ctx.arc(CX, CY, ORBIT_R, 0, Math.PI * 2);
  ctx.strokeStyle = gridColor + '55';
  ctx.lineWidth   = 1.5;
  ctx.shadowColor = gridColor;
  ctx.shadowBlur  = 6;
  ctx.stroke();
  ctx.shadowBlur  = 0;
}

// ── HELPERS PERSPECTIVE ──────────────────────────────────────────
// Convertit une distance radiale (0=centre, ORBIT_R=orbite joueur)
// en facteur d'échelle pseudo-3D : petit au centre, grand à l'orbite
function perspScale(distFromCenter) {
  const t = Math.max(0, Math.min(1, distFromCenter / ORBIT_R));
  // Fonction de perspective : objet 3x plus petit au centre qu'à l'orbite
  return 0.12 + t * 0.88;
}

// Alpha selon profondeur : objets lointains (centre) plus transparents
function perspAlpha(distFromCenter) {
  const t = Math.max(0, Math.min(1, distFromCenter / ORBIT_R));
  return 0.3 + t * 0.7;
}

// ── JOUEUR ───────────────────────────────────────────────────────
const player = {
  angle:        Math.PI / 2,
  speed:        0.045,
  fireTimer:    0,
  fireCooldown: 16,
  alive:        true,
  respawnTimer: 0,
  blinking:     0,
  get x() { return CX + Math.cos(this.angle) * ORBIT_R; },
  get y() { return CY + Math.sin(this.angle) * ORBIT_R; }
};

function resetPlayer() {
  player.angle     = Math.PI / 2;
  player.alive     = true;
  player.blinking  = 120;
  player.fireTimer = 0;
}

function killPlayer() {
  if (!player.alive || player.blinking > 0) return;
  spawnExplosion(player.x, player.y, '#00ffff');
  Audio.sfxPlayerDeath();
  flashTimer = 20;
  player.alive = false;
  lives--;
  if (lives <= 0) {
    setTimeout(() => { state = 'gameover'; stateTimer = 0; Audio.sfxGameOver(); Audio.stopMusic(); }, 1200);
  } else {
    player.respawnTimer = 120;
    state = 'dead';
  }
}

function updatePlayer() {
  if (state === 'dead') {
    player.respawnTimer--;
    if (player.respawnTimer <= 0) {
      player.alive    = true;
      player.blinking = 120;
      state = 'playing';
    }
    return;
  }
  if (!player.alive) return;
  if (player.blinking > 0) player.blinking--;

  if (keys['ArrowLeft']  || keys['KeyA']) player.angle -= player.speed;
  if (keys['ArrowRight'] || keys['KeyD']) player.angle += player.speed;

  player.fireTimer--;
  if (player.fireTimer <= 0) {
    spawnPlayerBullets();
    player.fireTimer = player.fireCooldown;
  }
}

function drawShipAt(x, y, angle, scale, color) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle + Math.PI);
  ctx.scale(scale, scale);
  const s = SIZE * 0.028;

  ctx.shadowColor = color;
  ctx.shadowBlur  = 18;
  ctx.strokeStyle = color;
  ctx.fillStyle   = color;
  ctx.lineWidth   = 1.5;

  // fuselage
  ctx.beginPath();
  ctx.moveTo(0, -s * 1.5);
  ctx.lineTo(-s * 0.55, s * 0.6);
  ctx.lineTo(0, s * 0.25);
  ctx.lineTo( s * 0.55, s * 0.6);
  ctx.closePath();
  ctx.globalAlpha = 0.3; ctx.fill();
  ctx.globalAlpha = 1;   ctx.stroke();

  // aile gauche
  ctx.beginPath();
  ctx.moveTo(-s * 0.55, s * 0.6);
  ctx.lineTo(-s * 1.5,  s * 1.1);
  ctx.lineTo(-s * 0.2,  s * 0.1);
  ctx.closePath();
  ctx.globalAlpha = 0.2; ctx.fill();
  ctx.globalAlpha = 1;   ctx.stroke();

  // aile droite
  ctx.beginPath();
  ctx.moveTo( s * 0.55, s * 0.6);
  ctx.lineTo( s * 1.5,  s * 1.1);
  ctx.lineTo( s * 0.2,  s * 0.1);
  ctx.closePath();
  ctx.globalAlpha = 0.2; ctx.fill();
  ctx.globalAlpha = 1;   ctx.stroke();

  // réacteur
  ctx.shadowColor = '#ff8800';
  ctx.fillStyle   = '#ff6600';
  ctx.beginPath();
  ctx.arc(0, s * 0.45, s * 0.22, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
}

function drawPlayer() {
  if (!player.alive) return;
  if (player.blinking > 0 && Math.floor(player.blinking / 5) % 2 === 0) return;
  // drawShipAt fait rotate(angle + π), le nez est à Y=-s (haut local).
  // Pour que le nez pointe vers le centre, la direction voulue est player.angle + π.
  // Il faut donc : angle_passé + π = player.angle + π  → angle_passé = player.angle
  // Mais le nez est en Y négatif (haut), et rotate(θ) fait pointer Y- dans la direction θ - π/2.
  // Direction vers centre = player.angle + π
  // Y- pointe en θ - π/2 → on veut θ - π/2 = player.angle + π → θ = player.angle + π + π/2 = player.angle + 3π/2
  // Donc on passe angle = player.angle + 3π/2 - π = player.angle + π/2
  drawShipAt(player.x, player.y, player.angle + Math.PI / 2, 1, '#00ffff');
}

// ── BALLES JOUEUR ────────────────────────────────────────────────
const playerBullets = [];

function spawnPlayerBullets() {
  const dx  = CX - player.x, dy = CY - player.y;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const nx  = dx / len, ny = dy / len;
  const spd = SIZE * 0.013;
  const px  = -ny * SIZE * 0.013, py = nx * SIZE * 0.013; // perpendiculaire
  playerBullets.push({ x: player.x + px, y: player.y + py, vx: nx * spd, vy: ny * spd, life: 90 });
  playerBullets.push({ x: player.x - px, y: player.y - py, vx: nx * spd, vy: ny * spd, life: 90 });
  Audio.sfxShoot();
}

function updatePlayerBullets() {
  for (let i = playerBullets.length - 1; i >= 0; i--) {
    const b = playerBullets[i];
    b.x += b.vx; b.y += b.vy; b.life--;
    if (b.life <= 0) { playerBullets.splice(i, 1); continue; }
    // Supprimer la balle si elle atteint le centre (rayon de la planète)
    if (Math.hypot(b.x - CX, b.y - CY) < SIZE * 0.10) { playerBullets.splice(i, 1); continue; }
    // collision ennemis
    for (let j = enemies.length - 1; j >= 0; j--) {
      const e  = enemies[j];
      const ex = e.drawing ? e.x : e.fx;
      const ey = e.drawing ? e.y : e.fy;
      const dx = b.x - ex, dy = b.y - ey;
      const r  = SIZE * 0.025;
      if (dx * dx + dy * dy < r * r) {
        playerBullets.splice(i, 1);
        spawnExplosion(ex, ey, e.color);
        Audio.sfxEnemyExplode();
        score += 100;
        if (score > hiScore) hiScore = score;
        enemies.splice(j, 1);
        checkWaveClear();
        break;
      }
    }
  }
}

function drawPlayerBullets() {
  for (const b of playerBullets) {
    const dist  = Math.hypot(b.x - CX, b.y - CY);
    const ps    = perspScale(dist);
    const alpha = perspAlpha(dist);
    const r     = SIZE * 0.007 * ps;
    // Traînée lumineuse
    const dx = -b.vx * 3, dy = -b.vy * 3;
    const grad = ctx.createLinearGradient(b.x, b.y, b.x + dx, b.y + dy);
    grad.addColorStop(0, `rgba(170,255,255,${alpha})`);
    grad.addColorStop(1, 'rgba(0,200,255,0)');
    ctx.beginPath();
    ctx.moveTo(b.x, b.y);
    ctx.lineTo(b.x + dx, b.y + dy);
    ctx.strokeStyle = grad;
    ctx.lineWidth   = r * 2;
    ctx.stroke();
    // Point lumineux
    ctx.shadowColor = '#00ffff';
    ctx.shadowBlur  = 8 * ps;
    ctx.fillStyle   = `rgba(200,255,255,${alpha})`;
    ctx.beginPath();
    ctx.arc(b.x, b.y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.shadowBlur = 0;
}

// ── BALLES ENNEMIES ──────────────────────────────────────────────
const enemyBullets = [];

function spawnEnemyBullet(ex, ey) {
  const dx  = player.x - ex, dy = player.y - ey;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const spd = SIZE * 0.005 + getLevel() * SIZE * 0.0004;
  enemyBullets.push({ x: ex, y: ey, vx: dx / len * spd, vy: dy / len * spd, life: 120 });
  Audio.sfxEnemyShoot();
}

function updateEnemyBullets() {
  for (let i = enemyBullets.length - 1; i >= 0; i--) {
    const b = enemyBullets[i];
    b.x += b.vx; b.y += b.vy; b.life--;
    if (b.life <= 0) { enemyBullets.splice(i, 1); continue; }
    if (player.alive && player.blinking === 0) {
      const dx = b.x - player.x, dy = b.y - player.y;
      if (dx * dx + dy * dy < (SIZE * 0.028) * (SIZE * 0.028)) {
        enemyBullets.splice(i, 1);
        killPlayer();
      }
    }
  }
}

function drawEnemyBullets() {
  for (const b of enemyBullets) {
    const dist  = Math.hypot(b.x - CX, b.y - CY);
    const ps    = perspScale(dist);
    const alpha = perspAlpha(dist);
    const r     = SIZE * 0.006 * ps;
    // Traînée
    const dx = -b.vx * 3, dy = -b.vy * 3;
    const grad = ctx.createLinearGradient(b.x, b.y, b.x + dx, b.y + dy);
    grad.addColorStop(0, `rgba(255,100,50,${alpha})`);
    grad.addColorStop(1, 'rgba(255,50,0,0)');
    ctx.beginPath();
    ctx.moveTo(b.x, b.y);
    ctx.lineTo(b.x + dx, b.y + dy);
    ctx.strokeStyle = grad;
    ctx.lineWidth   = r * 2;
    ctx.stroke();
    // Point
    ctx.shadowColor = '#ff3300';
    ctx.shadowBlur  = 8 * ps;
    ctx.fillStyle   = `rgba(255,150,100,${alpha})`;
    ctx.beginPath();
    ctx.arc(b.x, b.y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.shadowBlur = 0;
}

// ── ENNEMIS ──────────────────────────────────────────────────────
const enemies = [];
const ENEMY_COLORS = ['#ff00ff', '#ffff00', '#ff8800', '#00ff88', '#ff4488'];

// types d'ennemis: 0=basique, 1=rapide, 2=lourd
function spawnWave() {
  enemies.length    = 0;
  enemyBullets.length = 0;
  playerBullets.length = 0;

  const count     = 12 + wave * 2 + (getLevel() - 1) * 4;
  const rings     = wave < 2 ? 1 : 2;
  const perRing   = Math.ceil(count / rings);
  let   idx       = 0;

  for (let r = 0; r < rings; r++) {
    const formR = SIZE * (0.18 + r * 0.10); // rayon de formation
    const n     = r < rings - 1 ? perRing : count - perRing * (rings - 1);
    for (let i = 0; i < n; i++) {
      const targetAngle = (i / n) * Math.PI * 2;
      const type        = (wave + r + i) % 3;
      const color       = ENEMY_COLORS[(r + wave) % ENEMY_COLORS.length];
      // position de formation finale
      const fx = CX + Math.cos(targetAngle) * formR;
      const fy = CY + Math.sin(targetAngle) * formR;
      enemies.push({
        // position courante (animation d'entrée en spirale)
        x: CX, y: CY,
        // position de formation
        fx, fy,
        formR, targetAngle,
        color, type,
        idx: idx++,
        // animation d'entrée
        entering:    true,
        entryT:      0,
        entryDelay:  idx * 4,    // décalage entre ennemis
        entryDur:    90,
        // état en formation
        formOscPhase: Math.random() * Math.PI * 2,
        // tir
        fireTimer:   60 + Math.floor(Math.random() * 120),
        // attaque
        attacking:   false,
        attackT:     0,
        attackDelay: 200 + Math.floor(Math.random() * 400),
        ax: 0, ay: 0,  // position attaque
        // helper: position effective pour le dessin
        get drawing() { return !this.entering; }
      });
    }
  }
}

function updateEnemies() {
  for (const e of enemies) {
    // ── ENTRÉE EN SPIRALE
    if (e.entering) {
      e.entryDelay--;
      if (e.entryDelay > 0) continue;
      e.entryT++;
      const t   = Math.min(e.entryT / e.entryDur, 1);
      const et  = t * t * (3 - 2 * t); // easeInOut
      // spirale: l'ennemi part du centre en tournant
      const spiralAngle = e.targetAngle + (1 - t) * Math.PI * 4;
      const spiralR     = et * e.formR;
      e.x = CX + Math.cos(spiralAngle) * spiralR;
      e.y = CY + Math.sin(spiralAngle) * spiralR;
      if (t >= 1) {
        e.entering = false;
        e.x = e.fx; e.y = e.fy;
      }
      continue;
    }

    // ── ATTAQUE
    if (e.attacking) {
      e.attackT++;
      const t  = e.attackT / 80;
      if (t >= 1) {
        e.attacking = false;
        e.attackT   = 0;
        e.attackDelay = 300 + Math.floor(Math.random() * 500);
        e.x = e.fx; e.y = e.fy;
      } else {
        // vol parabolique vers le joueur puis retour
        const t2   = t < 0.5 ? t * 2 : (1 - t) * 2;
        const tx   = e.fx + (e.ax - e.fx) * Math.sin(t * Math.PI);
        const ty   = e.fy + (e.ay - e.fy) * Math.sin(t * Math.PI);
        e.x = tx; e.y = ty;
      }
    } else {
      // oscillation douce en formation
      const osc = Math.sin(frameCount * 0.03 + e.formOscPhase) * SIZE * 0.008;
      e.x = e.fx + Math.cos(e.targetAngle) * osc;
      e.y = e.fy + Math.sin(e.targetAngle) * osc;

      // déclenchement attaque
      e.attackDelay--;
      if (e.attackDelay <= 0 && !e.entering) {
        e.attacking   = true;
        e.attackT     = 0;
        e.ax          = player.x;
        e.ay          = player.y;
      }
    }

    // ── TIR
    if (!e.entering) {
      e.fireTimer--;
      if (e.fireTimer <= 0) {
        spawnEnemyBullet(e.x, e.y);
        e.fireTimer = Math.max(40, 90 - getLevel() * 5) + Math.floor(Math.random() * 60);
      }
    }
  }
}

function drawEnemies() {
  // Trier par distance au centre (les plus lointains/petits d'abord = z-order correct)
  const sorted = [...enemies].sort((a, b) => {
    const da = Math.hypot(a.x - CX, a.y - CY);
    const db = Math.hypot(b.x - CX, b.y - CY);
    return da - db;
  });

  for (const e of sorted) {
    const x   = e.x, y = e.y;
    const dist = Math.hypot(x - CX, y - CY);

    // Mise à l'échelle pseudo-3D
    const ps    = perspScale(dist);
    const alpha = perspAlpha(dist);
    const r     = SIZE * 0.022 * ps;

    // Angle de rotation pour pointer vers le centre (nez en avant)
    const angle = Math.atan2(y - CY, x - CX);

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(x, y);
    ctx.rotate(angle + Math.PI); // pointe vers le centre
    ctx.shadowColor = e.color;
    ctx.shadowBlur  = 10 * ps;

    if (e.type === 0) {
      // Basique: losange orienté
      ctx.strokeStyle = e.color;
      ctx.fillStyle   = e.color + '44';
      ctx.lineWidth   = 1.5 * ps;
      ctx.beginPath();
      ctx.moveTo(0, -r * 1.4);
      ctx.lineTo(r * 0.9, 0);
      ctx.lineTo(0,  r * 1.4);
      ctx.lineTo(-r * 0.9, 0);
      ctx.closePath();
      ctx.fill(); ctx.stroke();
      // moteur
      ctx.fillStyle = e.color;
      ctx.beginPath(); ctx.arc(0, r * 0.5, r * 0.28, 0, Math.PI * 2); ctx.fill();
    } else if (e.type === 1) {
      // Rapide: triangle pointu orienté
      ctx.strokeStyle = e.color;
      ctx.fillStyle   = e.color + '44';
      ctx.lineWidth   = 1.5 * ps;
      ctx.beginPath();
      ctx.moveTo(0, -r * 1.6);
      ctx.lineTo( r * 1.1, r * 0.9);
      ctx.lineTo(-r * 1.1, r * 0.9);
      ctx.closePath();
      ctx.fill(); ctx.stroke();
      // noyau central lumineux
      ctx.fillStyle = e.color;
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.32, 0, Math.PI * 2);
      ctx.fill();
    } else {
      // Lourd: vaisseau circulaire avec détails
      ctx.strokeStyle = e.color;
      ctx.fillStyle   = e.color + '33';
      ctx.lineWidth   = 2 * ps;
      ctx.beginPath();
      ctx.arc(0, 0, r, 0, Math.PI * 2);
      ctx.fill(); ctx.stroke();
      // anneau intérieur
      ctx.lineWidth = 1 * ps;
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.58, 0, Math.PI * 2);
      ctx.stroke();
      // canons latéraux
      ctx.fillStyle = e.color;
      ctx.beginPath(); ctx.arc(-r * 0.85, 0, r * 0.22, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc( r * 0.85, 0, r * 0.22, 0, Math.PI * 2); ctx.fill();
      // noyau
      ctx.beginPath(); ctx.arc(0, 0, r * 0.28, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }
}

// ── PARTICULES / EXPLOSIONS ──────────────────────────────────────
const particles = [];

function spawnExplosion(x, y, color) {
  for (let i = 0; i < 22; i++) {
    const angle = Math.random() * Math.PI * 2;
    const spd   = Math.random() * SIZE * 0.009 + SIZE * 0.002;
    particles.push({
      x, y,
      vx:      Math.cos(angle) * spd,
      vy:      Math.sin(angle) * spd,
      life:    35 + Math.random() * 35,
      maxLife: 70,
      r:       Math.random() * SIZE * 0.009 + SIZE * 0.002,
      color
    });
  }
}

function updateParticles() {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx; p.y += p.vy;
    p.vx *= 0.92; p.vy *= 0.92;
    p.life--;
    if (p.life <= 0) particles.splice(i, 1);
  }
}

function drawParticles() {
  for (const p of particles) {
    const alpha = p.life / p.maxLife;
    ctx.globalAlpha = alpha;
    ctx.shadowColor = p.color;
    ctx.shadowBlur  = 8;
    ctx.fillStyle   = p.color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r * alpha + 0.5, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  ctx.shadowBlur  = 0;
}

// ── PLANÈTE AU CENTRE ─────────────────────────────────────────────
function drawPlanet() {
  const p   = currentPlanet();
  const r   = SIZE * 0.10;
  const cx  = CX, cy = CY;

  // Halo lumineux
  const halo = ctx.createRadialGradient(cx, cy, r * 0.8, cx, cy, r * 2.2);
  halo.addColorStop(0, p.glow + '33');
  halo.addColorStop(1, 'transparent');
  ctx.beginPath(); ctx.arc(cx, cy, r * 2.2, 0, Math.PI * 2);
  ctx.fillStyle = halo; ctx.fill();

  // Dessin de la planète
  ctx.save();
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
  p.draw(cx, cy, r);
  ctx.restore();
  // Reflet (spéculaire)
  const shine = ctx.createRadialGradient(cx - r*0.35, cy - r*0.35, r*0.02, cx - r*0.25, cy - r*0.25, r*0.55);
  shine.addColorStop(0, 'rgba(255,255,255,0.22)');
  shine.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fillStyle = shine; ctx.fill();
  // Contour glow
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = p.glow + '88'; ctx.lineWidth = 2;
  ctx.shadowColor = p.glow; ctx.shadowBlur = 18; ctx.stroke();
  ctx.shadowBlur = 0;
}

// ── ANIMATION WARP ────────────────────────────────────────────────
function initWarp() {
  warpParticles = [];
  warpSpeed     = 0;
  for (let i = 0; i < 120; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist  = Math.random() * SIZE * 0.05 + SIZE * 0.02;
    warpParticles.push({
      angle, dist,
      speed: Math.random() * 0.04 + 0.02,
      bright: Math.random(),
      r: Math.random() * 1.5 + 0.5
    });
  }
}

function updateWarp() {
  warpSpeed = Math.min(warpSpeed + 0.04, 1);
  for (const p of warpParticles) {
    p.dist += p.speed * SIZE * (0.01 + warpSpeed * 0.06);
    if (p.dist > SIZE) { p.dist = Math.random() * SIZE * 0.04; }
  }
  stateTimer--;
  if (stateTimer <= 0) afterWarp();
}

function drawWarp() {
  const p    = currentPlanet();
  const next = PLANETS[Math.min(planetIdx + (warpIdx === 0 ? 0 : 0), PLANETS.length - 1)];

  // Tunnel de lignes radiales (effet hyperespace)
  for (const wp of warpParticles) {
    const x1 = CX + Math.cos(wp.angle) * (wp.dist * 0.3);
    const y1 = CY + Math.sin(wp.angle) * (wp.dist * 0.3);
    const x2 = CX + Math.cos(wp.angle) * wp.dist;
    const y2 = CY + Math.sin(wp.angle) * wp.dist;
    const alpha = wp.bright * warpSpeed;
    ctx.beginPath();
    ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
    ctx.strokeStyle = `rgba(180,220,255,${alpha})`;
    ctx.lineWidth   = wp.r;
    ctx.stroke();
  }

  // Texte WARP
  ctx.textAlign   = 'center';
  ctx.shadowColor = '#ffffff';
  ctx.shadowBlur  = 30 * warpSpeed;
  ctx.fillStyle   = `rgba(255,255,255,${warpSpeed})`;
  ctx.font        = `bold ${SIZE * 0.11}px 'Courier New', monospace`;
  ctx.fillText('WARP!', CX, CY - SIZE * 0.06);

  // Destination
  ctx.font      = `${SIZE * 0.042}px 'Courier New', monospace`;
  ctx.fillStyle = `rgba(255,255,180,${warpSpeed})`;
  ctx.shadowColor = '#ffff88';
  ctx.fillText(`→ ${p.name}`, CX, CY + SIZE * 0.06);
  ctx.shadowBlur = 0;
}

// ── HUD ──────────────────────────────────────────────────────────
function drawHUD() {
  const p = currentPlanet();
  ctx.shadowBlur = 0;
  ctx.font       = `${SIZE * 0.034}px 'Courier New', monospace`;

  // Score
  ctx.fillStyle  = '#00ffff';
  ctx.textAlign  = 'left';
  ctx.fillText(`SCORE ${score}`, SIZE * 0.02, SIZE * 0.052);

  // Hi-Score
  ctx.fillStyle  = '#ffff00';
  ctx.textAlign  = 'center';
  ctx.fillText(`HI ${hiScore}`, CX, SIZE * 0.052);

  // Planète + warp (à droite)
  ctx.fillStyle  = p.glow;
  ctx.shadowColor = p.glow;
  ctx.shadowBlur  = 8;
  ctx.textAlign  = 'right';
  ctx.fillText(levelLabel(), SIZE * 0.98, SIZE * 0.052);
  ctx.shadowBlur = 0;

  // Vies (petits vaisseaux)
  ctx.textAlign  = 'left';
  for (let i = 0; i < lives; i++) {
    drawShipAt(SIZE * 0.025 + i * SIZE * 0.06, SIZE * 0.965, -Math.PI / 2, 0.55, '#00ffff');
  }

  // Mini carte du système solaire (progression)
  drawMiniMap();

  // Touche M = mute
  ctx.shadowBlur = 0;
  ctx.fillStyle  = Audio.isMuted() ? '#ff4444' : '#444444';
  ctx.font       = `${SIZE * 0.024}px 'Courier New', monospace`;
  ctx.textAlign  = 'right';
  ctx.fillText(Audio.isMuted() ? '🔇 M' : '🔊 M', SIZE * 0.98, SIZE * 0.985);

  // Label mute temporaire
  if (muteLabelTimer > 0) {
    ctx.globalAlpha = Math.min(1, muteLabelTimer / 30);
    ctx.fillStyle   = '#ffffff';
    ctx.font        = `${SIZE * 0.04}px 'Courier New', monospace`;
    ctx.textAlign   = 'center';
    ctx.fillText(muteLabel, CX, CY);
    ctx.globalAlpha = 1;
    muteLabelTimer--;
  }
}

// Mini carte : points de planètes en bas, avec indicateur de position
function drawMiniMap() {
  const n      = PLANETS.length;
  const y      = SIZE * 0.965;
  const startX = CX - (n - 1) * SIZE * 0.05;
  for (let i = 0; i < n; i++) {
    const px = startX + i * SIZE * 0.05 * 2 / (n - 1) * (n - 1) / 2;
    const pp = PLANETS[n - 1 - i]; // droite = Terre, gauche = Neptune
    const pi = n - 1 - i;
    const isCurrent = pi === planetIdx;
    const isPassed  = pi > planetIdx;
    ctx.beginPath();
    ctx.arc(startX + i * SIZE * 0.052, y, SIZE * 0.012, 0, Math.PI * 2);
    ctx.fillStyle = isPassed ? '#333' : (isCurrent ? pp.glow : pp.color + '88');
    if (isCurrent) {
      ctx.shadowColor = pp.glow; ctx.shadowBlur = 12;
    } else { ctx.shadowBlur = 0; }
    ctx.fill();
    ctx.shadowBlur = 0;
  }
  // Flèche indicatrice au-dessus de la planète courante
  const curX = startX + (n - 1 - planetIdx) * SIZE * 0.052;
  ctx.fillStyle = '#ffffff';
  ctx.font      = `${SIZE * 0.022}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.fillText('▲', curX, y - SIZE * 0.02);
}

// ── VÉRIFICATION FIN DE VAGUE / NIVEAU ──────────────────────────
function checkWaveClear() {
  if (enemies.length > 0) return;
  wave++;
  if (wave >= WAVES_PER_LEVEL) {
    // toutes les vagues du niveau terminées → WARP
    wave       = 0;
    const bonus = 500 + planetIdx * 300 + warpIdx * 100;
    score     += bonus;
    if (score > hiScore) hiScore = score;
    Audio.sfxLevelUp();
    Audio.stopMusic();
    // Afficher écran level clear puis lancer warp
    state      = 'levelup';
    stateTimer = 150;
  } else {
    // prochaine vague après un délai
    setTimeout(() => {
      if (state === 'playing') spawnWave();
    }, 1500);
  }
}

// ── ÉCRANS ───────────────────────────────────────────────────────
function drawTitle() {
  // Musique titre
  Audio.playMusic('title');

  // Titre
  ctx.textAlign  = 'center';
  ctx.shadowColor = '#ff00ff';
  ctx.shadowBlur  = 30;
  ctx.fillStyle   = '#ff00ff';
  ctx.font        = `bold ${SIZE * 0.16}px 'Courier New', monospace`;
  ctx.fillText('GYRUSS', CX, CY - SIZE * 0.06);

  // Sous-titre
  ctx.shadowColor = '#00ffff';
  ctx.shadowBlur  = 12;
  ctx.fillStyle   = '#00ffff';
  ctx.font        = `${SIZE * 0.04}px 'Courier New', monospace`;
  ctx.fillText('HTML5 EDITION', CX, CY + SIZE * 0.04);

  // Clignotement "APPUYER SUR ESPACE"
  if (Math.floor(frameCount / 28) % 2 === 0) {
    ctx.shadowColor = '#ffff00';
    ctx.shadowBlur  = 10;
    ctx.fillStyle   = '#ffff00';
    ctx.font        = `${SIZE * 0.038}px 'Courier New', monospace`;
    ctx.fillText('PRESS SPACE TO START', CX, CY + SIZE * 0.16);
  }

  // Contrôles
  ctx.shadowBlur = 0;
  ctx.fillStyle  = '#888888';
  ctx.font       = `${SIZE * 0.028}px 'Courier New', monospace`;
  ctx.fillText('← → : MOVE    AUTO-FIRE', CX, CY + SIZE * 0.26);

  if (keys['Space']) startGame();
}

function drawLevelUp() {
  const p     = currentPlanet();
  const bonus = 500 + planetIdx * 300 + warpIdx * 100;
  ctx.textAlign   = 'center';
  ctx.shadowColor = '#ffff00';
  ctx.shadowBlur  = 20;
  ctx.fillStyle   = '#ffff00';
  ctx.font        = `bold ${SIZE * 0.09}px 'Courier New', monospace`;
  ctx.fillText('STAGE CLEAR!', CX, CY - SIZE * 0.08);
  ctx.font        = `${SIZE * 0.042}px 'Courier New', monospace`;
  ctx.fillStyle   = p.glow;
  ctx.shadowColor = p.glow;
  ctx.shadowBlur  = 12;
  ctx.fillText(levelLabel(), CX, CY - SIZE * 0.02);
  ctx.font       = `${SIZE * 0.038}px 'Courier New', monospace`;
  ctx.fillStyle  = '#00ffff';
  ctx.shadowColor = '#00ffff';
  ctx.fillText(`+${bonus} BONUS`, CX, CY + SIZE * 0.06);
  ctx.shadowBlur = 0;
  stateTimer--;
  if (stateTimer <= 0) startWarp();
}

// Lancer l'animation de warp
function startWarp() {
  state      = 'warp';
  stateTimer = 140;
  initWarp();
}

// Après le warp : avancer dans la progression
function afterWarp() {
  warpIdx++;
  if (warpIdx >= currentPlanet().warps) {
    // On arrive à la planète : bonus supplémentaire
    warpIdx = 0;
    planetIdx++;
    if (planetIdx >= PLANETS.length) {
      // VICTOIRE ! On a atteint la Terre
      state = 'victory';
      stateTimer = 0;
      Audio.stopMusic();
      Audio.sfxLevelUp();
      return;
    }
    score += 1000 + planetIdx * 500;
    if (score > hiScore) hiScore = score;
  }
  // Lancer le prochain niveau
  state = 'playing';
  resetPlayer();
  spawnWave();
  Audio.playMusic('play');
}

function drawGameOver() {
  ctx.textAlign   = 'center';
  ctx.shadowColor = '#ff0000';
  ctx.shadowBlur  = 25;
  ctx.fillStyle   = '#ff0000';
  ctx.font        = `bold ${SIZE * 0.1}px 'Courier New', monospace`;
  ctx.fillText('GAME OVER', CX, CY - SIZE * 0.08);

  ctx.shadowColor = '#ffff00';
  ctx.fillStyle   = '#ffff00';
  ctx.font        = `${SIZE * 0.045}px 'Courier New', monospace`;
  ctx.fillText(`SCORE: ${score}`, CX, CY + SIZE * 0.04);

  ctx.shadowColor = '#00ffff';
  ctx.fillStyle   = '#00ffff';
  ctx.font        = `${SIZE * 0.038}px 'Courier New', monospace`;
  ctx.fillText(`HI-SCORE: ${hiScore}`, CX, CY + SIZE * 0.10);

  // Progression atteinte
  ctx.shadowColor = PLANETS[planetIdx] ? PLANETS[planetIdx].glow : '#ffffff';
  ctx.fillStyle   = ctx.shadowColor;
  ctx.font        = `${SIZE * 0.032}px 'Courier New', monospace`;
  ctx.fillText(`REACHED: ${levelLabel()}`, CX, CY + SIZE * 0.17);

  if (Math.floor(frameCount / 28) % 2 === 0) {
    ctx.shadowColor = '#ffffff';
    ctx.fillStyle   = '#ffffff';
    ctx.font        = `${SIZE * 0.035}px 'Courier New', monospace`;
    ctx.fillText('PRESS SPACE TO RESTART', CX, CY + SIZE * 0.26);
  }
  ctx.shadowBlur = 0;
  if (keys['Space']) startGame();
}

function drawVictory() {
  stateTimer++;
  // Fond arc-en-ciel pulsant
  const hue = (stateTimer * 2) % 360;
  ctx.fillStyle = `hsla(${hue},80%,20%,0.05)`;
  ctx.fillRect(0, 0, SIZE, SIZE);

  ctx.textAlign = 'center';
  // Titre
  ctx.shadowColor = '#44ffaa';
  ctx.shadowBlur  = 30 + Math.sin(stateTimer * 0.1) * 15;
  ctx.fillStyle   = '#44ffaa';
  ctx.font        = `bold ${SIZE * 0.09}px 'Courier New', monospace`;
  ctx.fillText('MISSION', CX, CY - SIZE * 0.18);
  ctx.fillStyle   = '#ffff44';
  ctx.shadowColor = '#ffff44';
  ctx.font        = `bold ${SIZE * 0.12}px 'Courier New', monospace`;
  ctx.fillText('COMPLETE!', CX, CY - SIZE * 0.06);

  // Planète Terre au centre
  PLANETS[5].draw(CX, CY + SIZE * 0.06, SIZE * 0.12);

  ctx.font      = `${SIZE * 0.036}px 'Courier New', monospace`;
  ctx.fillStyle = '#00ffff';
  ctx.shadowColor = '#00ffff';
  ctx.shadowBlur  = 10;
  ctx.fillText(`SCORE FINAL: ${score}`, CX, CY + SIZE * 0.26);
  ctx.fillStyle = '#ffff00';
  ctx.fillText(`HI-SCORE: ${hiScore}`, CX, CY + SIZE * 0.33);

  if (Math.floor(frameCount / 28) % 2 === 0) {
    ctx.shadowColor = '#ffffff';
    ctx.shadowBlur  = 8;
    ctx.fillStyle   = '#ffffff';
    ctx.font        = `${SIZE * 0.032}px 'Courier New', monospace`;
    ctx.fillText('PRESS SPACE TO PLAY AGAIN', CX, CY + SIZE * 0.43);
  }
  ctx.shadowBlur = 0;
  if (keys['Space']) startGame();
}

// ── GESTION NIVEAUX ──────────────────────────────────────────────
function startGame() {
  score      = 0;
  lives      = 3;
  wave       = 0;
  planetIdx  = 0;
  warpIdx    = 0;
  state      = 'playing';
  stateTimer = 0;
  resetPlayer();
  spawnWave();
  Audio.playMusic('play');
}

// ── FLASH ÉCRAN ──────────────────────────────────────────────────
function drawFlash() {
  if (flashTimer <= 0) return;
  ctx.globalAlpha = flashTimer / 20 * 0.5;
  ctx.fillStyle   = '#ffffff';
  ctx.fillRect(0, 0, SIZE, SIZE);
  ctx.globalAlpha = 1;
  flashTimer--;
}

// ── BOUCLE PRINCIPALE ────────────────────────────────────────────
function gameLoop() {
  frameCount++;

  // Fond
  ctx.fillStyle = 'rgba(0,0,0,0.88)';
  ctx.fillRect(0, 0, SIZE, SIZE);

  updateStars();
  drawStars();

  if (state === 'title') {
    drawTitle();
    requestAnimationFrame(gameLoop);
    return;
  }

  if (state === 'gameover') {
    drawGameOver();
    requestAnimationFrame(gameLoop);
    return;
  }

  if (state === 'victory') {
    drawVictory();
    requestAnimationFrame(gameLoop);
    return;
  }

  if (state === 'warp') {
    updateWarp();
    drawWarp();
    requestAnimationFrame(gameLoop);
    return;
  }

  if (state === 'levelup') {
    drawPlanet();
    drawHUD();
    drawLevelUp();
    requestAnimationFrame(gameLoop);
    return;
  }

  // ── PLAYING / DEAD
  updatePlayer();
  updatePlayerBullets();
  updateEnemyBullets();
  if (state === 'playing') updateEnemies();
  updateParticles();
  updateDust();

  // Ordre de rendu : fond → profondeur → objets → effets post → HUD
  drawDust();          // 1. poussière cosmique (derrière tout)
  drawTunnelGrid();    // 2. grille perspective
  drawDepthFog();      // 3. brouillard de profondeur (assombrit le centre)
  drawPlanet();        // 4. planète centrale
  drawEnemies();       // 5. ennemis (triés par z)
  drawParticles();     // 6. explosions
  drawPlayerBullets(); // 7. balles joueur
  drawEnemyBullets();  // 8. balles ennemies
  drawOrbitGlow();     // 9. lueur orbitale (sur l'orbite du joueur)
  drawPlayer();        // 10. joueur (toujours au premier plan)
  drawVignette();      // 11. vignettage (assombrit les bords)
  drawFlash();         // 12. flash mort
  drawHUD();           // 13. interface

  requestAnimationFrame(gameLoop);
}

// ── DÉMARRAGE ────────────────────────────────────────────────────
gameLoop();
