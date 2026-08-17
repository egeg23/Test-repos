// Звук синтезируется на лету через WebAudio: ни одного аудиофайла в билде.
// Деревянный стук — короткий импульс с быстрым спадом, шелест мешка — фильтрованный шум.

let ctx = null;
let muted = false;

function ac() {
  if (!ctx) {
    const C = window.AudioContext || window.webkitAudioContext;
    if (!C) return null;
    ctx = new C();
  }
  // Браузеры держат контекст приглушённым до первого жеста пользователя.
  if (ctx.state === 'suspended') ctx.resume().catch(() => {});
  return ctx;
}

export function setMuted(v) { muted = !!v; }

// Приглушение на время рекламы. Не трогает выбор игрока в настройках:
// приостанавливаем сам аудиоконтекст и потом возвращаем как было.
export function suspend() { try { ctx && ctx.state === 'running' && ctx.suspend(); } catch {} }
export function resume()  { try { ctx && ctx.state === 'suspended' && ctx.resume(); } catch {} }
export function isMuted() { return muted; }

function tone({ freq = 220, dur = 0.12, type = 'triangle', gain = 0.25, sweep = 0 }) {
  const c = ac();
  if (!c || muted) return;
  const o = c.createOscillator();
  const g = c.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, c.currentTime);
  if (sweep) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + sweep), c.currentTime + dur);
  g.gain.setValueAtTime(gain, c.currentTime);
  g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + dur);
  o.connect(g).connect(c.destination);
  o.start();
  o.stop(c.currentTime + dur + 0.02);
}

function noise({ dur = 0.25, gain = 0.12, cutoff = 1800 }) {
  const c = ac();
  if (!c || muted) return;
  const n = Math.floor(c.sampleRate * dur);
  const buf = c.createBuffer(1, n, c.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
  const src = c.createBufferSource();
  src.buffer = buf;
  const f = c.createBiquadFilter();
  f.type = 'bandpass';
  f.frequency.value = cutoff;
  const g = c.createGain();
  g.gain.value = gain;
  src.connect(f).connect(g).connect(c.destination);
  src.start();
}

export const sfx = {
  // Бочонок выкатился из мешка: шелест плюс деревянный стук.
  roll() { noise({ dur: 0.22, gain: 0.10, cutoff: 2400 }); setTimeout(() => tone({ freq: 190, dur: 0.10, sweep: -70 }), 90); },
  place() { tone({ freq: 300, dur: 0.08, type: 'square', gain: 0.14, sweep: -110 }); },
  good()  { tone({ freq: 520, dur: 0.10, gain: 0.16 }); setTimeout(() => tone({ freq: 780, dur: 0.14, gain: 0.14 }), 80); },
  line()  { [0, 60, 120, 180, 240].forEach((d, i) => setTimeout(() => tone({ freq: 440 + i * 90, dur: 0.09, gain: 0.13 }), d)); },
  bad()   { tone({ freq: 150, dur: 0.16, type: 'sawtooth', gain: 0.10, sweep: -50 }); },
  win()   { [0, 120, 240, 420].forEach((d, i) => setTimeout(() => tone({ freq: [523, 659, 784, 1047][i], dur: 0.22, gain: 0.16 }), d)); },
  lose()  { [0, 150].forEach((d, i) => setTimeout(() => tone({ freq: [300, 200][i], dur: 0.26, type: 'triangle', gain: 0.13 }), d)); },
  tick()  { tone({ freq: 900, dur: 0.03, gain: 0.06 }); },
};
