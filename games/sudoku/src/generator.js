// Генератор задач.
//
// Две гарантии, которые мы даём и закрываем тестами:
//   1) решение единственно — иначе задача не судоку, а угадайка;
//   2) заявленная сложность настоящая: она равна самой сложной технике,
//      без которой задача не решается. В каталоге «сложные» задачи сплошь
//      и рядом закрываются одними одиночками — мы так не делаем.

import { makeBoard } from './units.js';
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

/**
 * Снять как можно больше подсказок, не потеряв единственность решения и не
 * перевалив за потолок сложности. Потолок проверяется на каждом шаге: резать
 * вслепую и потом надеяться попасть в полосу — это десятки секунд на задачу.
 */
function carve(b, solution, rnd, maxLevel) {
  const puzzle = solution.slice();
  for (const c of shuffled([...Array(b.cells).keys()], rnd)) {
    const keep = puzzle[c];
    puzzle[c] = 0;
    if (countSolutions(b, puzzle, 2).count !== 1) { puzzle[c] = keep; continue; }
    const g = grade(b, puzzle);
    if (!g.solved || g.level > maxLevel) puzzle[c] = keep;
  }
  return puzzle;
}

/**
 * Задача заданной сложности. Возвращает null, если полоса недостижима:
 * на поле 6×6, например, X-Wing физически не встречается.
 */
export function generate(variant, bandKey, rnd, attempts = 8) {
  const band = BANDS.find((x) => x.key === bandKey);
  if (!band) throw new Error('неизвестная сложность: ' + bandKey);

  let closest = null;
  for (let i = 0; i < attempts; i++) {
    const b = makeBoard(variant, rnd);
    const solution = fullGrid(b, rnd);
    const puzzle = carve(b, solution, rnd, band.levels[1]);
    const g = grade(b, puzzle);
    if (!g.solved) continue;

    const made = { variant, band: bandOf(g.level), level: g.level, used: g.used,
                   puzzle, solution, clues: puzzle.filter(Boolean).length, units: b.units };
    if (g.level >= band.levels[0]) return made;
    if (!closest || g.level > closest.level) closest = made;
  }
  return closest;
}
