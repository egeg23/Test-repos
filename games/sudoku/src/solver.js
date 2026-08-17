// Решатель на распространении ограничений. Про варианты не знает ничего —
// работает с любым полем из units.js, поэтому диагональ, кривые области
// и 6×6 достаются бесплатно.
//
// Кандидаты хранятся битовой маской на клетку: девять бит вместо массива.
// Это не преждевременная оптимизация — генератор вызывает решатель тысячи
// раз на одну задачу (на каждое снятие подсказки проверяется единственность).

import { bit, popcount, firstValue } from './units.js';

export const emptyCands = (b) => new Int16Array(b.cells).fill(b.full);

/** Убрать значение v из клетки c. false — противоречие, ветка мертва. */
export function eliminate(b, cands, c, v) {
  const m = bit(v);
  if (!(cands[c] & m)) return true;              // уже убрано
  cands[c] &= ~m;

  const left = cands[c];
  if (left === 0) return false;                  // клетка без вариантов
  if (popcount(left) === 1) {
    // Единственный кандидат в клетке — значит у соседей его быть не может.
    const only = firstValue(left);
    for (const p of b.peers[c]) if (!eliminate(b, cands, p, only)) return false;
  }

  // Единственное место в области: если v больше некуда поставить — ставим.
  for (const u of b.unitsOf[c]) {
    let place = -1, count = 0;
    for (const x of u) if (cands[x] & m) { place = x; if (++count > 1) break; }
    if (count === 0) return false;
    if (count === 1 && popcount(cands[place]) > 1 && !assign(b, cands, place, v)) return false;
  }
  return true;
}

/** Поставить v в клетку c, вычистив остальных кандидатов. */
export function assign(b, cands, c, v) {
  const others = cands[c] & ~bit(v);
  for (let x = 1; x <= b.n; x++) {
    if (others & bit(x)) if (!eliminate(b, cands, c, x)) return false;
  }
  return true;
}

/** Разложить готовую сетку (0 — пусто) в кандидатов. null — противоречие. */
export function fromGrid(b, grid) {
  const cands = emptyCands(b);
  for (let c = 0; c < b.cells; c++) {
    if (grid[c] && !assign(b, cands, c, grid[c])) return null;
  }
  return cands;
}

const solved = (b, cands) => {
  for (let c = 0; c < b.cells; c++) if (popcount(cands[c]) !== 1) return false;
  return true;
};

export const toGrid = (b, cands) =>
  Array.from({ length: b.cells }, (_, c) =>
    popcount(cands[c]) === 1 ? firstValue(cands[c]) : 0);

/** Клетка с наименьшим числом кандидатов — самая дешёвая точка ветвления. */
function hardest(b, cands) {
  let best = -1, bestN = 99;
  for (let c = 0; c < b.cells; c++) {
    const k = popcount(cands[c]);
    if (k > 1 && k < bestN) { bestN = k; best = c; if (k === 2) break; }
  }
  return best;
}

/**
 * Сколько решений у задачи, но не больше limit.
 * Генератору хватает ответа «одно или больше одного», считать все незачем.
 */
export function countSolutions(b, grid, limit = 2, order = null) {
  const start = fromGrid(b, grid);
  if (!start) return 0;
  let found = 0;
  let first = null;

  (function search(cands) {
    if (found >= limit) return;
    if (solved(b, cands)) { found++; if (!first) first = toGrid(b, cands); return; }
    const c = hardest(b, cands);
    const vals = [];
    for (let v = 1; v <= b.n; v++) if (cands[c] & bit(v)) vals.push(v);
    if (order) order(vals);
    for (const v of vals) {
      const copy = cands.slice();
      if (assign(b, copy, c, v)) search(copy);
      if (found >= limit) return;
    }
  })(start);

  return { count: found, solution: first };
}

/** Полностью заполненная сетка — основа будущей задачи. */
export function fullGrid(b, rnd) {
  const shuffle = (a) => {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
  };
  const r = countSolutions(b, new Array(b.cells).fill(0), 1, shuffle);
  if (!r.solution) throw new Error('поле варианта не имеет решений');
  return r.solution;
}
