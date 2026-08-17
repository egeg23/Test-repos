import test from 'node:test';
import assert from 'node:assert/strict';
import * as S from '../src/suspicion.js';
import {
  DECAY_FLAT, DECAY_RATE, SUSPICION_MAX, GAUGE_DELAY,
} from '../src/balance.js';

test('подозрение сходится к расчётному равновесию', () => {
  // Главная формула баланса: S* = (приток - 1) / 0,03.
  // Если она перестанет выполняться, все числа игры поедут разом.
  for (const inflow of [1.5, 2.0, 2.9, 3.5]) {
    const s = S.create();
    for (let i = 0; i < 500; i++) { S.add(s, inflow); S.endTurn(s); }
    const expected = S.equilibrium(inflow);
    assert.ok(Math.abs(s.value - expected) < 2,
      `приток ${inflow}: ожидалось ${expected.toFixed(1)}, получено ${s.value.toFixed(1)}`);
  }
});

test('жадный игрок обречён, осторожный живёт вечно', () => {
  const greedy = S.equilibrium(4.0);
  const careful = S.equilibrium(2.0);
  assert.ok(greedy >= SUSPICION_MAX, `приток 4,0 обязан упираться в потолок, дал ${greedy}`);
  assert.ok(careful < 40, `приток 2,0 должен быть безопасным, дал ${careful}`);
});

test('подозрение не выходит за границы', () => {
  const s = S.create();
  S.add(s, 1e6);
  assert.equal(s.value, SUSPICION_MAX);
  S.relieve(s, 1e6);
  assert.equal(s.value, 0);
  S.decay(s);
  assert.ok(s.value >= 0, 'распад не уводит ниже нуля');
});

test('метка шума считается из того же числа, что применяется к подозрению', () => {
  const cases = [[0,'silent'], [1,'quiet'], [4,'quiet'], [5,'noticeable'],
                 [9,'noticeable'], [10,'loud'], [19,'loud'], [20,'blaring'], [99,'blaring']];
  for (const [noise, label] of cases) {
    assert.equal(S.noiseLabel(noise), label, `шум ${noise}`);
  }
  const s = S.create();
  S.add(s, 7);
  assert.equal(S.noiseLabel(s.turnNoise), 'noticeable', 'метка берётся из накопленного шума хода');
});

test('листы дела не убывают никогда', () => {
  const s = S.create();
  S.add(s, 5, 2);
  S.add(s, 5, 1);
  assert.equal(s.papers, 3);
  S.relieve(s, 100);
  assert.equal(s.papers, 3, '«замести след» не стирает того, что было');
  S.decay(s);
  assert.equal(s.papers, 3);
});

test('косвенная шкала показывает прошлое, а не настоящее', () => {
  const s = S.create();
  // Резкий скачок подозрения не должен мгновенно отражаться на шкале.
  for (let i = 0; i < GAUGE_DELAY; i++) { S.endTurn(s); }
  const before = S.gauge(s);
  S.add(s, 90);
  S.endTurn(s);
  assert.equal(S.gauge(s), before, 'шкала не выдаёт скачок в тот же ход');
});

test('шкала догоняет за отведённую задержку', () => {
  const s = S.create();
  S.add(s, 95);
  for (let i = 0; i <= GAUGE_DELAY + 1; i++) S.endTurn(s);
  assert.ok(S.gauge(s) >= 3, 'через задержку высокое подозрение обязано проявиться');
});

test('точное подозрение по шкале не вычисляется', () => {
  // Игрок не должен уметь восстановить S дифференцированием шкалы:
  // за партию делений должно смениться сильно меньше, чем ходов.
  const s = S.create();
  const seen = [];
  for (let t = 0; t < 50; t++) {
    S.add(s, 2 + (t % 3));
    S.endTurn(s);
    seen.push(S.gauge(s));
  }
  const changes = seen.filter((v, i) => i > 0 && v !== seen[i - 1]).length;
  assert.ok(changes < 12, `шкала сменилась ${changes} раз за 50 ходов — это уже читаемо`);
});
