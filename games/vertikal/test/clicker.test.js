import test from 'node:test';
import assert from 'node:assert/strict';
import * as C from '../src/clicker.js';
import { CLICK_REWARD, AD_REWARD, AD_COOLDOWN_MS } from '../src/balance.js';

test('клик даёт ровно заявленное', () => {
  const c = C.create();
  assert.equal(C.click(c), CLICK_REWARD);
  assert.equal(c.clicks, 1);
});

test('реклама не чаще раза в минуту', () => {
  const c = C.create();
  const t0 = 1_000_000;
  assert.equal(C.watchAd(c, t0), AD_REWARD);
  assert.equal(C.watchAd(c, t0 + 1000), 0, 'через секунду ролик не даётся');
  assert.equal(C.watchAd(c, t0 + AD_COOLDOWN_MS - 1), 0, 'за миллисекунду до — тоже');
  assert.equal(C.watchAd(c, t0 + AD_COOLDOWN_MS), AD_REWARD, 'ровно через минуту — можно');
  assert.equal(c.adsWatched, 2);
});

test('остаток кулдауна считается честно', () => {
  const c = C.create();
  const t0 = 500_000;
  C.watchAd(c, t0);
  assert.equal(C.adCooldownLeft(c, t0), AD_COOLDOWN_MS);
  assert.equal(C.adCooldownLeft(c, t0 + 30_000), AD_COOLDOWN_MS - 30_000);
  assert.equal(C.adCooldownLeft(c, t0 + AD_COOLDOWN_MS + 5), 0);
});

test('ролик выгоднее яростного кликания, но не кратно', () => {
  // Смысл ролика — экономить пальцы, а не открывать недоступное.
  const perMinuteClicking = CLICK_REWARD * 4 * 60;   // 4 клика в секунду
  assert.ok(AD_REWARD > perMinuteClicking, 'иначе ролик бессмысленен');
  assert.ok(AD_REWARD < perMinuteClicking * 3, 'иначе кликер бессмысленен');
});

test('честный труд отстаёт от схемы в сотни раз — это тезис игры', () => {
  const scheme = 80_000;                       // осторожная схема
  const minutes = C.honestMinutesFor(scheme);
  assert.ok(minutes > 100,
    `схема окупается ${minutes.toFixed(0)} минутами кликания — слишком быстро, тезис не читается`);
});
