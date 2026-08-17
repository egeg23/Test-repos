// Обёртка над Yandex Games SDK.
//
// Вне платформы (локальный запуск, другая площадка) SDK отсутствует — тогда
// каждый вызов молча деградирует до безопасной заглушки. Игровой код не должен
// знать, где он выполняется, и не должен падать, если SDK не загрузился:
// по требованиям модерации игра обязана оставаться играбельной.

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
      if (typeof t === 'number') state.serverTimeOffset = t - Date.now();
    } catch { /* серверное время недоступно — считаем по локальному */ }

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

// Полноэкранная реклама. Показывается только там, где геймплей объективно
// остановлен (экран результата), и никогда внутри партии.
export function showFullscreen(onDone = noop) {
  if (!ysdk?.adv) { onDone(false); return; }
  let settled = false;
  const finish = (shown) => { if (!settled) { settled = true; onDone(shown); } };
  try {
    ysdk.adv.showFullscreenAdv({
      callbacks: {
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
  try {
    ysdk.adv.showRewardedVideo({
      callbacks: {
        onRewarded: () => { rewarded = true; onReward(); },
        onClose: () => onClose(rewarded),
        onError: () => onClose(false),
      },
    });
  } catch { onClose(false); }
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
