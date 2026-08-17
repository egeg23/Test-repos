// Состояние партии и цикл хода.

import * as B from './balance.js';
import * as Susp from './suspicion.js';
import * as Loy from './loyalty.js';
import * as Clk from './clicker.js';
import { pick as pickEvent } from './events.js';
import { mulberry32 } from './rng.js';

export function create(seed = 1) {
  return {
    seed,
    rnd: mulberry32(seed >>> 0),
    turn: 1,
    rankIndex: 0,
    rubles: 0,
    points: B.ACTION_POINTS,
    coversUsed: 0,
    susp: Susp.create(),
    people: Loy.create(),
    clicker: Clk.create(),
    seenEvents: [],
    pending: null,      // событие, ожидающее решения
    log: [],
    finished: false,
    ending: null,
    prologue: null,     // выбор в прологе — всплывёт в финале
  };
}

export const rank = (g) => B.RANKS[g.rankIndex];
export const canAfford = (g, cost) => g.rubles >= cost;

function note(g, text) {
  g.log.unshift({ turn: g.turn, text });
  g.log = g.log.slice(0, 30);
}

// --- честная работа ---
export function click(g) {
  const gain = Clk.click(g.clicker);
  g.rubles += gain;
  return gain;
}

export function watchAd(g, now) {
  const gain = Clk.watchAd(g.clicker, now);
  if (gain) { g.rubles += gain; note(g, `Подработка: +${gain} бублей`); }
  return gain;
}

// --- действия, стоящие очков хода ---
function spend(g, action, cost = 0) {
  const pts = B.ACTION_COSTS[action] ?? 1;
  if (g.points < pts || g.rubles < cost) return false;
  g.points -= pts;
  g.rubles -= cost;
  return true;
}

export function greet(g, id) {
  if (!spend(g, 'greet')) return false;
  const got = Loy.raise(g.people[id], 2, g.turn);
  note(g, got ? 'Зашли поздороваться' : 'Зашли, но чаще уже некуда');
  return true;
}

export function gift(g, id, byTaste) {
  const cost = byTaste ? B.COSTS.giftTaste : B.COSTS.giftPlain;
  if (!spend(g, 'gift', cost)) return false;
  const got = Loy.raise(g.people[id], byTaste ? 6 : 3, g.turn);
  note(g, got ? 'Подарок принят' : 'Подарок принят, но без впечатления');
  return true;
}

export function party(g, guests) {
  if (!spend(g, 'party', B.COSTS.party ?? 6000)) return false;
  for (const id of guests.slice(0, 2)) Loy.raise(g.people[id], 10, g.turn);
  note(g, 'Посидели в бане');
  return true;
}

// Замести след: снимает подозрение, но не листы дела. Ограничено ходами,
// а не деньгами — потому бесконечный кликер и не ускоряет карьеру.
export function coverTracks(g) {
  if (g.coversUsed >= B.COVER_TRACKS_PER_TURN) return false;
  if (!spend(g, 'cover', B.COSTS.coverTracks)) return false;
  g.coversUsed++;
  Susp.relieve(g.susp, B.COVER_TRACKS_RELIEF);
  note(g, 'Бумаги привели в порядок');
  return true;
}

export function runScheme(g, schemeId) {
  const sc = B.SCHEMES.find((s) => s.id === schemeId);
  if (!sc || !spend(g, 'scheme')) return null;
  g.rubles += sc.income;
  Susp.add(g.susp, sc.suspicion, sc.papers);
  note(g, `Схема проведена: +${sc.income} бублей`);
  return sc;
}

// --- события ---
export function resolveEvent(g, optionId) {
  const e = g.pending;
  if (!e) return null;
  const o = e.options.find((x) => x.id === optionId);
  if (!o) return null;
  if ((o.cost || 0) > g.rubles) return null;

  g.rubles -= o.cost || 0;
  Susp.add(g.susp, o.suspicion || 0, o.papers || 0);
  for (const [id, d] of Object.entries(o.loyalty || {})) {
    if (d > 0) Loy.raise(g.people[id], d, g.turn);
    else Loy.lower(g.people[id], -d);
  }
  if (o.blame) { g.people[o.blame].defendant = true; Loy.lower(g.people[o.blame], 20); }
  if (o.demote) g.rankIndex = Math.max(0, g.rankIndex - o.demote);

  note(g, `${e.title}: ${o.label}`);
  g.seenEvents.push(e.id);
  g.pending = null;
  return o;
}

// --- ход ---
export function endTurn(g) {
  if (g.finished || g.pending) return null;

  g.rubles += rank(g).income;

  const hostile = Loy.hostilePenalty(g.people);
  if (hostile.perTurn) Susp.add(g.susp, hostile.perTurn);

  // Проверка ДО распада. Иначе подозрение упирается в потолок, распад тут же
  // стягивает его обратно, и арест не наступает никогда: значение вечно
  // колеблется чуть ниже порога. Приходят в момент пересечения черты,
  // а не после того, как пыль осела.
  if (Susp.isCaught(g.susp)) {
    g.finished = true;
    g.ending = 'caught';
    return { noise: g.susp.turnNoise, caught: true };
  }

  const noise = Susp.endTurn(g.susp);

  g.turn++;
  g.points = B.ACTION_POINTS;
  g.coversUsed = 0;

  const promoted = tryPromote(g);
  const event = maybeEvent(g);
  return { noise, promoted, event, hostile: hostile.signs };
}

export function nextRequirement(g) {
  const next = B.RANKS[g.rankIndex + 1];
  if (!next) return null;
  const req = B.PROMOTION[next.id];
  return {
    rank: next,
    loyaltyNeed: req.loyaltySum,
    loyaltyHave: Loy.totalLoyalty(g.people),
    turnsNeed: req.turns,
    turnsHave: g.turn,
  };
}

function tryPromote(g) {
  const r = nextRequirement(g);
  if (!r) return null;
  if (r.loyaltyHave < r.loyaltyNeed || r.turnsHave < r.turnsNeed) return null;
  g.rankIndex++;
  Susp.add(g.susp, B.PROMOTION_SUSPICION, 0);
  note(g, `Назначены: ${rank(g).name}`);
  return rank(g);
}

function maybeEvent(g) {
  if (g.turn % 3 !== 0) return null;
  const e = pickEvent(rank(g).id, g.turn, g.seenEvents, g.rnd);
  if (e) g.pending = e;
  return e;
}

// --- итог ---
export function score(g) {
  const d = Loy.defendants(g.people);
  const weight = d.reduce((a, x) => a + x.weight, 0);
  return {
    rank: rank(g),
    points: rank(g).id * B.SCORE_PER_RANK - B.SCORE_PER_DEFENDANT * weight,
    defendants: d,
    papers: g.susp.papers,
    turns: g.turn,
  };
}

// Уйти самому — единственный способ закончить партию без списка.
export function resign(g) {
  g.finished = true;
  g.ending = Loy.defendants(g.people).length ? 'quiet_with_list' : 'quiet';
  return score(g);
}
