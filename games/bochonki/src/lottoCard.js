// Генератор карточки русского лото.
//
// Карточка: 3 строки × 9 столбцов, ровно 15 чисел, по 5 в каждой строке.
// Столбец j содержит числа своего десятка (0: 1–9, 1: 10–19, ... 8: 80–90),
// в столбце от 1 до 3 чисел, сверху вниз по возрастанию.
// Нарушение любого из этих правил сразу видно игроку 55+, который в лото играл.

import { mulberry32, shuffle } from './rng.js';

export const ROWS = 3;
export const COLS = 9;
export const NUMBERS = 15;
export const PER_ROW = 5;

export function columnRange(j) {
  if (j === 0) return [1, 9];
  if (j === COLS - 1) return [80, 90];
  return [j * 10, j * 10 + 9];
}

// Сколько чисел в каждом столбце: по одному в каждом плюс 6 добавочных, максимум 3 в столбце.
function columnCounts(rnd) {
  const counts = Array(COLS).fill(1);
  let left = NUMBERS - COLS;
  while (left > 0) {
    const j = Math.floor(rnd() * COLS);
    if (counts[j] < 3) { counts[j]++; left--; }
  }
  return counts;
}

// Раскладываем числа столбцов по строкам так, чтобы в каждой строке вышло ровно 5.
// Жадно с откатом: столбцы с большим числом чисел размещаем первыми.
function assignRows(counts, rnd) {
  const order = counts.map((c, j) => [c, j]).sort((a, b) => b[0] - a[0] || rnd() - 0.5);
  const rowLoad = Array(ROWS).fill(0);
  const placement = Array(COLS).fill(null);

  for (const [count, j] of order) {
    // Из строк с наибольшим запасом берём нужное количество.
    const rows = [0, 1, 2]
      .filter((r) => rowLoad[r] < PER_ROW)
      .sort((a, b) => (PER_ROW - rowLoad[b]) - (PER_ROW - rowLoad[a]) || rnd() - 0.5);
    if (rows.length < count) return null;
    const chosen = rows.slice(0, count);
    chosen.forEach((r) => rowLoad[r]++);
    placement[j] = chosen.sort((a, b) => a - b);
  }
  return rowLoad.every((n) => n === PER_ROW) ? placement : null;
}

export function makeCard(seed) {
  const rnd = mulberry32(seed >>> 0);
  for (let attempt = 0; attempt < 200; attempt++) {
    const counts = columnCounts(rnd);
    const placement = assignRows(counts, rnd);
    if (!placement) continue;

    const grid = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
    for (let j = 0; j < COLS; j++) {
      const [lo, hi] = columnRange(j);
      const pool = [];
      for (let n = lo; n <= hi; n++) pool.push(n);
      const picked = shuffle(pool, rnd).slice(0, counts[j]).sort((a, b) => a - b);
      placement[j].forEach((r, k) => { grid[r][j] = picked[k]; });
    }
    return grid;
  }
  throw new Error('не удалось собрать карточку лото');
}

export function cardNumbers(card) {
  return card.flat().filter((n) => n > 0);
}

// Проверка карточки на соответствие правилам — используется тестами
// и как страховка в рантайме.
export function validateCard(card) {
  const errors = [];
  if (card.length !== ROWS) errors.push(`строк ${card.length}, ожидалось ${ROWS}`);
  card.forEach((row, i) => {
    if (row.length !== COLS) errors.push(`в строке ${i} столбцов ${row.length}`);
    const filled = row.filter((n) => n > 0).length;
    if (filled !== PER_ROW) errors.push(`в строке ${i} чисел ${filled}, ожидалось ${PER_ROW}`);
  });

  const nums = cardNumbers(card);
  if (nums.length !== NUMBERS) errors.push(`всего чисел ${nums.length}, ожидалось ${NUMBERS}`);
  if (new Set(nums).size !== nums.length) errors.push('есть повторяющиеся числа');

  for (let j = 0; j < COLS; j++) {
    const [lo, hi] = columnRange(j);
    const col = card.map((r) => r[j]).filter((n) => n > 0);
    if (col.length < 1 || col.length > 3) errors.push(`в столбце ${j} чисел ${col.length}`);
    if (col.some((n) => n < lo || n > hi)) errors.push(`столбец ${j}: число вне диапазона ${lo}–${hi}`);
    const sorted = [...col].sort((a, b) => a - b);
    if (col.join(',') !== sorted.join(',')) errors.push(`столбец ${j}: числа не по возрастанию`);
  }
  return errors;
}
