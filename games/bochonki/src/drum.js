// Режим «Барабан»: вытягивание становится решением.
//
// Барабан выкатывает три бочонка, игрок берёт один — два возвращаются в мешок
// на случайные позиции. Отказ от бочонка не окончателен: он вернётся, но
// неизвестно когда, и поле к тому времени будет другим.
//
// Поле, правила и подсчёт очков те же, что в «Карточке мастера», поэтому
// scoring.js переиспользуется целиком, а не дублируется.

import { SIZE, EMPTY, emptyGrid, scoreDelta, scoreBreakdown, activeRules, isFull } from './scoring.js';
import { mulberry32, shuffle } from './rng.js';

export const POOL = 30;      // бочонков в мешке
export const CANDS = 3;      // сколько барабан выкатывает за раз
export const TURNS = SIZE * SIZE;

export function createGame({ seed, gamesPlayed }) {
  const rnd = mulberry32((seed >>> 0) + 7);
  const all = Array.from({ length: 90 }, (_, i) => i + 1);
  const g = {
    mode: 'drum',
    seed,
    rnd,
    pool: shuffle(all, rnd).slice(0, POOL),
    cands: [],
    held: null,               // выбранный бочонок, ждёт постановки
    grid: emptyGrid(),
    rules: activeRules(gamesPlayed),
    placements: [],
    skipped: 0,               // сколько бочонков возвращено в мешок
    rerollUsed: false,        // перекат барабана — один раз за партию
    finished: false,
  };
  deal(g);
  return g;
}

function deal(g) {
  g.cands = g.pool.slice(0, Math.min(CANDS, g.pool.length));
}

// Взять кандидата: остальные уходят обратно в мешок на случайные позиции,
// поэтому вернуться могут и через ход, и через десять.
export function pick(g, index) {
  if (g.finished || g.held != null) return null;
  if (index < 0 || index >= g.cands.length) return null;

  const chosen = g.cands[index];
  const rest = g.cands.filter((_, i) => i !== index);

  g.pool = g.pool.slice(g.cands.length);
  for (const v of rest) {
    const at = Math.floor(g.rnd() * (g.pool.length + 1));
    g.pool.splice(at, 0, v);
    g.skipped++;
  }

  g.held = chosen;
  g.cands = [];
  return chosen;
}

export function place(g, row, cell) {
  if (g.finished || g.held == null) return null;
  if (g.grid[row][cell] !== EMPTY) return null;

  const value = g.held;
  const d = scoreDelta(g.grid, row, cell, value, g.rules);
  g.grid[row][cell] = value;
  g.placements.push({ row, cell, value, delta: d.delta });
  g.held = null;

  if (isFull(g.grid) || g.placements.length >= TURNS || g.pool.length === 0) {
    g.finished = true;
  } else {
    deal(g);
  }
  return { value, delta: d.delta, changed: d.changed, finished: g.finished };
}

// Перекатить барабан: вся тройка уходит обратно в мешок, выкатывается новая.
// Одна попытка за партию, только пока бочонок не взят.
export function reroll(g) {
  if (g.finished || g.rerollUsed || g.held != null || !g.cands.length) return false;
  const back = g.cands;
  g.pool = g.pool.slice(g.cands.length);
  for (const v of back) {
    const at = Math.floor(g.rnd() * (g.pool.length + 1));
    g.pool.splice(at, 0, v);
  }
  g.rerollUsed = true;
  deal(g);
  return true;
}

export function currentBarrel(g) { return g.held; }
export function barrelsLeft(g) { return TURNS - g.placements.length; }

// Лучшее, что даст этот бочонок на текущем поле. Показывается под кандидатом:
// выбор должен быть информированным, как и постановка.
export function bestDelta(g, value) {
  let best = null;
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (g.grid[r][c] !== EMPTY) continue;
      const d = scoreDelta(g.grid, r, c, value, g.rules).delta;
      if (best === null || d > best) best = d;
    }
  }
  return best ?? 0;
}

export function score(g) { return scoreBreakdown(g.grid, g.rules); }
