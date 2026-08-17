import test from 'node:test';
import assert from 'node:assert/strict';
import { trim, saveSize, MAX_SAVE_BYTES, HISTORY_LIMIT, DEFAULT_SAVE } from '../src/storage.js';

test('сохранение укладывается в лимит платформы в 200 КБ', () => {
  const full = {
    ...DEFAULT_SAVE,
    gamesPlayed: 9999, best: 311, streak: 365,
    achievements: 'AAAAAAAA',
    history: Array.from({ length: HISTORY_LIMIT }, (_, i) =>
      ({ score: 300 - i, day: '2026-08-16', mode: 'drum' })),
    dailyBest: Object.fromEntries(Array.from({ length: 365 }, (_, i) => ['2026-01-' + i, 250])),
  };
  const size = saveSize(trim(full));
  assert.ok(size <= MAX_SAVE_BYTES, `сохранение ${size} байт при лимите ${MAX_SAVE_BYTES}`);
  console.log(`      реальный размер сохранения: ${size} байт из ${MAX_SAVE_BYTES}`);
});

test('история обрезается до лимита', () => {
  const save = { ...DEFAULT_SAVE, history: Array.from({ length: 500 }, (_, i) => ({ score: i })) };
  const t = trim(save);
  assert.equal(t.history.length, HISTORY_LIMIT);
  assert.equal(t.history[t.history.length - 1].score, 499, 'сохраняются последние партии');
});

test('при переполнении жертвуем статистикой, а не прогрессом', () => {
  // Искусственно раздуваем запись, чтобы сработала аварийная ветка.
  const fat = 'x'.repeat(300 * 1024);
  const save = { ...DEFAULT_SAVE, gamesPlayed: 42, achievements: 'ZZZZ',
                 history: [{ score: 1, note: fat }] };
  const t = trim(save);
  assert.equal(t.history.length, 0, 'история отброшена');
  assert.equal(t.gamesPlayed, 42, 'прогресс сохранён');
  assert.equal(t.achievements, 'ZZZZ', 'коллекция сохранена');
  assert.ok(saveSize(t) <= MAX_SAVE_BYTES);
});

test('trim не портит исходный объект', () => {
  const save = { ...DEFAULT_SAVE, history: Array.from({ length: 100 }, (_, i) => ({ score: i })) };
  const snapshot = JSON.stringify(save);
  trim(save);
  assert.equal(JSON.stringify(save), snapshot);
});
