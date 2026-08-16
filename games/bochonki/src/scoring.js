// Система очков «Карточки мастера».
//
// Три независимых правила, открывающиеся лесенкой (см. RULE_TIERS):
//   строки    — возрастание слева направо
//   столбцы   — родство десятков
//   диагонали — чётность
//
// Единственный источник правды для счёта. Подсветка «что даст эта клетка»
// считается тем же кодом (scoreDelta), поэтому предсказание не может разойтись
// с фактическим результатом — это ключевое требование концепта.

export const SIZE = 5;
export const EMPTY = 0;

// Сколько партий сыграно -> какие правила активны.
export const RULE_TIERS = [
  { after: 0, rules: ['rows'] },
  { after: 1, rules: ['rows', 'cols'] },
  { after: 2, rules: ['rows', 'cols', 'diags'] },
];

export function activeRules(gamesPlayed) {
  let r = RULE_TIERS[0].rules;
  for (const t of RULE_TIERS) if (gamesPlayed >= t.after) r = t.rules;
  return r;
}

export function emptyGrid() {
  return Array.from({ length: SIZE }, () => Array(SIZE).fill(EMPTY));
}

// Десятки нарезаны как колонки карточки русского лото: 1..9, 10..19, ... 70..79, 80..90.
// Та же нарезка используется в режиме лото, поэтому «родство» читается игроком
// как «числа из одного столбца карточки».
const decade = (n) => (n >= 80 ? 8 : Math.floor(n / 10));

// --- строки: самая длинная строго возрастающая серия подряд идущих клеток ---
const RUN_POINTS = [0, 0, 2, 6, 12, 25];

export function scoreRow(cells) {
  let best = 0, run = 0;
  for (let i = 0; i < cells.length; i++) {
    if (cells[i] === EMPTY) { run = 0; continue; }
    if (run === 0) run = 1;
    else if (cells[i - 1] !== EMPTY && cells[i] > cells[i - 1]) run++;
    else run = 1;
    if (run > best) best = run;
  }
  return RUN_POINTS[best] || 0;
}

// --- столбцы: самая большая группа чисел одного десятка ---
const DECADE_POINTS = [0, 0, 3, 8, 15, 30];

export function scoreCol(cells) {
  const counts = new Map();
  for (const c of cells) {
    if (c === EMPTY) continue;
    const d = decade(c);
    counts.set(d, (counts.get(d) || 0) + 1);
  }
  let best = 0;
  for (const v of counts.values()) if (v > best) best = v;
  return DECADE_POINTS[best] || 0;
}

// --- диагонали: преобладающая чётность ---
export function scoreDiag(cells) {
  let even = 0, odd = 0;
  for (const c of cells) {
    if (c === EMPTY) continue;
    if (c % 2 === 0) even++; else odd++;
  }
  const k = Math.max(even, odd);
  return k >= 3 ? (k - 2) * 6 : 0;
}

const col = (g, i) => g.map((r) => r[i]);
const diagMain = (g) => g.map((r, i) => r[i]);
const diagAnti = (g) => g.map((r, i) => r[SIZE - 1 - i]);

// Полный разбор счёта: и сумма, и вклад каждой линии — для подсветки.
export function scoreBreakdown(grid, rules) {
  const on = new Set(rules);
  const lines = [];
  let total = 0;

  if (on.has('rows')) {
    for (let i = 0; i < SIZE; i++) {
      const p = scoreRow(grid[i]);
      lines.push({ kind: 'row', index: i, points: p });
      total += p;
    }
  }
  if (on.has('cols')) {
    for (let i = 0; i < SIZE; i++) {
      const p = scoreCol(col(grid, i));
      lines.push({ kind: 'col', index: i, points: p });
      total += p;
    }
  }
  if (on.has('diags')) {
    const a = scoreDiag(diagMain(grid));
    const b = scoreDiag(diagAnti(grid));
    lines.push({ kind: 'diag', index: 0, points: a });
    lines.push({ kind: 'diag', index: 1, points: b });
    total += a + b;
  }
  return { total, lines };
}

export function scoreGrid(grid, rules) {
  return scoreBreakdown(grid, rules).total;
}

// Сколько даст постановка бочонка в клетку и какие линии просядут.
// Возвращает дельту и список изменившихся линий — ровно то, что показывает подсветка.
export function scoreDelta(grid, row, cell, value, rules) {
  if (grid[row][cell] !== EMPTY) return null;
  const before = scoreBreakdown(grid, rules);
  grid[row][cell] = value;
  const after = scoreBreakdown(grid, rules);
  grid[row][cell] = EMPTY;

  const changed = [];
  for (let i = 0; i < after.lines.length; i++) {
    const d = after.lines[i].points - before.lines[i].points;
    if (d !== 0) changed.push({ ...after.lines[i], delta: d });
  }
  return { delta: after.total - before.total, changed };
}

export function isFull(grid) {
  return grid.every((r) => r.every((c) => c !== EMPTY));
}

export function emptyCells(grid) {
  const out = [];
  for (let r = 0; r < SIZE; r++)
    for (let c = 0; c < SIZE; c++)
      if (grid[r][c] === EMPTY) out.push([r, c]);
  return out;
}
