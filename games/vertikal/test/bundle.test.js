import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Опубликованная однофайловая сборка один раз ушла игроку сломанной: бандлер
// подставлял `var {suspend as audioSuspend} = ...` — невалидный JS, и страница
// замирала на загрузочном экране. Исходники и архив при этом были в порядке,
// поэтому проверка обязана идти по самой сборке.
test('однофайловая сборка — валидный JS', () => {
  execFileSync('python3', [path.join(ROOT, 'tools', 'bundle.py')], { cwd: ROOT });
  const page = readFileSync(path.join(ROOT, 'build', 'vertikal-single.html'), 'utf8');
  const js = page.slice(page.indexOf('<script>') + 8, page.lastIndexOf('</script>'));
  assert.ok(js.length > 1000, 'скрипт из сборки не извлёкся');

  const dir = mkdtempSync(path.join(tmpdir(), 'vertikal-bundle-'));
  const file = path.join(dir, 'bundle.js');
  writeFileSync(file, js);
  execFileSync('node', ['--check', file]);
});

test('импорт с псевдонимом превращается в двоеточие, а не в as', () => {
  const page = readFileSync(path.join(ROOT, 'build', 'vertikal-single.html'), 'utf8');
  assert.ok(/suspend:\s*audioSuspend/.test(page), 'псевдоним импорта не переписан');
  assert.ok(!/\{[^}\n]*\bas\s+audioSuspend/.test(page), 'в сборке остался `as` внутри деструктуризации');
});

test('на загрузочном экране буква своей игры', () => {
  const page = readFileSync(path.join(ROOT, 'build', 'vertikal-single.html'), 'utf8');
  const mark = page.match(/class="boot__mark">(.)</);
  assert.equal(mark && mark[1], 'В', 'загрузочная метка не от «Вертикали»');
});
