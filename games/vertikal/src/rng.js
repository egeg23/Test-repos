// Детерминированный ГПСЧ. Один и тот же сид даёт одну и ту же последовательность
// на любом устройстве — на этом держится «общий мешок дня» и честность лидерборда.

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Сид из даты в UTC. Один и тот же для всех игроков в течение суток.
export function daySeed(ms) {
  const d = new Date(ms);
  return d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate();
}

export function dayKey(ms) {
  const d = new Date(ms);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
}

// Тасование Фишера — Йейтса на заданном ГПСЧ.
export function shuffle(arr, rnd) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Мешок: `count` бочонков из чисел 1..max без повторов.
export function drawBag(seed, count = 25, max = 90) {
  const rnd = mulberry32(seed);
  const all = Array.from({ length: max }, (_, i) => i + 1);
  return shuffle(all, rnd).slice(0, count);
}
