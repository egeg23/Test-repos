import test from 'node:test';
import assert from 'node:assert/strict';
import { SIZE, emptyGrid, scoreGrid } from '../src/scoring.js';

// Экран «Как играть» рисует три примера и подписывает их очками.
// Эти тесты держат туториал в согласии с реальными правилами:
// если система очков изменится, тест упадёт раньше, чем игрок увидит враньё.

const put = (cells) => {
  const g = emptyGrid();
  for (const [r, c, v] of cells) g[r][c] = v;
  return g;
};

test('пример строки в туториале действительно даёт +25', () => {
  const g = put([4, 18, 29, 46, 72].map((v, i) => [2, i, v]));
  assert.equal(scoreGrid(g, ['rows']), 25);
});

test('пример столбца в туториале действительно даёт +30', () => {
  const g = put([31, 35, 33, 38, 30].map((v, i) => [i, 2, v]));
  assert.equal(scoreGrid(g, ['cols']), 30);
});

test('пример диагонали в туториале действительно даёт +18', () => {
  const g = put([4, 18, 46, 72, 90].map((v, i) => [i, i, v]));
  assert.equal(scoreGrid(g, ['diags']), 18);
});

test('пример подсказки в туториале действительно даёт +6', () => {
  // 18 _ 46 в строке: постановка 29 между ними замыкает серию из трёх.
  const g = put([[1, 1, 18], [1, 3, 46]]);
  const before = scoreGrid(g, ['rows']);
  g[1][2] = 29;
  assert.equal(scoreGrid(g, ['rows']) - before, 6);
});

test('числа в примерах не противоречат подписям', () => {
  const row = [4, 18, 29, 46, 72];
  assert.deepEqual(row, [...row].sort((a, b) => a - b), 'строка обязана возрастать');

  const col = [31, 35, 33, 38, 30];
  const dec = (n) => (n >= 80 ? 8 : Math.floor(n / 10));
  assert.equal(new Set(col.map(dec)).size, 1, 'столбец обязан быть из одного десятка');

  const diag = [4, 18, 46, 72, 90];
  assert.equal(new Set(diag.map((n) => n % 2)).size, 1, 'диагональ обязана быть одной чётности');

  for (const n of [...row, ...col, ...diag]) {
    assert.ok(n >= 1 && n <= 90, `${n} вне диапазона бочонков`);
  }
});
