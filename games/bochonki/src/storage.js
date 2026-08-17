// Сохранения. Пишем и в localStorage (мгновенно, работает для неавторизованных),
// и в облако Яндекса (переносится между устройствами).
//
// Важное ограничение платформы: setData перезаписывает объект целиком и лимит
// запросов невелик. Поэтому облачная запись отложенная и не чаще раза в 5 секунд.

import * as sdk from './sdk.js';

const KEY = 'bochonki.save.v1';
// Лимит платформы — 100 записей за 5 минут. Пауза в 5 секунд даёт максимум 60,
// то есть держимся с почти двукратным запасом.
const CLOUD_THROTTLE_MS = 5000;
// Лимит платформы на объём данных игрока — 200 КБ. Наше сохранение на порядки
// меньше, но история партий растёт, поэтому размер проверяется явно.
const MAX_SAVE_BYTES = 200 * 1024;
const HISTORY_LIMIT = 30;

export const DEFAULT_SAVE = {
  v: 1,
  gamesPlayed: 0,       // определяет, какие правила открыты
  best: 0,
  achievements: '',     // битовая маска в base64
  history: [],          // последние 30 партий: { score, day, mode }
  streak: 0,
  lastDailyKey: '',
  dailyBest: {},        // ключ дня -> лучший результат
  seenRules: 0,         // сколько правил игрок уже видел в объяснении
  muted: false,
  lang: '',
};

let cache = { ...DEFAULT_SAVE };
let cloudTimer = null;
let lastCloudWrite = 0;
let dirty = false;

function readLocal() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function writeLocal(save) {
  try { localStorage.setItem(KEY, JSON.stringify(save)); } catch {}
}

function merge(a, b) {
  if (!a) return b;
  if (!b) return a;
  // При расхождении устройств выигрывает более сыгранный профиль.
  const pick = (b.gamesPlayed || 0) > (a.gamesPlayed || 0) ? b : a;
  const other = pick === a ? b : a;
  return {
    ...DEFAULT_SAVE, ...other, ...pick,
    best: Math.max(a.best || 0, b.best || 0),
    streak: Math.max(a.streak || 0, b.streak || 0),
    history: (pick.history || []).slice(-30),
  };
}

export async function load() {
  const local = readLocal();
  const cloud = await sdk.loadData();
  cache = { ...DEFAULT_SAVE, ...merge(local, cloud) };
  if (!Array.isArray(cache.history)) cache.history = [];
  return cache;
}

export function get() { return cache; }

export function update(patch) {
  cache = { ...cache, ...patch };
  writeLocal(cache);
  dirty = true;
  scheduleCloud();
  return cache;
}

function scheduleCloud() {
  if (cloudTimer) return;
  const wait = Math.max(0, CLOUD_THROTTLE_MS - (Date.now() - lastCloudWrite));
  cloudTimer = setTimeout(async () => {
    cloudTimer = null;
    if (!dirty) return;
    dirty = false;
    lastCloudWrite = Date.now();
    await sdk.saveData(trim(cache), false);
  }, wait);
}

// Досрочный сброс в облако — на закрытии вкладки и после партии.
// Досрочный сброс: закрытие вкладки, уход в фон, конец партии.
// Здесь запись немедленная — очередь может не успеть уехать.
export async function flush() {
  if (cloudTimer) { clearTimeout(cloudTimer); cloudTimer = null; }
  if (!dirty) return;
  dirty = false;
  lastCloudWrite = Date.now();
  await sdk.saveData(trim(cache), true);
}

// Страховка от разрастания: история обрезается, и если сохранение всё же
// не влезает в лимит платформы, история отбрасывается целиком —
// прогресс и коллекция важнее статистики.
export function saveSize(save) {
  try { return new TextEncoder().encode(JSON.stringify(save)).length; }
  catch { return JSON.stringify(save).length; }
}

export function trim(save) {
  let out = { ...save, history: (save.history || []).slice(-HISTORY_LIMIT) };
  if (saveSize(out) <= MAX_SAVE_BYTES) return out;
  out = { ...out, history: out.history.slice(-10) };
  if (saveSize(out) <= MAX_SAVE_BYTES) return out;
  return { ...out, history: [] };
}

export { MAX_SAVE_BYTES, HISTORY_LIMIT };

export function recordGame(entry) {
  const history = [...(cache.history || []), entry].slice(-HISTORY_LIMIT);
  return update({
    history,
    gamesPlayed: (cache.gamesPlayed || 0) + 1,
    best: Math.max(cache.best || 0, entry.score || 0),
  });
}
