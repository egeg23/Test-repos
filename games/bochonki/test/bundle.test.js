import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Однофайловая сборка используется для превью. Бандлер подставлял
// `var {suspend as audioSuspend} = ...` — невалидный JS: страница замирала на
// загрузочном экране, хотя исходники и архив работали. Проверяем саму сборку.
test('однофайловая сборка — валидный JS', () => {
  execFileSync('python3', [path.join(ROOT, 'tools', 'bundle.py')], { cwd: ROOT });
  const page = readFileSync(path.join(ROOT, 'build', 'bochonki-single.html'), 'utf8');
  const js = page.slice(page.indexOf('<script>') + 8, page.lastIndexOf('</script>'));
  assert.ok(js.length > 1000, 'скрипт из сборки не извлёкся');

  const dir = mkdtempSync(path.join(tmpdir(), 'bochonki-bundle-'));
  const file = path.join(dir, 'bundle.js');
  writeFileSync(file, js);
  execFileSync('node', ['--check', file]);
});

test('импорт с псевдонимом превращается в двоеточие, а не в as', () => {
  const page = readFileSync(path.join(ROOT, 'build', 'bochonki-single.html'), 'utf8');
  assert.ok(/suspend:\s*audioSuspend/.test(page), 'псевдоним импорта не переписан');
  assert.ok(!/\{[^}\n]*\bas\s+audioSuspend/.test(page), 'в сборке остался `as` внутри деструктуризации');
});
