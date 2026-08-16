import test from 'node:test';
import assert from 'node:assert/strict';
import { median, summarize, distribution, percentile, nextStreak } from '../src/stats.js';
import { decode, encode, has, set, countUnlocked, evaluate, TOTAL } from '../src/achievements.js';

test('медиана для чётного и нечётного числа партий', () => {
  assert.equal(median([]), 0);
  assert.equal(median([7]), 7);
  assert.equal(median([1, 3, 5]), 3);
  assert.equal(median([1, 2, 3, 4]), 3);   // (2+3)/2 = 2.5 -> 3
  assert.equal(median([10, 1, 5]), 5, 'порядок на входе не важен');
});

test('сводка по истории партий', () => {
  const h = [{ score: 10 }, { score: 40 }, { score: 25 }];
  const s = summarize(h);
  assert.equal(s.games, 3);
  assert.equal(s.best, 40);
  assert.equal(s.worst, 10);
  assert.equal(s.median, 25);
  assert.equal(s.last, 25);
  assert.equal(summarize([]), null);
});

test('распределение раскладывает результаты по корзинам', () => {
  const d = distribution([{ score: 5 }, { score: 25 }, { score: 35 }], 20);
  assert.equal(d.length, 2);
  assert.equal(d[0].count, 1);
  assert.equal(d[1].count, 2);
  assert.equal(d.reduce((a, b) => a + b.count, 0), 3, 'ни одна партия не потеряна');
});

test('процентиль требует хотя бы двух партий', () => {
  assert.equal(percentile([{ score: 10 }], 50), null);
  assert.equal(percentile([{ score: 10 }, { score: 20 }], 30), 100);
  assert.equal(percentile([{ score: 10 }, { score: 20 }], 5), 0);
});

test('серия дней: продолжается только при игре подряд', () => {
  assert.equal(nextStreak(0, '', '2026-08-16'), 1, 'первая партия');
  assert.equal(nextStreak(3, '2026-08-15', '2026-08-16'), 4, 'вчера -> продолжение');
  assert.equal(nextStreak(3, '2026-08-16', '2026-08-16'), 3, 'тот же день не наращивает');
  assert.equal(nextStreak(9, '2026-08-13', '2026-08-16'), 1, 'пропуск обнуляет');
  assert.equal(nextStreak(2, '2026-08-31', '2026-09-01'), 3, 'переход через месяц');
  assert.equal(nextStreak(5, '2026-12-31', '2027-01-01'), 6, 'переход через год');
});

test('битовая маска достижений переживает кодирование', () => {
  const bits = decode('');
  assert.equal(countUnlocked(bits), 0);
  set(bits, 0); set(bits, 7); set(bits, 8); set(bits, TOTAL - 1);
  const round = decode(encode(bits));
  assert.ok(has(round, 0) && has(round, 7) && has(round, 8) && has(round, TOTAL - 1));
  assert.equal(countUnlocked(round), 4);
});

test('повреждённое сохранение не роняет коллекцию', () => {
  assert.equal(countUnlocked(decode('не base64 !!!')), 0);
  assert.equal(countUnlocked(decode(null)), 0);
});

test('достижения выдаются один раз и накапливаются', () => {
  const ctx = {
    gamesPlayed: 1, score: 60, fullRows: 1, fullCols: 0, fullDiags: 0,
    rowPoints: 25, colPoints: 0, diagPoints: 0, dailyPlayed: 0, streak: 0,
    usedUndo: true, newBest: true, percentile: null, ascendingFull: 1,
    decadeFive: 0, parityFive: 0, lottoWins: 0, lottoMissed: 1, lottoWon: false,
    improvedBy: 0, rulesActive: 1,
  };
  const first = evaluate('', ctx);
  assert.ok(first.fresh.length > 0, 'первая партия что-то открывает');
  const keys = first.fresh.map((a) => a.key);
  assert.ok(keys.includes('first_game'));
  assert.ok(keys.includes('score_50'));
  assert.ok(!keys.includes('score_100'), 'недостигнутое не выдаётся');

  const second = evaluate(first.encoded, ctx);
  assert.equal(second.fresh.length, 0, 'повторно то же не выдаётся');
  assert.equal(second.unlocked, first.unlocked);
});

test('у достижений уникальные и плотные идентификаторы', async () => {
  const { ACHIEVEMENTS } = await import('../src/achievements.js');
  const ids = ACHIEVEMENTS.map((a) => a.id);
  assert.equal(new Set(ids).size, ids.length, 'нет дублей id');
  assert.deepEqual(ids, [...ids].sort((a, b) => a - b), 'id идут по порядку');
  assert.equal(ids[0], 0);
  assert.equal(ids[ids.length - 1], TOTAL - 1, 'нет дыр в нумерации');
  assert.equal(new Set(ACHIEVEMENTS.map((a) => a.key)).size, TOTAL, 'ключи уникальны');
});
