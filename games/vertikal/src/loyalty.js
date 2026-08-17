// Связи. Лояльность даёт не скидку, а зрение: свой человек предупреждает
// о том, чего игрок не видит. Низкая лояльность не блокирует игру,
// а лишает подсказок — играть приходится ещё более вслепую.

import { LOYALTY_BANDS, LOYALTY_CAP, LOYALTY_WINDOW } from './balance.js';

// Ростер тизера. Полный состав — в патчах; здесь только те, кто нужен,
// чтобы механика прочиталась за первые десять минут.
export const PEOPLE = [
  { id: 'alla',    name: 'Аллочка',    role: 'секретарь канцелярии', taste: 'attention', start: 40 },
  { id: 'proshkin',name: 'Прошкин',    role: 'приглядчик',           taste: 'order',     start: 40 },
  { id: 'garik',   name: 'Гарик Плащ', role: 'решала',               taste: 'money',     start: 40 },
  { id: 'hvat',    name: 'Хват',       role: 'соперник',             taste: null,        start: 50 },
  { id: 'roza',    name: 'Роза Марковна', role: 'тёща',              taste: 'family',    start: 60, kin: true },
];

export function create() {
  const map = {};
  for (const p of PEOPLE) {
    map[p.id] = { id: p.id, value: p.start, gained: [], defendant: false };
  }
  return map;
}

export function band(value) {
  for (const b of LOYALTY_BANDS) if (value >= b.from && value <= b.to) return b.key;
  return LOYALTY_BANDS[0].key;
}

// Потолок роста: не более LOYALTY_CAP за LOYALTY_WINDOW ходов на одну связь.
// Единственный шлюз, и он временной, а не денежный: купить сто подарков
// и поднять связь с нуля до ста за один ход нельзя.
export function headroom(person, turn) {
  const recent = person.gained.filter((g) => turn - g.turn < LOYALTY_WINDOW);
  const used = recent.reduce((a, g) => a + g.amount, 0);
  return Math.max(0, LOYALTY_CAP - used);
}

export function raise(person, amount, turn) {
  const allowed = Math.min(amount, headroom(person, turn));
  if (allowed <= 0) return 0;
  person.value = Math.min(100, person.value + allowed);
  person.gained.push({ turn, amount: allowed });
  person.gained = person.gained.filter((g) => turn - g.turn < LOYALTY_WINDOW);
  return allowed;
}

// Падение — только от явных действий игрока. Пассивного затухания нет:
// не заходил пять ходов — вернулся к тем же цифрам. Наказывать игрока
// за то, что он живёт своей жизнью, мы не будем.
export function lower(person, amount) {
  person.value = Math.max(0, person.value - Math.max(0, amount));
  return person.value;
}

// Качество предупреждения по полосе. Это и есть «развитие персонажа»:
// один человек говорит по-разному на разных полосах.
export function warningQuality(value) {
  switch (band(value)) {
    case 'inner':   return { warns: true, type: true, turn: true, price: true };
    case 'friend':  return { warns: true, type: true, turn: false, price: false };
    case 'neutral': return { warns: true, type: false, turn: false, price: false };
    default:        return { warns: false, type: false, turn: false, price: false };
  }
}

// Персональный «эффект нуля»: враждебная связь вредит, но предсказуемо
// и с видимым признаком. Врать игроку о скрытых числах мы не будем —
// это генератор единиц в отзывах.
export function hostilePenalty(map) {
  let perTurn = 0;
  const signs = [];
  if (map.alla.value <= 14)     { perTurn += 3; signs.push('alla'); }
  if (map.hvat.value < 30)      { perTurn += 2; signs.push('hvat'); }
  return { perTurn, signs };
}

export function totalLoyalty(map) {
  return PEOPLE.filter((p) => !p.kin)
    .reduce((a, p) => a + map[p.id].value, 0);
}

export function defendants(map) {
  return PEOPLE.filter((p) => map[p.id].defendant)
    .map((p) => ({ id: p.id, name: p.name, weight: p.kin ? 2 : 1 }));
}
