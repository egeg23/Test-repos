import test from 'node:test';
import assert from 'node:assert/strict';
import { EVENTS, available, pick, freeOption } from '../src/events.js';
import { mulberry32 } from '../src/rng.js';
import { PEOPLE } from '../src/loyalty.js';

test('у каждого события есть выход при нуле бублей', () => {
  // Игрок никогда не должен оказаться заперт без денег: спуск по ступени —
  // это выбор, а не следствие пустого кошелька.
  for (const e of EVENTS) {
    assert.ok(freeOption(e), `событие «${e.title}» не проходится без денег`);
  }
});

test('у каждого события минимум три варианта и все различимы', () => {
  for (const e of EVENTS) {
    assert.ok(e.options.length >= 3, `«${e.title}»: вариантов ${e.options.length}`);
    const ids = e.options.map((o) => o.id);
    assert.equal(new Set(ids).size, ids.length, `«${e.title}»: дублирующиеся id вариантов`);
    for (const o of e.options) {
      assert.ok(o.label && o.label.length > 3, `«${e.title}»: пустая надпись варианта`);
    }
  }
});

test('дешёвые варианты платят подозрением, а не бесплатны', () => {
  // Иначе исчезает размен «скорость покупается риском».
  for (const e of EVENTS) {
    const free = e.options.filter((o) => (o.cost || 0) === 0);
    for (const o of free) {
      const costsSomething = (o.suspicion || 0) > 0 || o.demote || o.loyalty || o.blame;
      assert.ok(costsSomething,
        `«${e.title}» / «${o.label}»: бесплатно и без последствий — доминирующая стратегия`);
    }
  }
});

test('события ссылаются только на существующих людей', () => {
  const ids = PEOPLE.map((p) => p.id);
  for (const e of EVENTS) {
    if (e.requires?.person) assert.ok(ids.includes(e.requires.person), `${e.id}: нет такого лица`);
    for (const o of e.options) {
      for (const who of Object.keys(o.loyalty || {})) {
        assert.ok(ids.includes(who), `${e.id}/${o.id}: лояльность несуществующему «${who}»`);
      }
      if (o.blame) assert.ok(ids.includes(o.blame), `${e.id}/${o.id}: вина на несуществующего`);
    }
  }
});

test('на стартовой ступени есть из чего выбирать', () => {
  const pool = available(5, 1, []);
  assert.ok(pool.length >= 3, `на ступени 5 доступно всего ${pool.length} событий`);
});

test('выбор события детерминирован по сиду и не повторяется', () => {
  const rnd = mulberry32(42);
  const seen = [];
  for (let i = 0; i < EVENTS.length; i++) {
    const e = pick(9, i, seen, rnd);
    assert.ok(e, `на шаге ${i} пул опустел раньше времени`);
    assert.ok(!seen.includes(e.id), 'событие повторилось');
    seen.push(e.id);
  }
  assert.equal(pick(9, 99, seen, rnd), null, 'исчерпанный пул возвращает null, а не падает');
});

test('спуск по ступени встречается, но не в каждом событии', () => {
  const withDemote = EVENTS.filter((e) => e.options.some((o) => o.demote));
  assert.ok(withDemote.length >= 1, 'спуск должен быть возможен');
  assert.ok(withDemote.length < EVENTS.length, 'спуск в каждом событии — однообразно');
});
