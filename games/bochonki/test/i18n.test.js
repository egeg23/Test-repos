import test from 'node:test';
import assert from 'node:assert/strict';
import { DICTS, LANGS } from '../src/i18n.js';

test('во всех языках одинаковый набор ключей', () => {
  const base = Object.keys(DICTS.ru).sort();
  for (const lang of LANGS) {
    const keys = Object.keys(DICTS[lang]).sort();
    const missing = base.filter((k) => !keys.includes(k));
    const extra = keys.filter((k) => !base.includes(k));
    assert.deepEqual(missing, [], `в «${lang}» не хватает ключей`);
    assert.deepEqual(extra, [], `в «${lang}» лишние ключи`);
  }
});

test('нет пустых строк и незаменённых заглушек', () => {
  for (const lang of LANGS) {
    for (const [k, v] of Object.entries(DICTS[lang])) {
      assert.equal(typeof v, 'string', `${lang}.${k} должен быть строкой`);
      assert.ok(v.trim().length > 0, `${lang}.${k} пустой`);
      assert.ok(!/^TODO/i.test(v), `${lang}.${k} не переведён`);
    }
  }
});

test('плейсхолдеры совпадают между языками', () => {
  const ph = (s) => (s.match(/\{(\w+)\}/g) || []).sort().join(',');
  for (const k of Object.keys(DICTS.ru)) {
    const want = ph(DICTS.ru[k]);
    for (const lang of LANGS) {
      assert.equal(ph(DICTS[lang][k]), want, `${lang}.${k}: разошлись плейсхолдеры`);
    }
  }
});

import { ACH_TITLES } from '../src/i18n.js';
import { ACHIEVEMENTS, TOTAL } from '../src/achievements.js';

test('у каждого достижения есть название на всех языках', () => {
  for (const lang of LANGS) {
    const titles = ACH_TITLES[lang];
    assert.ok(titles, `нет словаря названий для «${lang}»`);
    for (const a of ACHIEVEMENTS) {
      assert.ok(titles[a.key], `${lang}: нет названия для «${a.key}»`);
      assert.ok(titles[a.key].trim().length > 0, `${lang}.${a.key} пустое`);
    }
    assert.equal(Object.keys(titles).length, TOTAL, `${lang}: лишние или недостающие названия`);
  }
});
