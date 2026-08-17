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

test('название игры совпадает во всех материалах', () => {
  const fields = read('store/console-fields.md');
  const cover = read('store/cover.html');
  assert.ok(fields.includes('**Название:** `Бочонки`'), 'название в текстах для консоли изменилось');
  assert.ok(cover.includes('<h1>Бочонки</h1>'),
    'название на обложке разошлось с консолью — платформа требует совпадения');
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
