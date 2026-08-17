// Обёртка над Yandex Games SDK.
//
// Вне платформы (локальный запуск, другая площадка) SDK отсутствует — тогда
// каждый вызов молча деградирует до безопасной заглушки. Игровой код не должен
// знать, где он выполняется, и не должен падать, если SDK не загрузился:
// по требованиям модерации игра обязана оставаться играбельной.

import * as audio from './audio.js';

const noop = () => {};

let ysdk = null;
let player = null;
let leaderboards = null;
let lbApi = null;      // 'modern' | 'legacy'
let ready = false;

export const state = {
  available: false,      // SDK загрузился
  authorized: false,     // игрок вошёл в аккаунт
  lang: 'ru',
  deviceType: 'desktop',
  serverTimeOffset: 0,   // мс: серверное время минус локальное
  // Подтверждено ли время сервером. Если нет, «день» определяется часами
  // устройства, а их игрок волен перевести — тогда результат партии дня
  // в общую таблицу не отправляем.
  timeVerified: false,
};

export async function init() {
  if (typeof YaGames === 'undefined') {
    detectLangOffline();
    return false;
  }
  try {
    ysdk = await YaGames.init();
    state.available = true;
    state.lang = (ysdk.environment?.i18n?.lang || 'ru').slice(0, 2);
    state.deviceType = ysdk.deviceInfo?.type || 'desktop';

    try {
      const t = await ysdk.serverTime();
      if (typeof t === 'number') {
        state.serverTimeOffset = t - Date.now();
        state.timeVerified = true;
      }
    } catch { /* серверное время недоступно — день считаем по локальному, но не соревнуемся */ }

    try {
      player = await ysdk.getPlayer({ scopes: false });
      state.authorized = player.getMode() !== 'lite';
    } catch { player = null; }

    // Актуальный API — объект ysdk.leaderboards. Инициализация через
    // getLeaderboards() помечена в документации как устаревшая и держится
    // здесь только как запасной путь для старых сборок SDK.
    if (ysdk.leaderboards) {
      leaderboards = ysdk.leaderboards;
      lbApi = 'modern';
    } else {
      try { leaderboards = await ysdk.getLeaderboards(); lbApi = 'legacy'; }
      catch { leaderboards = null; }
    }
    return true;
  } catch (e) {
    console.warn('[sdk] init не удался, играем без платформы:', e);
    detectLangOffline();
    return false;
  }
}

function detectLangOffline() {
  const l = (navigator.language || 'ru').slice(0, 2).toLowerCase();
  state.lang = ['ru', 'en', 'tr'].includes(l) ? l : 'en';
  state.deviceType = matchMedia('(pointer: coarse)').matches ? 'mobile' : 'desktop';
}

// Требование платформы: сообщить, что игра загрузилась и готова к вводу.
// Вызывать ровно один раз и как можно раньше — иначе отказ модерации.
export function loadingReady() {
  if (ready) return;
  ready = true;
  try { ysdk?.features?.LoadingAPI?.ready(); } catch { /* не критично */ }
}

// Границы активного геймплея. Платформа по ним решает, когда можно
// показывать рекламу, и приглушает фоновые звуки.
export function gameplayStart() { try { ysdk?.features?.GameplayAPI?.start(); } catch {} }
export function gameplayStop()  { try { ysdk?.features?.GameplayAPI?.stop();  } catch {} }

// Серверное время — общая для всех точка отсчёта «дня». Без него мешок дня
// можно было бы подкрутить переводом часов на устройстве.
export function now() { return Date.now() + state.serverTimeOffset; }

export async function loadData() {
  if (!player) return null;
  try {
    const d = await player.getData(['save']);
    return d?.save ?? null;
  } catch { return null; }
}

// flush=true отправляет немедленно, false — ставит в очередь.
// Очередь дешевле по лимитам, но при закрытии вкладки может не уехать,
// поэтому финальное сохранение всегда немедленное.
export async function saveData(save, immediate = false) {
  if (!player) return false;
  try { await player.setData({ save }, immediate); return true; }
  catch { return false; }
}

// Сколько ждём хоть какой-то реакции SDK, прежде чем считать показ несостоявшимся.
// Сторож нужен на случай, когда не приходит ни onClose, ни onError: без него игра
// застыла бы на переходе к результату. При onOpen сторож снимается — иначе он
// оборвал бы реально идущий ролик.
const ADV_WATCHDOG_MS = 8000;

// Полноэкранная реклама. Показывается только там, где геймплей объективно
// остановлен (экран результата), и никогда внутри партии.
export function showFullscreen(onDone = noop) {
  if (!ysdk?.adv) { onDone(false); return; }
  let settled = false;
  let timer = setTimeout(() => finish(false), ADV_WATCHDOG_MS);
  const clear = () => { if (timer) { clearTimeout(timer); timer = null; } };
  function finish(shown) {
    if (settled) return;
    settled = true;
    clear();
    audio.resume();
    onDone(shown);
  }
  try {
    ysdk.adv.showFullscreenAdv({
      callbacks: {
        onOpen: () => { clear(); audio.suspend(); },
        onClose: (wasShown) => finish(!!wasShown),
        onError: () => finish(false),
      },
    });
  } catch { finish(false); }
}

// Rewarded — строго по желанию игрока. Награда выдаётся только по onRewarded.
export function showRewarded(onReward = noop, onClose = noop) {
  if (!ysdk?.adv) { onClose(false); return; }
  let rewarded = false;
  let settled = false;
  let timer = setTimeout(() => finish(), ADV_WATCHDOG_MS);
  const clear = () => { if (timer) { clearTimeout(timer); timer = null; } };
  function finish() {
    if (settled) return;      // onClose и onError могут прийти оба — закрываем один раз
    settled = true;
    clear();
    audio.resume();
    onClose(rewarded);
  }
  try {
    ysdk.adv.showRewardedVideo({
      callbacks: {
        onOpen: () => { clear(); audio.suspend(); },
        onRewarded: () => { rewarded = true; onReward(); },
        onClose: () => finish(),
        onError: () => finish(),
      },
    });
  } catch { finish(); }
}

// --- sticky-баннер ---
// Появляется по умолчанию при запуске и управляется через API. Держим его на
// экранах вне партии и убираем на время игры: поле 5×5 и карточка лото занимают
// экран целиком, баннер поверх них мешал бы попадать по клеткам.

export async function showBanner() {
  try { await ysdk?.adv?.showBannerAdv?.(); } catch {}
}

export async function hideBanner() {
  try { await ysdk?.adv?.hideBannerAdv?.(); } catch {}
}

export async function bannerStatus() {
  try { return (await ysdk?.adv?.getBannerAdvStatus?.()) ?? null; } catch { return null; }
}

export function hasAds() { return !!ysdk?.adv; }

export async function submitScore(board, score) {
  if (!leaderboards || !state.authorized) return false;
  const value = Math.max(0, Math.round(score));
  try {
    if (lbApi === 'modern') await leaderboards.setScore(board, value);
    else await leaderboards.setLeaderboardScore(board, value);
    return true;
  } catch { return false; }
}

export async function topEntries(board, quantity = 20) {
  if (!leaderboards) return null;
  const opts = { quantityTop: quantity, includeUser: true, quantityAround: 3 };
  try {
    const r = lbApi === 'modern'
      ? await leaderboards.getEntries(board, opts)
      : await leaderboards.getLeaderboardEntries(board, opts);
    return r?.entries ?? null;
  } catch { return null; }
}

// Предложение добавить игру на рабочий стол — заметный прирост возвратов.
export async function canReview() {
  try { const r = await ysdk?.feedback?.canReview(); return !!r?.value; } catch { return false; }
}
export async function requestReview() {
  try { await ysdk?.feedback?.requestReview(); } catch {}
}
