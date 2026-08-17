import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const read = (p) => readFileSync(join(root, p), 'utf8');

// Поле «Комментарий для модератора» в консоли ограничено 2048 символами.
// Текст правится при каждом изменении игры, поэтому лимит проверяется тестом:
// иначе превышение обнаружится в момент подачи.
const MODERATOR_LIMIT = 2048;

function commentBody() {
  const file = read('store/moderator-comment.md');
  const parts = file.split('\n---\n');
  assert.ok(parts.length > 1, 'в файле нет разделителя перед текстом комментария');
  return parts.slice(1).join('\n---\n').trim();
}

test('комментарий для модератора укладывается в 2048 символов', () => {
  const body = commentBody();
  assert.ok(body.length <= MODERATOR_LIMIT,
    `комментарий ${body.length} символов при лимите ${MODERATOR_LIMIT}`);
  console.log(`      комментарий: ${body.length} из ${MODERATOR_LIMIT}, запас ${MODERATOR_LIMIT - body.length}`);
});

test('комментарий содержит то, ради чего он нужен', () => {
  const body = commentBody();
  for (const must of ['2.9', 'LoadingAPI', 'GameplayAPI', 'onRewarded', 'daily', 'best', 'drum']) {
    assert.ok(body.includes(must), `в комментарии потерялось упоминание «${must}»`);
  }
});

test('тексты для консоли перечисляют все три лидерборда', () => {
  const fields = read('store/console-fields.md');
  for (const lb of ['`daily`', '`best`', '`drum`']) {
    assert.ok(fields.includes(lb), `в текстах для консоли нет лидерборда ${lb}`);
  }
});

test('названия на обложках совпадают с названиями для консоли по каждому языку', () => {
  // Платформа требует совпадения названия на промоматериалах с названием
  // в консоли для того же языка. Обложки локализованы, значит расхождение
  // возможно в трёх местах сразу — сверяем таблицы напрямую.
  const fields = read('store/console-fields.md');
  const cover = read('store/cover.html');
  const expected = { ru: 'Бочонки', en: 'Barrels', tr: 'Fıçılar' };

  for (const [lang, name] of Object.entries(expected)) {
    assert.ok(fields.includes('`' + name + '`'),
      `в текстах для консоли нет названия «${name}» (${lang})`);
    const row = new RegExp(lang + ":\\s*\\['" + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "'");
    assert.ok(row.test(cover),
      `на обложке для «${lang}» название разошлось с консолью`);
  }
});

test('обложка отрисована для каждого заявленного языка', () => {
  // Черновик не уходит на модерацию, пока медиа заполнены не для всех языков.
  for (const lang of ['ru', 'en', 'tr']) {
    const f = join(root, 'store', `cover-${lang}-800x470.png`);
    assert.doesNotThrow(() => readFileSync(f), `нет обложки для языка «${lang}»`);
  }
});

// Регрессия к SEC-001: в лидерборд не должно уходить значение из сохранения.
// Сохранение лежит в localStorage открытым JSON и правится игроком.
test('в лидерборд отправляется счёт партии, а не поле из сохранения', () => {
  const main = read('src/main.js');
  assert.ok(!/submitScore\(\s*'best'\s*,\s*save\./.test(main),
    'счёт рекорда снова берётся из сохранения — подменённое значение попадёт в таблицу');
  assert.ok(/if \(newBest\) sdk\.submitScore\('best', s\.total\)/.test(main),
    'рекорд должен отправляться только при реальном улучшении и значением партии');
});

test('партия дня не отправляется, пока время не подтверждено сервером', () => {
  const main = read('src/main.js');
  assert.ok(/sdk\.state\.timeVerified/.test(main),
    'без проверки серверного времени день задают часы устройства');
});

// Регрессии к сверке с документацией SDK (docs/ADV_REVIEW.md).
test('реклама вызывается в форме { callbacks: ... }, как в документации', () => {
  const sdk = read('src/sdk.js');
  for (const fn of ['showFullscreenAdv', 'showRewardedVideo']) {
    const call = new RegExp(fn + '\\(\\s*\\{\\s*\\n?\\s*callbacks:', 'm');
    assert.ok(call.test(sdk), `${fn} должен получать объект с полем callbacks`);
  }
});

test('у показа рекламы есть сторож от неотработавших колбэков', () => {
  const sdk = read('src/sdk.js');
  assert.ok(/ADV_WATCHDOG_MS/.test(sdk), 'без сторожа молчащий SDK подвесит игру');
  assert.ok(/onOpen: \(\) => \{ clear\(\)/.test(sdk),
    'onOpen должен снимать сторож, иначе он оборвёт идущий ролик');
});

test('звук приглушается на время рекламы', () => {
  const sdk = read('src/sdk.js');
  assert.ok(/audio\.suspend\(\)/.test(sdk) && /audio\.resume\(\)/.test(sdk));
});

test('sticky-баннер прячется на время партии', () => {
  const main = read('src/main.js');
  assert.ok(/sdk\.hideBanner\(\)/.test(main) && /sdk\.showBanner\(\)/.test(main),
    'баннер должен скрываться в партии и возвращаться вне её');
});

// Требование 2.14: язык определяется при запуске из SDK и ничем не перебивается.
test('сохранённый язык не перебивает язык платформы', () => {
  const main = read('src/main.js');
  assert.ok(!/save\.lang\s*\|\|/.test(main),
    'кэш языка перебивает SDK — модерация не увидит смену языка в debug-панели');
  assert.ok(/setLang\(sdk\.state\.lang\)/.test(main),
    'язык должен браться напрямую из состояния SDK');
});

test('аварийный экран тоже переведён', () => {
  const main = read('src/main.js');
  assert.ok(!/Не удалось загрузить игру/.test(main),
    'в аварийном экране осталась захардкоженная строка');
  assert.ok(/t\('load_failed'\)/.test(main));
});

// Правила проекта из games/CLAUDE.md должны оставаться синхронными с кодом.
// Файл читается новыми сессиями как инструкция, поэтому расхождение опаснее,
// чем его отсутствие: следующая игра будет сделана по устаревшему тексту.
test('правила проекта перечисляют все пункты чек-листа, что закрыты в коде', () => {
  const rules = readFileSync(join(root, '..', 'CLAUDE.md'), 'utf8');
  const must = ['§1.1', '§1.19', '§2.14', '§1.14', '§1.15', '§1.9', '§1.10',
                '§1.6', '§1.3', '§4.7', '§4.4', '§4.5', '§2.7', '§5.12',
                '§2.3', '§2.10', '§3.4', '§3.5', '§3.6', '§2.9'];
  const missing = must.filter((p) => !rules.includes(p));
  assert.deepEqual(missing, [], 'в правилах проекта пропущены пункты чек-листа');
});

test('правила проекта не разошлись с фактическими лимитами', () => {
  const rules = readFileSync(join(root, '..', 'CLAUDE.md'), 'utf8');
  assert.ok(/2048/.test(rules), 'потерян лимит комментария модератора');
  assert.ok(/800×470/.test(rules), 'потерян подтверждённый размер обложки');
  assert.ok(/5 секунд/.test(rules) && /200 КБ/.test(rules), 'потеряны лимиты сохранений');
  assert.ok(/56 px/.test(rules) && /28 px/.test(rules), 'потеряны требования к размерам элементов');
  assert.ok(/requestAnimationFrame/.test(rules),
    'потеряно точное правило вызова Game Ready API — на нём был отказ модерации');
  assert.ok(/на КАЖДЫЙ заявленный язык/.test(rules),
    'потеряно правило про комплект медиа на каждый язык — на нём был отказ модерации');
});

// Требование 1.19: Game Ready API вызывается ровно тогда, когда игрок может
// начать играть. Модерация уже отклоняла сборку, где сеть стояла в критическом
// пути и меню (а с ним и сигнал) ждало ответа сервера.
test('в критическом пути до показа меню нет сетевых вызовов', () => {
  const main = read('src/main.js');
  const boot = main.slice(main.indexOf('async function boot'), main.indexOf("go('menu')"));
  assert.ok(!/store\.load\(\)/.test(boot),
    'загрузка облачного сохранения снова блокирует показ меню');
  assert.ok(/store\.loadLocal\(\)/.test(boot),
    'локальное сохранение должно читаться синхронно');
  assert.ok(!/initDeferred/.test(boot),
    'сетевая часть SDK не должна выполняться до показа меню');
});

test('сигнал готовности привязан к кадру, в котором появилось меню', () => {
  const main = read('src/main.js');
  const idxMenu = main.indexOf("go('menu')");
  const idxReady = main.indexOf('loadingReady');
  assert.ok(idxMenu > 0 && idxReady > idxMenu, 'ready() должен идти после отрисовки меню');
  assert.ok(/requestAnimationFrame\(\(\) => sdk\.loadingReady\(\)\)/.test(main),
    'ready() должен вызываться в requestAnimationFrame — не раньше кадра с меню и не позже');
});

test('сетевая инициализация вынесена в отложенную фазу', () => {
  const sdk = read('src/sdk.js');
  const init = sdk.slice(sdk.indexOf('export async function init'), sdk.indexOf('export async function initDeferred'));
  for (const call of ['serverTime', 'getPlayer', 'getLeaderboards']) {
    assert.ok(!init.includes(call), `${call} остался в быстрой инициализации`);
  }
});
