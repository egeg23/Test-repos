import test from 'node:test';
import assert from 'node:assert/strict';
import * as G from '../src/state.js';
import * as B from '../src/balance.js';
import * as Loy from '../src/loyalty.js';

const fresh = (seed = 1) => G.create(seed);

test('повышение не выдаётся на первом же ходу', () => {
  // Пороги обязаны быть выше стартовой суммы лояльности, иначе игрок
  // получает следующую ступень, ничего не сделав.
  const g = fresh();
  const start = Loy.totalLoyalty(g.people);
  const req = G.nextRequirement(g);
  assert.ok(req.loyaltyNeed > start,
    `порог ${req.loyaltyNeed} не выше стартовых ${start} — повышение мгновенное`);
});

test('бубли не покупают ранг', () => {
  const g = fresh();
  g.rubles = 100_000_000;
  for (let i = 0; i < 60; i++) G.endTurn(g);
  assert.equal(g.rankIndex, 0,
    'ранг вырос от одних денег — бесконечный кликер ломает игру');
});

test('очки хода ограничивают действия, а деньги — нет', () => {
  const g = fresh();
  g.rubles = 10_000_000;
  let done = 0;
  while (G.greet(g, 'alla')) done++;
  assert.equal(done, B.ACTION_POINTS, `сделано ${done} действий при ${B.ACTION_POINTS} очках`);
});

test('«замести след» ограничено ходом, а не кошельком', () => {
  const g = fresh();
  g.rubles = 10_000_000;
  let used = 0;
  while (G.coverTracks(g)) used++;
  assert.equal(used, Math.min(B.COVER_TRACKS_PER_TURN, B.ACTION_POINTS));
});

test('жадная схема кормит, но топит', () => {
  const g = fresh();
  const before = g.susp.value;
  const sc = G.runScheme(g, 'greedy');
  assert.ok(sc && g.rubles >= sc.income);
  assert.ok(g.susp.value > before, 'жадная схема обязана поднимать подозрение');
  assert.ok(g.susp.papers > 0, 'и оставлять листы дела');
});

test('осторожная схема шумит заметно меньше жадной', () => {
  const careful = B.SCHEMES.find((s) => s.id === 'careful');
  const greedy = B.SCHEMES.find((s) => s.id === 'greedy');
  assert.ok(greedy.suspicion > careful.suspicion * 3,
    'разница между осторожно и жадно должна быть кратной, иначе выбора нет');
});

test('партия заканчивается арестом при переполнении подозрения', () => {
  const g = fresh();
  for (let i = 0; i < 200 && !g.finished; i++) {
    if (g.pending) G.resolveEvent(g, g.pending.options[0].id);
    G.runScheme(g, 'greedy');
    G.endTurn(g);
  }
  assert.ok(g.finished, 'жадная игра обязана кончиться');
  assert.equal(g.ending, 'caught');
});

test('осторожная игра до ареста не доходит', () => {
  const g = fresh(7);
  for (let i = 0; i < 120 && !g.finished; i++) {
    if (g.pending) {
      const free = g.pending.options.find((o) => !(o.cost > 0) && !o.demote) || g.pending.options[0];
      G.resolveEvent(g, free.id);
    }
    G.endTurn(g);
  }
  assert.equal(g.finished, false, 'ничего не нарушая, сесть нельзя');
});

test('уйти самому без фигурантов даёт тихий уход', () => {
  const g = fresh();
  const s = G.resign(g);
  assert.equal(g.ending, 'quiet');
  assert.equal(s.defendants.length, 0);
  assert.equal(s.points, B.RANKS[0].id * B.SCORE_PER_RANK);
});

test('счёт падает за каждого утащенного, а тёща весит вдвое', () => {
  const a = fresh(); a.people.garik.defendant = true;
  const b = fresh(); b.people.roza.defendant = true;
  assert.equal(G.score(a).points, B.RANKS[0].id * B.SCORE_PER_RANK - B.SCORE_PER_DEFENDANT);
  assert.equal(G.score(b).points, B.RANKS[0].id * B.SCORE_PER_RANK - 2 * B.SCORE_PER_DEFENDANT,
    'она не знала — потому и весит вдвое');
});

// Игрок всегда выбирает вариант, который может себе позволить — иначе
// разрешение молча проваливается и ход блокируется навсегда.
const affordable = (g) =>
  g.pending.options.find((o) => (o.cost || 0) <= g.rubles) || null;

test('партия детерминирована по сиду', () => {
  const run = (seed) => {
    const g = G.create(seed);
    const ids = [];
    for (let i = 0; i < 60 && !g.finished; i++) {
      if (g.pending) { ids.push(g.pending.id); G.resolveEvent(g, affordable(g).id); }
      G.endTurn(g);
    }
    return ids;
  };
  assert.deepEqual(run(123), run(123), 'один сид — одна партия');
  const a = run(11), b = run(4242);
  assert.notDeepEqual(a, b, 'разные сиды обязаны расходиться');
});

test('игра не заходит в тупик: у нерешённого события всегда есть посильный вариант', () => {
  // Самый опасный класс ошибок: событие, которое нечем закрыть. Ход не
  // заканчивается, игра застывает намертво. Проверяем при нулевом балансе.
  for (let seed = 1; seed <= 50; seed++) {
    const g = G.create(seed);
    for (let i = 0; i < 60 && !g.finished; i++) {
      if (g.pending) {
        g.rubles = 0;                       // худший случай: денег нет вовсе
        const out = affordable(g);
        assert.ok(out, `сид ${seed}: событие «${g.pending.title}» нечем закрыть`);
        assert.ok(G.resolveEvent(g, out.id), 'посильный вариант обязан проходить');
      }
      G.endTurn(g);
    }
  }
});

test('ход не блокируется навсегда', () => {
  const g = G.create(3);
  let advanced = 0;
  const start = g.turn;
  for (let i = 0; i < 80 && !g.finished; i++) {
    if (g.pending) G.resolveEvent(g, affordable(g).id);
    if (G.endTurn(g)) advanced++;
  }
  assert.ok(g.turn > start + 20, `за 80 итераций ход дошёл только до ${g.turn}`);
});

test('событие блокирует конец хода, пока не решено', () => {
  const g = fresh();
  while (!g.pending && g.turn < 30) G.endTurn(g);
  assert.ok(g.pending, 'события должны появляться');
  const before = g.turn;
  assert.equal(G.endTurn(g), null, 'ход не заканчивается с нерешённым событием');
  assert.equal(g.turn, before);
});
