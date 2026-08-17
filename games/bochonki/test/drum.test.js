import test from 'node:test';
import assert from 'node:assert/strict';
import { createGame, pick, place, currentBarrel, bestDelta, score, reroll, POOL, CANDS, TURNS } from '../src/drum.js';
import { SIZE, EMPTY, emptyCells, isFull, scoreGrid } from '../src/scoring.js';

const fresh = (seed = 1, played = 5) => createGame({ seed, gamesPlayed: played });

test('барабан сразу выкатывает три бочонка', () => {
  const g = fresh();
  assert.equal(g.cands.length, CANDS);
  assert.equal(new Set(g.cands).size, CANDS, 'кандидаты не повторяются');
  assert.equal(currentBarrel(g), null, 'до выбора в руке пусто');
});

test('нельзя ставить, пока бочонок не выбран', () => {
  const g = fresh();
  assert.equal(place(g, 0, 0), null);
});

test('пропущенные бочонки возвращаются в мешок, а не исчезают', () => {
  const g = fresh(3);
  const before = [...g.cands];
  const poolBefore = g.pool.length;
  const taken = pick(g, 1);

  assert.equal(taken, before[1]);
  assert.equal(currentBarrel(g), before[1]);
  // из мешка ушли трое, двое вернулись — итого минус один
  assert.equal(g.pool.length, poolBefore - 1);
  assert.equal(g.skipped, 2);
  const skipped = before.filter((_, i) => i !== 1);
  for (const v of skipped) assert.ok(g.pool.includes(v), `бочонок ${v} потерян`);
  assert.ok(!g.pool.includes(taken), 'взятый бочонок остался в мешке');
});

test('партия доигрывается ровно до заполнения поля', () => {
  for (let seed = 1; seed <= 60; seed++) {
    const g = fresh(seed);
    let guard = 0;
    while (!g.finished && guard++ < 200) {
      assert.ok(g.cands.length > 0, 'барабан не выкатил кандидатов');
      pick(g, guard % g.cands.length);
      const free = emptyCells(g.grid);
      place(g, free[0][0], free[0][1]);
    }
    assert.ok(g.finished, `сид ${seed}: партия не завершилась`);
    assert.equal(g.placements.length, TURNS);
    assert.ok(isFull(g.grid), 'поле заполнено');
  }
});

test('подсказка кандидата не расходится с реальной постановкой', () => {
  // bestDelta обещает максимум по полю — проверяем, что он достижим.
  for (let seed = 1; seed <= 40; seed++) {
    const g = fresh(seed);
    let guard = 0;
    while (!g.finished && guard++ < 100) {
      const cand = g.cands[0];
      const promised = bestDelta(g, cand);
      pick(g, 0);

      let actualBest = null;
      for (const [r, c] of emptyCells(g.grid)) {
        const before = scoreGrid(g.grid, g.rules);
        g.grid[r][c] = cand;
        const after = scoreGrid(g.grid, g.rules);
        g.grid[r][c] = EMPTY;
        const d = after - before;
        if (actualBest === null || d > actualBest) actualBest = d;
      }
      assert.equal(promised, actualBest, `сид ${seed}: обещано ${promised}, достижимо ${actualBest}`);

      const free = emptyCells(g.grid);
      place(g, free[0][0], free[0][1]);
    }
  }
});

test('сумма дельт постановок равна итоговому счёту', () => {
  for (let seed = 1; seed <= 100; seed++) {
    const g = fresh(seed);
    let predicted = 0, guard = 0;
    while (!g.finished && guard++ < 100) {
      pick(g, guard % g.cands.length);
      const free = emptyCells(g.grid);
      const [r, c] = free[Math.floor(g.rnd() * free.length)];
      predicted += place(g, r, c).delta;
    }
    assert.equal(predicted, score(g).total, `сид ${seed}`);
  }
});

test('партия детерминирована по сиду', () => {
  const a = fresh(99), b = fresh(99);
  assert.deepEqual(a.cands, b.cands);
  pick(a, 0); pick(b, 0);
  place(a, 0, 0); place(b, 0, 0);
  assert.deepEqual(a.cands, b.cands, 'после хода барабан выдал то же самое');
});

test('мешок не пустеет раньше конца партии', () => {
  for (let seed = 1; seed <= 30; seed++) {
    const g = fresh(seed);
    let guard = 0;
    while (!g.finished && guard++ < 100) {
      assert.ok(g.cands.length >= 1, `сид ${seed}: мешок опустел на ходу ${g.placements.length}`);
      pick(g, 0);
      const free = emptyCells(g.grid);
      place(g, free[0][0], free[0][1]);
    }
    assert.equal(g.placements.length, TURNS);
  }
});

test('выбор из трёх реально даёт преимущество над случайным', () => {
  // Жадный по подсказке игрок должен стабильно обыгрывать берущего первого попавшегося.
  let greedyTotal = 0, blindTotal = 0;
  for (let seed = 1; seed <= 40; seed++) {
    for (const greedy of [true, false]) {
      const g = fresh(seed);
      let guard = 0;
      while (!g.finished && guard++ < 100) {
        let idx = 0;
        if (greedy) {
          let best = -Infinity;
          g.cands.forEach((v, i) => { const d = bestDelta(g, v); if (d > best) { best = d; idx = i; } });
        }
        const value = g.cands[idx];
        pick(g, idx);
        // ставим в лучшую клетку в обоих случаях — сравниваем именно выбор бочонка
        let bestCell = null, bestD = -Infinity;
        for (const [r, c] of emptyCells(g.grid)) {
          const before = scoreGrid(g.grid, g.rules);
          g.grid[r][c] = value;
          const d = scoreGrid(g.grid, g.rules) - before;
          g.grid[r][c] = EMPTY;
          if (d > bestD) { bestD = d; bestCell = [r, c]; }
        }
        place(g, bestCell[0], bestCell[1]);
      }
      if (greedy) greedyTotal += score(g).total; else blindTotal += score(g).total;
    }
  }
  assert.ok(greedyTotal > blindTotal,
    `выбор должен что-то значить: осознанный ${greedyTotal}, случайный ${blindTotal}`);
  console.log(`      осознанный выбор ${greedyTotal} против случайного ${blindTotal} за 40 партий`);
});

test('перекат барабана: одна попытка за партию, тройка меняется', () => {
  const g = fresh(21);
  const before = [...g.cands];
  const poolBefore = g.pool.length;
  assert.equal(reroll(g), true);
  assert.equal(g.rerollUsed, true);
  assert.equal(g.cands.length, 3);
  assert.notDeepEqual(g.cands, before, 'выкатилась новая тройка');
  // cands — это первые элементы самого мешка, а не отдельная копия,
  // поэтому считаем только мешок: перекат ничего не отнимает и не добавляет.
  assert.equal(g.pool.length, poolBefore, 'перекат изменил размер мешка');
  const alive = new Set(g.pool);
  for (const v of before) assert.ok(alive.has(v), `бочонок ${v} пропал при перекате`);
  assert.equal(new Set(g.pool).size, g.pool.length, 'в мешке появились дубликаты');
  assert.equal(reroll(g), false, 'вторая попытка не даётся');
});

test('перекат недоступен после выбора бочонка', () => {
  const g = fresh(22);
  pick(g, 0);
  assert.equal(reroll(g), false);
});
