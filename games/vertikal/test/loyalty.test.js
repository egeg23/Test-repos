import test from 'node:test';
import assert from 'node:assert/strict';
import * as L from '../src/loyalty.js';
import { LOYALTY_CAP, LOYALTY_WINDOW } from '../src/balance.js';

test('полосы лояльности покрывают весь диапазон без дыр', () => {
  const seen = new Set();
  for (let v = 0; v <= 100; v++) {
    const b = L.band(v);
    assert.ok(b, `нет полосы для ${v}`);
    seen.add(b);
  }
  assert.equal(seen.size, 5, 'должно быть ровно пять полос');
});

test('потолок роста не даёт купить связь за один ход', () => {
  const map = L.create();
  const p = map.alla;
  let total = 0;
  for (let i = 0; i < 20; i++) total += L.raise(p, 6, 1);
  assert.equal(total, LOYALTY_CAP, `за один ход подняли ${total}, потолок ${LOYALTY_CAP}`);
});

test('потолок отпускает через отведённое окно', () => {
  const map = L.create();
  const p = map.alla;
  L.raise(p, LOYALTY_CAP, 1);
  assert.equal(L.raise(p, 6, 1), 0, 'в том же ходу больше нельзя');
  assert.ok(L.raise(p, 6, 1 + LOYALTY_WINDOW) > 0, 'через окно снова можно');
});

test('пассивного затухания нет', () => {
  const map = L.create();
  const before = map.proshkin.value;
  // «прошло» сто ходов, игрок ничего не делал
  for (let t = 1; t <= 100; t++) L.headroom(map.proshkin, t);
  assert.equal(map.proshkin.value, before,
    'лояльность не должна падать сама — иначе игра наказывает за отсутствие');
});

test('предупреждение улучшается по полосам, а не скачком', () => {
  const q0 = L.warningQuality(10);
  const q1 = L.warningQuality(40);
  const q2 = L.warningQuality(60);
  const q3 = L.warningQuality(80);
  assert.equal(q0.warns, false, 'враг не предупреждает');
  assert.deepEqual([q1.warns, q1.type], [true, false], 'ровно — только «что-то будет»');
  assert.deepEqual([q2.warns, q2.type, q2.turn], [true, true, false], 'свой — с типом');
  assert.deepEqual([q3.type, q3.turn, q3.price], [true, true, true], 'ближний круг — всё');
});

test('враждебность вредит предсказуемо и с видимым признаком', () => {
  const map = L.create();
  assert.equal(L.hostilePenalty(map).perTurn, 0, 'на старте никто не вредит');
  map.alla.value = 5;
  const h = L.hostilePenalty(map);
  assert.ok(h.perTurn > 0);
  assert.ok(h.signs.includes('alla'), 'у вреда обязан быть видимый источник');
});

test('родственница весит вдвое в списке фигурантов', () => {
  const map = L.create();
  map.roza.defendant = true;
  map.garik.defendant = true;
  const d = L.defendants(map);
  assert.equal(d.length, 2);
  assert.equal(d.find((x) => x.id === 'roza').weight, 2, 'она не знала');
  assert.equal(d.find((x) => x.id === 'garik').weight, 1);
});

test('сумма лояльности не учитывает родню', () => {
  const map = L.create();
  const before = L.totalLoyalty(map);
  map.roza.value = 100;
  assert.equal(L.totalLoyalty(map), before, 'тёща не двигает карьеру');
});
