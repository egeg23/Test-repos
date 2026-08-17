// Подозрение — скрытый ресурс и ядро всей игры. Игрок точно знает,
// сколько у него денег, и никогда не знает, насколько он уязвим.

import {
  SUSPICION_MAX, DECAY_FLAT, DECAY_RATE, NOISE_LABELS,
  GAUGE_DELAY, GAUGE_BUCKETS, GAUGE_HYSTERESIS,
} from './balance.js';

export function create() {
  return {
    value: 0,
    history: [],      // значения по ходам — для косвенной шкалы с задержкой
    gaugeBucket: 0,   // текущее деление шкалы, хранится ради гистерезиса
    turnNoise: 0,     // шум, накопленный за текущий ход
    turnStart: 0,     // подозрение на начало хода — база для распада
    papers: 0,        // листы дела: видимы всегда и не убывают никогда
  };
}

// Прибавка подозрения. Одно и то же число идёт и в S, и в метку шума —
// поэтому подсказка не может разойтись с механикой.
export function add(s, amount, papers = 0) {
  const n = Math.max(0, amount);
  s.value = Math.min(SUSPICION_MAX, s.value + n);
  s.turnNoise += n;
  s.papers += papers;
  return s.value;
}

// Снятие подозрения. Листы дела при этом не трогаются: «замести след»
// снижает внимание, но не стирает того, что было.
export function relieve(s, amount) {
  s.value = Math.max(0, s.value - Math.max(0, amount));
  return s.value;
}

// Распад считается от того, насколько игрок был заметен НА НАЧАЛО хода,
// а не после сегодняшних действий. Иначе шумный ход частично гасит сам себя,
// и равновесие уезжает вниз от документированной формулы.
// Тематически это тоже вернее: только что сделанное громкое не забывается
// в тот же вечер.
export function decayAmount(base) {
  return DECAY_FLAT + DECAY_RATE * base;
}

export function decay(s) {
  s.value = Math.max(0, s.value - decayAmount(s.turnStart));
  return s.value;
}

// Равновесие при заданном постоянном притоке. Из этой формулы выводится
// весь баланс: приток 2,0 даёт S* = 33, приток 4,0 — уже 100.
export function equilibrium(inflow) {
  return (inflow - DECAY_FLAT) / DECAY_RATE;
}

export function endTurn(s) {
  const noise = s.turnNoise;
  decay(s);
  s.history.push(s.value);
  s.turnNoise = 0;
  s.turnStart = s.value;
  return noise;
}

export function noiseLabel(noise) {
  for (const l of NOISE_LABELS) if (noise <= l.max) return l.key;
  return NOISE_LABELS[NOISE_LABELS.length - 1].key;
}

export function isCaught(s) {
  return s.value >= SUSPICION_MAX;
}

// Косвенная шкала: пять делений по значению трёхходовой давности,
// с гистерезисом на границе, чтобы деление не мигало.
export function gauge(s) {
  const idx = s.history.length - 1 - GAUGE_DELAY;
  const past = idx >= 0 ? s.history[idx] : 0;

  let target = GAUGE_BUCKETS.findIndex((top) => past <= top);
  if (target < 0) target = GAUGE_BUCKETS.length - 1;

  if (target !== s.gaugeBucket) {
    const cur = s.gaugeBucket;
    const boundary = target > cur ? GAUGE_BUCKETS[cur] : GAUGE_BUCKETS[target];
    const clears = target > cur
      ? past >= boundary + GAUGE_HYSTERESIS
      : past <= boundary - GAUGE_HYSTERESIS;
    if (clears) s.gaugeBucket = target;
  }
  return s.gaugeBucket;
}
