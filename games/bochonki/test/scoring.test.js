import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SIZE, EMPTY, emptyGrid, scoreRow, scoreCol, scoreDiag,
  scoreGrid, scoreDelta, emptyCells, isFull, activeRules,
} from '../src/scoring.js';
import { drawBag, mulberry32, daySeed, dayKey } from '../src/rng.js';

const ALL = ['rows', 'cols', 'diags'];

test('мешок детерминирован и без повторов', () => {
  const a = drawBag(20260816);
  const b = drawBag(20260816);
  assert.deepEqual(a, b, 'один сид — один мешок');
  assert.equal(a.length, 25);
  assert.equal(new Set(a).size, 25, 'повторов нет');
  assert.ok(a.every((n) => n >= 1 && n <= 90));
  assert.notDeepEqual(drawBag(20260817), a, 'другой день — другой мешок');
});

test('сид дня одинаков внутри суток UTC и меняется на границе', () => {
  const d1 = Date.UTC(2026, 7, 16, 0, 0, 1);
  const d2 = Date.UTC(2026, 7, 16, 23, 59, 59);
  const d3 = Date.UTC(2026, 7, 17, 0, 0, 1);
  assert.equal(daySeed(d1), daySeed(d2));
  assert.notEqual(daySeed(d2), daySeed(d3));
  assert.equal(dayKey(d1), '2026-08-16');
});

test('строки: очки за самую длинную возрастающую серию', () => {
  assert.equal(scoreRow([1, 2, 3, 4, 5]), 25, 'полная строка');
  assert.equal(scoreRow([5, 4, 3, 2, 1]), 0, 'убывание не считается');
  assert.equal(scoreRow([1, 2, 3, 0, 0]), 6, 'серия из трёх');
  assert.equal(scoreRow([9, 1, 2, 3, 4]), 12, 'серия из четырёх после обрыва');
  assert.equal(scoreRow([1, 1, 2, 3, 4]), 12, 'равные числа рвут серию');
  assert.equal(scoreRow([0, 0, 0, 0, 0]), 0, 'пустая строка');
  assert.equal(scoreRow([7, 0, 8, 9, 0]), 2, 'пустая клетка рвёт серию');
});

test('столбцы: очки за родство десятков', () => {
  assert.equal(scoreCol([1, 5, 9, 3, 7]), 30, 'все пять из первого десятка');
  assert.equal(scoreCol([11, 15, 19, 3, 7]), 8, 'тройка из второго десятка');
  assert.equal(scoreCol([1, 20, 35, 47, 88]), 0, 'все десятки разные');
  assert.equal(scoreCol([90, 85, 0, 0, 0]), 3, '80..90 — один столбец карточки');
  assert.equal(scoreCol([81, 90, 0, 0, 0]), 3, '81 и 90 — один столбец');
  assert.equal(scoreCol([9, 10, 0, 0, 0]), 0, '9 и 10 — разные столбцы, как в лото');
  assert.equal(scoreCol([79, 80, 0, 0, 0]), 0, '79 и 80 — разные столбцы');
});

test('диагонали: очки за преобладающую чётность', () => {
  assert.equal(scoreDiag([2, 4, 6, 8, 10]), 18, 'все чётные');
  assert.equal(scoreDiag([1, 3, 5, 7, 9]), 18, 'все нечётные');
  assert.equal(scoreDiag([2, 4, 6, 8, 1]), 12, 'четыре из пяти');
  assert.equal(scoreDiag([2, 4, 1, 3, 0]), 0, 'паритет 2:2 очков не даёт');
  assert.equal(scoreDiag([2, 4, 6, 0, 0]), 6, 'три чётных');
});

test('лесенка правил открывается по числу сыгранных партий', () => {
  assert.deepEqual(activeRules(0), ['rows']);
  assert.deepEqual(activeRules(1), ['rows', 'cols']);
  assert.deepEqual(activeRules(2), ['rows', 'cols', 'diags']);
  assert.deepEqual(activeRules(50), ['rows', 'cols', 'diags']);
});

test('подсветка не может разойтись со счётом: сумма дельт равна итогу', () => {
  // Главный инвариант игры. Гоняем 300 случайных партий со случайными
  // постановками: накопленная сумма предсказаний обязана совпасть с финальным счётом.
  for (let seed = 1; seed <= 300; seed++) {
    const rnd = mulberry32(seed * 7919);
    const bag = drawBag(seed * 104729);
    const grid = emptyGrid();
    let predicted = 0;

    for (const value of bag) {
      const free = emptyCells(grid);
      if (!free.length) break;
      const [r, c] = free[Math.floor(rnd() * free.length)];
      const res = scoreDelta(grid, r, c, value, ALL);
      assert.ok(res, 'дельта считается для пустой клетки');
      predicted += res.delta;
      grid[r][c] = value;
    }

    assert.ok(isFull(grid), 'мешок из 25 бочонков заполняет поле 5×5');
    assert.equal(
      predicted, scoreGrid(grid, ALL),
      `сид ${seed}: предсказано ${predicted}, посчитано ${scoreGrid(grid, ALL)}`
    );
  }
});

test('дельта не изменяет поле', () => {
  const grid = emptyGrid();
  grid[0][0] = 5;
  const snapshot = JSON.stringify(grid);
  scoreDelta(grid, 2, 2, 42, ALL);
  assert.equal(JSON.stringify(grid), snapshot, 'поле осталось прежним');
});

test('в занятую клетку поставить нельзя', () => {
  const grid = emptyGrid();
  grid[1][1] = 7;
  assert.equal(scoreDelta(grid, 1, 1, 8, ALL), null);
});

test('дельта сообщает, какие линии просели', () => {
  const grid = emptyGrid();
  // 1,2,3,4 в строке — серия из четырёх (12 очков). Ставим 0 в конец: серия не растёт.
  grid[0][0] = 10; grid[0][1] = 20; grid[0][2] = 30; grid[0][3] = 40;
  const good = scoreDelta(grid, 0, 4, 50, ['rows']);
  assert.equal(good.delta, 25 - 12, 'замыкание строки добавляет очки');
  const bad = scoreDelta(grid, 0, 4, 5, ['rows']);
  assert.equal(bad.delta, 0, 'меньшее число серию не продолжает');
});
