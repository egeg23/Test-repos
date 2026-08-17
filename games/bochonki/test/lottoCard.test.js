import test from 'node:test';
import assert from 'node:assert/strict';
import { makeCard, validateCard, cardNumbers, columnRange, ROWS, COLS } from '../src/lottoCard.js';

test('диапазоны столбцов как на настоящей карточке', () => {
  assert.deepEqual(columnRange(0), [1, 9]);
  assert.deepEqual(columnRange(1), [10, 19]);
  assert.deepEqual(columnRange(7), [70, 79]);
  assert.deepEqual(columnRange(8), [80, 90], 'последний столбец шире');
});

test('1000 карточек подряд соответствуют правилам лото', () => {
  for (let seed = 1; seed <= 1000; seed++) {
    const card = makeCard(seed);
    const errors = validateCard(card);
    assert.deepEqual(errors, [], `сид ${seed}: ${errors.join('; ')}`);
  }
});

test('карточка детерминирована по сиду', () => {
  assert.deepEqual(makeCard(42), makeCard(42));
  assert.notDeepEqual(makeCard(42), makeCard(43));
});

test('форма карточки и количество чисел', () => {
  const card = makeCard(7);
  assert.equal(card.length, ROWS);
  assert.ok(card.every((r) => r.length === COLS));
  assert.equal(cardNumbers(card).length, 15);
});

test('валидатор ловит подделку', () => {
  const card = makeCard(1);
  const broken = card.map((r) => [...r]);
  const j = broken[0].findIndex((n) => n > 0);
  broken[0][j] = 91; // вне любого диапазона
  assert.ok(validateCard(broken).length > 0, 'число вне диапазона должно отлавливаться');
});

// --- режим лото ---
import { createLotto, callNext, markPlayer, progress, TO_CLOSE } from '../src/lotto.js';

test('лото: партия всегда завершается победителем', () => {
  for (let seed = 1; seed <= 200; seed++) {
    const l = createLotto({ seed });
    let guard = 0;
    while (!l.finished && guard++ < 200) {
      const n = callNext(l);
      if (n != null && l.playerNumbers.has(n)) markPlayer(l, n); // идеальный игрок
    }
    assert.ok(l.finished, `сид ${seed}: партия не завершилась`);
    assert.ok(['player', 'rival'].includes(l.result));
    assert.equal(l.missed, 0, 'идеальный игрок ничего не пропускает');
  }
});

test('лото: невнимательный игрок копит пропуски и не может отметить задним числом', () => {
  const l = createLotto({ seed: 5 });
  let firstHit = null;
  while (firstHit == null) {
    const n = callNext(l);
    if (n != null && l.playerNumbers.has(n)) firstHit = n;
  }
  callNext(l);                                   // не нажали вовремя
  assert.equal(l.missed, 1, 'пропуск засчитан');
  assert.equal(markPlayer(l, firstHit), false, 'задним числом не отметить');
  assert.equal(l.marked.has(firstHit), false);
});

test('лото: чужое число отметить нельзя', () => {
  const l = createLotto({ seed: 11 });
  callNext(l);
  const notMine = [...Array(90)].map((_, i) => i + 1).find((n) => !l.playerNumbers.has(n));
  assert.equal(markPlayer(l, notMine), false);
});

test('лото: прогресс не превышает 15 у любой стороны', () => {
  const l = createLotto({ seed: 3 });
  let guard = 0;
  while (!l.finished && guard++ < 200) {
    const n = callNext(l);
    if (n != null) markPlayer(l, n);
  }
  const p = progress(l);
  assert.ok(p.player <= TO_CLOSE);
  assert.ok(p.rivals.every((r) => r <= TO_CLOSE));
});

test('лото: возврат пропущенного числа даётся один раз и не даёт преимущества', async () => {
  const { recoverMissed, canRecover } = await import('../src/lotto.js');
  const l = createLotto({ seed: 7 });
  // играем невнимательно, чтобы накопились пропуски
  let guard = 0;
  while (l.missed < 2 && guard++ < 90) callNext(l);
  assert.ok(l.missed >= 2, 'пропуски накопились');

  assert.equal(canRecover(l), true);
  const missedBefore = l.missed;
  const markedBefore = l.marked.size;
  const n = recoverMissed(l);

  assert.ok(n != null, 'число возвращено');
  assert.equal(l.marked.has(n), true, 'возвращённое число отмечено');
  assert.equal(l.missed, missedBefore - 1, 'счётчик пропусков уменьшился');
  assert.equal(l.marked.size, markedBefore + 1);
  assert.ok(l.playerNumbers.has(n), 'возвращено именно своё число, а не чужое');

  assert.equal(canRecover(l), false, 'вторая попытка не даётся');
  assert.equal(recoverMissed(l), null);
});

test('лото: возвращать нечего, если ничего не пропущено', async () => {
  const { canRecover, recoverMissed } = await import('../src/lotto.js');
  const l = createLotto({ seed: 9 });
  callNext(l);
  assert.equal(canRecover(l), false);
  assert.equal(recoverMissed(l), null);
});
