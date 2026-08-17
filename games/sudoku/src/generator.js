// Генератор задач.
//
// Две гарантии, которые мы даём и закрываем тестами:
//   1) решение единственно — иначе задача не судоку, а угадайка;
//   2) заявленная сложность настоящая: она равна самой сложной технике,
//      без которой задача не решается. В каталоге «сложные» задачи сплошь
//      и рядом закрываются одними одиночками — мы так не делаем.

import { makeBoard, specKey } from './units.js';
import { countSolutions, fullGrid } from './solver.js';
import { grade } from './techniques.js';

// Полосы сложности по максимальной необходимой технике.
export const BANDS = [
  { key: 'easy',   name: 'Лёгкая',        levels: [1, 1] },
  { key: 'light',  name: 'Простая',       levels: [2, 2] },
  { key: 'medium', name: 'Средняя',       levels: [3, 3] },
  { key: 'hard',   name: 'Сложная',       levels: [4, 5] },
  { key: 'expert', name: 'Очень сложная', levels: [6, 6] },
];

export const bandOf = (level) =>
  BANDS.find((x) => level >= x.levels[0] && level <= x.levels[1]) || null;

const shuffled = (arr, rnd) => {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};

// Симметрия расположения подсказок. Ось эстетическая, но настоящая: газетное
// судоку почти всегда симметрично, и на глаз это читается как «сделано
// человеком». Плата честная — симметрия не даёт снять столько же подсказок.
export const SYMMETRIES = [
  { key: 'none',       name: 'Свободная',       map: null },
  { key: 'central',    name: 'Центральная',     map: (n, r, q) => [n - 1 - r, n - 1 - q] },
  { key: 'horizontal', name: 'Горизонтальная',  map: (n, r, q) => [n - 1 - r, q] },
  { key: 'vertical',   name: 'Вертикальная',    map: (n, r, q) => [r, n - 1 - q] },
  { key: 'diagonal',   name: 'Диагональная',    map: (n, r, q) => [q, r] },
];

/** Орбиты клеток: что снимается одним куском, чтобы узор остался симметричным. */
function orbits(n, symKey) {
  const sym = SYMMETRIES.find((x) => x.key === symKey);
  if (!sym) throw new Error('неизвестная симметрия: ' + symKey);
  if (!sym.map) return [...Array(n * n).keys()].map((c) => [c]);
  const seen = new Set(), out = [];
  for (let c = 0; c < n * n; c++) {
    if (seen.has(c)) continue;
    const [r2, q2] = sym.map(n, Math.floor(c / n), c % n);
    const pair = r2 * n + q2;
    const orbit = pair === c ? [c] : [c, pair];
    orbit.forEach((x) => seen.add(x));
    out.push(orbit);
  }
  return out;
}

/**
 * Снять как можно больше подсказок, не потеряв единственность решения и не
 * перевалив за потолок сложности. Потолок проверяется на каждом шаге: резать
 * вслепую и потом надеяться попасть в полосу стоило десятки секунд на задачу.
 */
function carve(b, solution, rnd, maxLevel, symKey, minClues) {
  const puzzle = solution.slice();
  let clues = b.cells;
  for (const orbit of shuffled(orbits(b.n, symKey), rnd)) {
    // Нижний порог подсказок — единственная честная форма этого ползунка.
    // Задать точное число нельзя: задачи с произвольным числом подсказок
    // может не существовать вовсе (для классики 9x9 доказанный минимум — 17,
    // с симметрией выше). Порог снизу выполним всегда и даёт ровно то, что
    // от него ждут: больше подсказок — мягче задача.
    if (clues - orbit.length < minClues) continue;
    const keep = orbit.map((c) => puzzle[c]);
    orbit.forEach((c) => { puzzle[c] = 0; });
    const restore = () => orbit.forEach((c, i) => { puzzle[c] = keep[i]; });
    if (countSolutions(b, puzzle, 2).count !== 1) { restore(); continue; }
    const g = grade(b, puzzle);
    if (!g.solved || g.level > maxLevel) { restore(); continue; }
    clues -= orbit.length;
  }
  return puzzle;
}

export function generate(spec, bandKey, rnd, opts = {}) {
  const { symmetry = 'none', attempts = 8, minClues = 0 } = opts;
  const band = BANDS.find((x) => x.key === bandKey);
  if (!band) throw new Error('неизвестная сложность: ' + bandKey);

  let closest = null;
  for (let i = 0; i < attempts; i++) {
    const b = makeBoard(spec, rnd);
    const solution = fullGrid(b, rnd);
    const puzzle = carve(b, solution, rnd, band.levels[1], symmetry, minClues);
    const g = grade(b, puzzle);
    if (!g.solved) continue;

    const made = { spec: b.spec, key: b.key, symmetry, minClues, band: bandOf(g.level), level: g.level,
                   used: g.used, puzzle, solution, clues: puzzle.filter(Boolean).length,
                   units: b.units, n: b.n };
    if (g.level >= band.levels[0]) return made;
    if (!closest || g.level > closest.level) closest = made;
  }
  return closest;
}
