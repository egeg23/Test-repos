// Кликер. Диегетический: это та самая честная работа, которую игрок всё ещё
// обязан делать. Надпись на кнопке меняется по ступеням.
//
// Ключевое экономическое решение: бубли НЕ покупают ранг. Поэтому бесконечное
// кликание не ускоряет карьеру — оно лишь даёт право на ошибку.

import { CLICK_REWARD, AD_REWARD, AD_COOLDOWN_MS } from './balance.js';

export function create() {
  return { clicks: 0, adsWatched: 0, lastAdAt: -Infinity };
}

export function click(c) {
  c.clicks++;
  return CLICK_REWARD;
}

export function canWatchAd(c, now) {
  return now - c.lastAdAt >= AD_COOLDOWN_MS;
}

export function adCooldownLeft(c, now) {
  return Math.max(0, AD_COOLDOWN_MS - (now - c.lastAdAt));
}

export function watchAd(c, now) {
  if (!canWatchAd(c, now)) return 0;
  c.lastAdAt = now;
  c.adsWatched++;
  return AD_REWARD;
}

// Во сколько раз одна схема выгоднее честного труда. Считается для экрана
// статистики: тезис игры выражен числом, а не репликой.
export function honestMinutesFor(amount, clicksPerSecond = 4) {
  const perMinute = CLICK_REWARD * clicksPerSecond * 60;
  return amount / perMinute;
}
