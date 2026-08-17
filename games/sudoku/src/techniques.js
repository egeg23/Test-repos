// Техники решения — по возрастанию сложности.
//
// Это не вспомогательный код, а сердце проекта. Из него растут сразу две вещи:
//   1) честная оценка сложности — задача трудна ровно настолько, насколько
//      трудна самая сложная техника, без которой её не решить;
//   2) подсказка, которая ОБЪЯСНЯЕТ. Каждая техника возвращает не только ход,
//      но и причину: какая область, какие клетки, почему иначе нельзя.
//      В каталоге подсказка обычно просто открывает цифру — это не учит.
//
// Все техники работают со списком областей и потому одинаково годятся для
// классики, диагонали, кривых областей и 6×6.

import { bit, popcount, firstValue } from './units.js';

/** Кандидаты «в лоб»: что не занято соседями. Без распространения. */
export function candidates(b, grid) {
  const cands = new Int16Array(b.cells);
  for (let c = 0; c < b.cells; c++) {
    if (grid[c]) { cands[c] = 0; continue; }
    let m = b.full;
    for (const p of b.peers[c]) if (grid[p]) m &= ~bit(grid[p]);
    cands[c] = m;
  }
  return cands;
}

const rowOf = (b, c) => Math.floor(c / b.n) + 1;
const colOf = (b, c) => (c % b.n) + 1;
const at = (b, c) => `r${rowOf(b, c)}c${colOf(b, c)}`;

// Как называть область в объяснении. Строки и столбцы узнаются по форме,
// остальное — блок, а у кривых областей слова «квадрат» нет вовсе.
//
// Падеж обязателен параметром: одна и та же область попадает и в «в строке 2»,
// и в «из остальных клеток строки 2». Одна форма на оба случая давала
// «из остальных клеток столбце 3» — для игры, которая продаётся качеством
// объяснений, это брак.
function unitName(b, u, form = 'loc') {
  const rows = new Set(u.map((c) => rowOf(b, c)));
  const cols = new Set(u.map((c) => colOf(b, c)));
  if (rows.size === 1) return `${form === 'gen' ? 'строки' : 'строке'} ${[...rows][0]}`;
  if (cols.size === 1) return `${form === 'gen' ? 'столбца' : 'столбце'} ${[...cols][0]}`;
  if (b.variant === 'jigsaw') return 'этой области';
  return form === 'gen' ? 'этого блока' : 'этом блоке';
}

// --- 1. Одиночка в клетке -------------------------------------------------
function nakedSingle(b, grid, cands) {
  for (let c = 0; c < b.cells; c++) {
    if (grid[c] || popcount(cands[c]) !== 1) continue;
    const v = firstValue(cands[c]);
    return { technique: 'naked_single', place: c, value: v, eliminations: [],
      highlight: b.peers[c].filter((p) => grid[p]),
      text: `В клетке ${at(b, c)} все цифры кроме ${v} уже стоят по соседству — значит здесь ${v}.` };
  }
  return null;
}

// --- 2. Единственное место в области --------------------------------------
function hiddenSingle(b, grid, cands) {
  for (const u of b.units) {
    for (let v = 1; v <= b.n; v++) {
      if (u.some((c) => grid[c] === v)) continue;
      const places = u.filter((c) => !grid[c] && (cands[c] & bit(v)));
      if (places.length !== 1) continue;
      const c = places[0];
      if (popcount(cands[c]) === 1) continue;          // это уже одиночка
      return { technique: 'hidden_single', place: c, value: v, eliminations: [],
        highlight: u.filter((x) => x !== c),
        text: `В ${unitName(b, u)} цифру ${v} больше некуда поставить — только ${at(b, c)}.` };
    }
  }
  return null;
}

// --- 3. Запертый кандидат -------------------------------------------------
// Обобщённая форма: если внутри области все места для значения лежат в
// пересечении с другой областью, из остальной части второй области значение
// уходит. Для кривых областей работает так же, как для квадратов.
function lockedCandidates(b, grid, cands) {
  for (let i1 = 0; i1 < b.units.length; i1++) {
    const u1 = b.units[i1], s1 = b.unitSets[i1];
    for (let v = 1; v <= b.n; v++) {
      if (u1.some((c) => grid[c] === v)) continue;
      const places = u1.filter((c) => !grid[c] && (cands[c] & bit(v)));
      if (places.length < 2 || places.length > 3) continue;
      for (let i2 = 0; i2 < b.units.length; i2++) {
        if (i2 === i1) continue;
        const u2 = b.units[i2], s2 = b.unitSets[i2];
        if (!places.every((c) => s2.has(c))) continue;
        const kill = u2.filter((c) => !grid[c] && !s1.has(c) && (cands[c] & bit(v)));
        if (!kill.length) continue;
        return { technique: 'locked_candidates', place: null, value: v,
          eliminations: kill.map((c) => ({ cell: c, value: v })),
          highlight: places,
          text: `В ${unitName(b, u1)} цифра ${v} возможна только в клетках ` +
                `${places.map((c) => at(b, c)).join(', ')}. Они все лежат в ${unitName(b, u2)}, ` +
                `поэтому в остальной части ${unitName(b, u2, 'gen')} цифры ${v} быть не может.` };
      }
    }
  }
  return null;
}

// --- 4. Голая пара --------------------------------------------------------
function nakedPair(b, grid, cands) {
  for (const u of b.units) {
    const open = u.filter((c) => !grid[c] && popcount(cands[c]) === 2);
    for (let i = 0; i < open.length; i++) {
      for (let j = i + 1; j < open.length; j++) {
        if (cands[open[i]] !== cands[open[j]]) continue;
        const m = cands[open[i]];
        const vs = [];
        for (let v = 1; v <= b.n; v++) if (m & bit(v)) vs.push(v);
        const kill = [];
        for (const c of u) {
          if (c === open[i] || c === open[j] || grid[c]) continue;
          for (const v of vs) if (cands[c] & bit(v)) kill.push({ cell: c, value: v });
        }
        if (!kill.length) continue;
        return { technique: 'naked_pair', place: null, value: null, eliminations: kill,
          highlight: [open[i], open[j]],
          text: `${at(b, open[i])} и ${at(b, open[j])} могут быть только ${vs[0]} или ${vs[1]}. ` +
                `Вдвоём они займут обе эти цифры, поэтому из остальных клеток ` +
                `${unitName(b, u, 'gen')} цифры ${vs[0]} и ${vs[1]} уходят.` };
      }
    }
  }
  return null;
}

// --- 5. Скрытая пара ------------------------------------------------------
function hiddenPair(b, grid, cands) {
  for (const u of b.units) {
    for (let v1 = 1; v1 <= b.n; v1++) {
      for (let v2 = v1 + 1; v2 <= b.n; v2++) {
        const p1 = u.filter((c) => !grid[c] && (cands[c] & bit(v1)));
        const p2 = u.filter((c) => !grid[c] && (cands[c] & bit(v2)));
        if (p1.length !== 2 || p2.length !== 2) continue;
        if (p1[0] !== p2[0] || p1[1] !== p2[1]) continue;
        const keep = bit(v1) | bit(v2);
        const kill = [];
        for (const c of p1) {
          for (let v = 1; v <= b.n; v++) {
            if ((cands[c] & bit(v)) && !(keep & bit(v))) kill.push({ cell: c, value: v });
          }
        }
        if (!kill.length) continue;
        return { technique: 'hidden_pair', place: null, value: null, eliminations: kill,
          highlight: p1,
          text: `В ${unitName(b, u)} цифры ${v1} и ${v2} помещаются только в ${at(b, p1[0])} ` +
                `и ${at(b, p1[1])}. Значит эти две клетки заняты ими, и других кандидатов там нет.` };
      }
    }
  }
  return null;
}

// --- 6. X-Wing ------------------------------------------------------------
function xWing(b, grid, cands) {
  const lines = (byRow) => [...Array(b.n).keys()].map((i) =>
    [...Array(b.n).keys()].map((j) => (byRow ? i * b.n + j : j * b.n + i)));
  for (const byRow of [true, false]) {
    const ls = lines(byRow);
    for (let v = 1; v <= b.n; v++) {
      const spots = ls.map((l) => l.filter((c) => !grid[c] && (cands[c] & bit(v))));
      for (let i = 0; i < ls.length; i++) {
        if (spots[i].length !== 2) continue;
        for (let j = i + 1; j < ls.length; j++) {
          if (spots[j].length !== 2) continue;
          const key = (c) => (byRow ? c % b.n : Math.floor(c / b.n));
          if (key(spots[i][0]) !== key(spots[j][0]) || key(spots[i][1]) !== key(spots[j][1])) continue;
          const corners = [...spots[i], ...spots[j]];
          const kill = [];
          for (const k of [key(spots[i][0]), key(spots[i][1])]) {
            for (let x = 0; x < b.n; x++) {
              const c = byRow ? x * b.n + k : k * b.n + x;
              if (corners.includes(c) || grid[c]) continue;
              if (cands[c] & bit(v)) kill.push({ cell: c, value: v });
            }
          }
          if (!kill.length) continue;
          const what = byRow ? 'строках' : 'столбцах';
          return { technique: 'x_wing', place: null, value: v, eliminations: kill,
            highlight: corners,
            text: `Цифра ${v} в двух ${what} стоит ровно в двух клетках, и они образуют ` +
                  `прямоугольник ${corners.map((c) => at(b, c)).join(', ')}. Как их ни расставь, ` +
                  `${v} займёт оба поперечных ряда — из них ${v} уходит.` };
        }
      }
    }
  }
  return null;
}

export const TECHNIQUES = [
  { key: 'naked_single',      level: 1, name: 'Одиночка в клетке',       find: nakedSingle },
  { key: 'hidden_single',     level: 2, name: 'Единственное место',      find: hiddenSingle },
  { key: 'locked_candidates', level: 3, name: 'Запертый кандидат',       find: lockedCandidates },
  { key: 'naked_pair',        level: 4, name: 'Голая пара',              find: nakedPair },
  { key: 'hidden_pair',       level: 5, name: 'Скрытая пара',            find: hiddenPair },
  { key: 'x_wing',            level: 6, name: 'X-Wing',                  find: xWing },
];

/** Первый ход, который можно объяснить. Это же и есть подсказка игроку. */
export function nextStep(b, grid) {
  const cands = candidates(b, grid);
  for (const t of TECHNIQUES) {
    const step = t.find(b, grid, cands);
    if (step) return { ...step, level: t.level, name: t.name };
  }
  return null;
}

/**
 * Пройти задачу только человеческими техниками, не сложнее maxLevel.
 * Ограничение сверху нужно, чтобы доказать заявленную сложность: задача
 * уровня L обязана НЕ решаться техниками до L-1 включительно.
 * Возвращает максимальный уровень и сколько раз что понадобилось.
 * solved: false означает, что без перебора не обойтись — такие мы не выдаём.
 */
export function grade(b, puzzle, maxLevel = Infinity) {
  const grid = puzzle.slice();
  const cands = candidates(b, grid);
  const allowed = TECHNIQUES.filter((t) => t.level <= maxLevel);
  const used = {};
  let max = 0;

  for (let guard = 0; guard < b.cells * 20; guard++) {
    if (grid.every((v) => v)) return { solved: true, level: max, used };

    let moved = false;
    for (const t of allowed) {
      const step = t.find(b, grid, cands);
      if (!step) continue;

      if (step.place != null) {
        grid[step.place] = step.value;
        // Пересчёт от сетки вернул бы уже снятых кандидатов, поэтому
        // пересечение: новые ограничения добавляются, старые не теряются.
        const fresh = candidates(b, grid);
        for (let c = 0; c < b.cells; c++) cands[c] &= fresh[c];
      } else {
        const real = step.eliminations.filter((e) => cands[e.cell] & bit(e.value));
        if (!real.length) continue;                 // техника ничего не меняет
        for (const e of real) cands[e.cell] &= ~bit(e.value);
      }

      used[t.key] = (used[t.key] || 0) + 1;
      max = Math.max(max, t.level);
      moved = true;
      break;
    }
    if (!moved) return { solved: false, level: max, used };
  }
  return { solved: false, level: max, used };
}
