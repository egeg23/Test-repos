import test from 'node:test';
import assert from 'node:assert/strict';
import { makeBoard, PRESETS, growRegions, specKey } from '../src/units.js';
import { countSolutions } from '../src/solver.js';
import { grade, nextStep, TECHNIQUES } from '../src/techniques.js';
import { generate } from '../src/generator.js';
import { mulberry32 } from '../src/rng.js';

const NAMES = Object.keys(PRESETS);

test('поле каждого варианта структурно корректно', () => {
  for (const v of NAMES) {
    const b = makeBoard(v, mulberry32(1));
    for (const u of b.units) {
      assert.equal(u.length, b.n, `${v}: область не из ${b.n} клеток`);
      assert.equal(new Set(u).size, b.n, `${v}: клетка повторяется в области`);
    }
    for (let c = 0; c < b.cells; c++) {
      assert.ok(b.unitsOf[c].length, `${v}: клетка ${c} вне областей`);
    }
  }
});

test('кривые области связны и по девять клеток', () => {
  for (let seed = 0; seed < 12; seed++) {
    const regs = growRegions(mulberry32(seed));
    assert.equal(regs.length, 9);
    for (const r of regs) {
      assert.equal(r.length, 9, `сид ${seed}: область из ${r.length} клеток`);
      // Обход по четырём сторонам обязан покрыть всю область.
      const set = new Set(r), seen = new Set([r[0]]), stack = [r[0]];
      while (stack.length) {
        const c = stack.pop(), row = Math.floor(c / 9), col = c % 9;
        for (const [dr, dc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          const nr = row + dr, nc = col + dc;
          if (nr < 0 || nc < 0 || nr > 8 || nc > 8) continue;
          const p = nr * 9 + nc;
          if (set.has(p) && !seen.has(p)) { seen.add(p); stack.push(p); }
        }
      }
      assert.equal(seen.size, 9, `сид ${seed}: область разорвана`);
    }
    // Все 81 клетка розданы ровно один раз.
    assert.equal(new Set(regs.flat()).size, 81);
  }
});

test('у выданной задачи решение единственно', () => {
  for (const v of NAMES) {
    for (const band of ['easy', 'medium']) {
      const r = generate(v, band, mulberry32(v.length * 13 + band.length));
      assert.ok(r, `${v}/${band}: задача не сгенерирована`);
      assert.equal(countSolutions(makeBoardFor(r), r.puzzle, 3).count, 1,
        `${v}/${band}: решений не одно`);
    }
  }
});

// Поле восстанавливаем из областей задачи: у кривых областей нарезка своя
// на каждую задачу, и заново её не сгенерировать.
function makeBoardFor(r) {
  const n = r.n;
  const units = r.units;
  const unitsOf = [...Array(n * n)].map(() => []);
  units.forEach((u) => u.forEach((c) => unitsOf[c].push(u)));
  const peers = [...Array(n * n)].map((_, c) => {
    const s = new Set();
    unitsOf[c].forEach((u) => u.forEach((x) => { if (x !== c) s.add(x); }));
    return [...s];
  });
  return { spec: r.spec, variant: r.spec.regions === 'jigsaw' ? 'jigsaw' : 'boxes',
           key: r.key, n, cells: n * n, units, unitSets: units.map((u) => new Set(u)),
           unitsOf, peers, full: (1 << n) - 1 };
}

test('заявленная сложность настоящая: ниже уровнем задача не решается', () => {
  // Главная гарантия проекта. В каталоге «сложные» задачи сплошь и рядом
  // закрываются одними одиночками — у нас это падающий тест.
  for (const v of NAMES) {
    for (const band of ['easy', 'medium', 'hard']) {
      const r = generate(v, band, mulberry32(v.length * 71 + band.length * 3));
      if (!r) continue;
      const b = makeBoardFor(r);
      assert.ok(grade(b, r.puzzle).solved, `${v}/${band}: не решается техниками вовсе`);
      if (r.level > 1) {
        assert.equal(grade(b, r.puzzle, r.level - 1).solved, false,
          `${v}/${band}: заявлен уровень ${r.level}, а хватает ${r.level - 1}`);
      }
    }
  }
});

test('подсказка не может расходиться с решением', () => {
  // Инвариант проекта: если интерфейс что-то обещает игроку, это тот же код,
  // что и результат. Подсказка, ставящая цифру мимо решения, — худший баг.
  for (const v of NAMES) {
    const r = generate(v, 'medium', mulberry32(v.length * 101));
    assert.ok(r);
    const b = makeBoardFor(r);
    const grid = r.puzzle.slice();
    let steps = 0;
    while (grid.some((x) => !x)) {
      const s = nextStep(b, grid);
      assert.ok(s, `${v}: подсказка кончилась на незаполненной сетке`);
      if (s.place != null) {
        assert.equal(s.value, r.solution[s.place],
          `${v}: подсказка ставит ${s.value} в ${s.place}, в решении ${r.solution[s.place]}`);
        grid[s.place] = s.value;
      } else {
        // Исключения тоже обязаны быть верными: убираемое значение не должно
        // стоять в решении.
        for (const e of s.eliminations) {
          assert.notEqual(r.solution[e.cell], e.value,
            `${v}: подсказка убирает верное значение из ${e.cell}`);
        }
        grid[s.place ?? -1] = grid[s.place ?? -1];
        // Исключения не двигают сетку — доигрываем размещением.
        const forced = nextStep(b, grid);
        if (forced && forced.place != null) grid[forced.place] = forced.value;
        else break;
      }
      assert.ok(++steps < 400, `${v}: подсказки зациклились`);
    }
  }
});

test('у каждой подсказки есть человеческое объяснение', () => {
  const b = makeBoard('classic', mulberry32(2));
  const r = generate('classic', 'hard', mulberry32(5));
  const s = nextStep(b, r.puzzle);
  assert.ok(s.text.length > 30, 'объяснение слишком короткое');
  assert.ok(/[а-яё]/i.test(s.text), 'объяснение не по-русски');
  assert.ok(TECHNIQUES.some((t) => t.key === s.technique));
});

test('объяснения не ломают падежи', () => {
  // «из остальных клеток столбце 3» — ровно то, что тут ловится.
  const b = makeBoard('classic', mulberry32(2));
  const bad = [/клеток (строке|столбце|этом блоке)/, /части (строке|столбце|этом блоке)/];
  let checked = 0;
  for (let seed = 0; seed < 25; seed++) {
    const r = generate('classic', 'hard', mulberry32(seed * 17), 4);
    if (!r) continue;
    const grid = r.puzzle.slice();
    for (let k = 0; k < 120 && grid.some((x) => !x); k++) {
      const s = nextStep(b, grid);
      if (!s) break;
      for (const re of bad) assert.ok(!re.test(s.text), `падеж: «${s.text}»`);
      checked++;
      if (s.place != null) grid[s.place] = s.value; else break;
    }
  }
  assert.ok(checked > 50, `проверено всего ${checked} объяснений — мало`);
});

test('порог подсказок соблюдается', () => {
  // Ползунок обещает «не меньше N подсказок». Если движок снимет больше —
  // интерфейс соврал игроку, а это наш худший класс бага.
  for (const min of [30, 40, 50]) {
    const r = generate({ size: 9, regions: 'boxes' }, 'easy', mulberry32(min * 3), { minClues: min });
    assert.ok(r, `порог ${min}: задача не сгенерирована`);
    assert.ok(r.clues >= min, `порог ${min}, а подсказок ${r.clues}`);
  }
});

test('симметрия расположения подсказок настоящая', () => {
  const maps = {
    central:    (n, r, q) => [n - 1 - r, n - 1 - q],
    horizontal: (n, r, q) => [n - 1 - r, q],
    vertical:   (n, r, q) => [r, n - 1 - q],
    diagonal:   (n, r, q) => [q, r],
  };
  for (const [key, map] of Object.entries(maps)) {
    const res = generate({ size: 9, regions: 'boxes' }, 'medium', mulberry32(key.length * 41),
      { symmetry: key });
    assert.ok(res, `${key}: задача не сгенерирована`);
    const n = res.n;
    for (let c = 0; c < n * n; c++) {
      const [r2, q2] = map(n, Math.floor(c / n), c % n);
      const mirror = r2 * n + q2;
      assert.equal(Boolean(res.puzzle[c]), Boolean(res.puzzle[mirror]),
        `${key}: клетка ${c} и её зеркало ${mirror} расходятся`);
    }
  }
});

test('невозможные наборы правил отбиваются, а не молча портят поле', () => {
  assert.throws(() => makeBoard({ size: 6, hyper: true }), /гипер/);
  assert.throws(() => makeBoard({ size: 7 }), /размер/);
  assert.throws(() => makeBoard('нет такого'), /неизвестные правила/);
  assert.equal(specKey({ size: 9, regions: 'jigsaw', diagonal: true }), '9x9-jigsaw-diag');
});
