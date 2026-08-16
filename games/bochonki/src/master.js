// Режим «Карточка мастера» — roll-and-write на поле 5×5.
//
// Ключевое требование концепта: игрок всегда видит, сколько даст постановка
// в каждую свободную клетку. Подсветка считается тем же scoreDelta, что и
// финальный счёт, поэтому предсказание не может разойтись с результатом.

import {
  SIZE, emptyGrid, scoreDelta, scoreBreakdown, activeRules, isFull, EMPTY,
} from './scoring.js';
import { drawBag, daySeed, dayKey } from './rng.js';

export function createGame({ seed, gamesPlayed, mode }) {
  return {
    mode,                              // 'daily' | 'free'
    seed,
    dayKey: mode === 'daily' ? null : null,
    grid: emptyGrid(),
    bag: drawBag(seed, SIZE * SIZE),
    index: 0,
    rules: activeRules(gamesPlayed),
    placements: [],                    // история ходов для отмены
    undoUsed: false,
    peekUsed: false,
    finished: false,
  };
}

export function currentBarrel(g) {
  return g.index < g.bag.length ? g.bag[g.index] : null;
}

export function barrelsLeft(g) {
  return Math.max(0, g.bag.length - g.index);
}

// Предпросмотр по всем свободным клеткам сразу — это и есть обучение.
export function previewAll(g) {
  const value = currentBarrel(g);
  const out = [];
  if (value == null) return out;
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (g.grid[r][c] !== EMPTY) continue;
      const d = scoreDelta(g.grid, r, c, value, g.rules);
      out.push({ row: r, cell: c, delta: d.delta, changed: d.changed });
    }
  }
  return out;
}

export function place(g, row, cell) {
  if (g.finished) return null;
  const value = currentBarrel(g);
  if (value == null || g.grid[row][cell] !== EMPTY) return null;

  const d = scoreDelta(g.grid, row, cell, value, g.rules);
  g.grid[row][cell] = value;
  g.placements.push({ row, cell, value, delta: d.delta });
  g.index++;
  if (isFull(g.grid) || g.index >= g.bag.length) g.finished = true;
  return { value, delta: d.delta, changed: d.changed, finished: g.finished };
}

// Отмена последнего хода — платная (rewarded) и ровно одна за партию.
export function undo(g) {
  if (g.undoUsed || !g.placements.length || g.finished) return false;
  const last = g.placements.pop();
  g.grid[last.row][last.cell] = EMPTY;
  g.index--;
  g.undoUsed = true;
  return true;
}

// Подсмотреть следующие бочонки — тоже rewarded, один раз за партию.
export function peek(g, count = 3) {
  if (g.peekUsed) return null;
  g.peekUsed = true;
  return g.bag.slice(g.index + 1, g.index + 1 + count);
}

export function score(g) {
  return scoreBreakdown(g.grid, g.rules);
}

// Разбор итога по группам правил — для экрана результата и достижений.
export function summary(g) {
  const all = scoreBreakdown(g.grid, ['rows', 'cols', 'diags']);
  const part = (kind) => all.lines.filter((l) => l.kind === kind).reduce((a, l) => a + l.points, 0);
  const active = scoreBreakdown(g.grid, g.rules);

  const fullRows = all.lines.filter((l) => l.kind === 'row' && l.points === 25).length;
  const fullCols = all.lines.filter((l) => l.kind === 'col' && l.points === 30).length;
  const fullDiags = all.lines.filter((l) => l.kind === 'diag' && l.points === 18).length;

  return {
    total: active.total,
    rowPoints: g.rules.includes('rows') ? part('row') : 0,
    colPoints: g.rules.includes('cols') ? part('col') : 0,
    diagPoints: g.rules.includes('diags') ? part('diag') : 0,
    fullRows, fullCols, fullDiags,
    ascendingFull: fullRows,
    decadeFive: fullCols,
    parityFive: fullDiags,
    lines: active.lines,
  };
}

export { daySeed, dayKey };
