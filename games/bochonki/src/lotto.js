// Классическое русское лото — узнаваемый вход в игру.
//
// Ведущий достаёт бочонки по одному. Соперники отмечают свои числа безошибочно,
// игрок обязан успеть нажать до следующего бочонка: пропущенное число уже
// не отметить. Напряжение здесь — во внимании, ровно как за настоящим столом.

import { mulberry32, shuffle } from './rng.js';
import { makeCard, cardNumbers } from './lottoCard.js';

export const TO_CLOSE = 15;

export function createLotto({ seed, rivals = 2 }) {
  const rnd = mulberry32((seed >>> 0) + 1);
  const bag = shuffle(Array.from({ length: 90 }, (_, i) => i + 1), rnd);

  const playerCard = makeCard(seed);
  const rivalCards = [];
  for (let i = 0; i < rivals; i++) rivalCards.push(makeCard(seed + 1000 * (i + 1)));

  return {
    bag,
    index: -1,
    playerCard,
    playerNumbers: new Set(cardNumbers(playerCard)),
    marked: new Set(),
    rivalCards,
    rivalNumbers: rivalCards.map((c) => new Set(cardNumbers(c))),
    rivalMarked: rivalCards.map(() => new Set()),
    called: [],
    pending: null,       // число, которое игрок ещё может отметить
    missed: 0,
    finished: false,
    result: null,        // 'player' | 'rival'
  };
}

export function current(l) {
  return l.index >= 0 && l.index < l.bag.length ? l.bag[l.index] : null;
}

// Достать следующий бочонок. Не отмеченное вовремя число уходит в пропущенные.
export function callNext(l) {
  if (l.finished) return null;

  if (l.pending != null && !l.marked.has(l.pending)) {
    l.missed++;
    l.pending = null;
  }

  l.index++;
  const n = current(l);
  if (n == null) { l.finished = true; l.result = decideOnExhaust(l); return null; }

  l.called.push(n);
  l.pending = l.playerNumbers.has(n) ? n : null;

  // Соперники отмечают сразу.
  l.rivalNumbers.forEach((set, i) => { if (set.has(n)) l.rivalMarked[i].add(n); });

  checkWin(l);
  return n;
}

export function markPlayer(l, n) {
  if (l.finished) return false;
  if (l.pending !== n) return false;      // только текущий бочонок
  if (!l.playerNumbers.has(n)) return false;
  l.marked.add(n);
  l.pending = null;
  checkWin(l);
  return true;
}

function checkWin(l) {
  if (l.finished) return;
  // Соперник закрывается только после того, как отмечены все его 15 чисел.
  for (let i = 0; i < l.rivalMarked.length; i++) {
    if (l.rivalMarked[i].size >= TO_CLOSE) { l.finished = true; l.result = 'rival'; return; }
  }
  if (l.marked.size >= TO_CLOSE) { l.finished = true; l.result = 'player'; }
}

function decideOnExhaust(l) {
  const best = Math.max(...l.rivalMarked.map((s) => s.size));
  return l.marked.size >= best ? 'player' : 'rival';
}

export function progress(l) {
  return {
    player: l.marked.size,
    rivals: l.rivalMarked.map((s) => s.size),
    missed: l.missed,
    called: l.called.length,
  };
}
