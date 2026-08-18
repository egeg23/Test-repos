// Таблица достижимых сочетаний.
//
// Не всякий набор правил даёт всякую полосу сложности: 6x6 с кривыми
// областями и диагоналями переограничен настолько, что не даёт ни одной,
// а 9x9 со всем сразу — только четыре сочетания из двадцати пяти.
//
// Недостижимое сочетание надо не «пробовать и извиняться», а не показывать
// вовсе. Заодно это снимает самый долгий сценарий: 15,8 секунды уходило
// ровно на попытки добыть полосу, которой на этих правилах не существует.
import { generate, BANDS, SYMMETRIES } from '../src/generator.js';
import { specKey } from '../src/units.js';
import { mulberry32 } from '../src/rng.js';
import { writeFileSync } from 'node:fs';

const SEEDS = Number(process.argv[2] || 3);

const rules = [];
for (const size of [9, 6]) {
  for (const regions of ['boxes', 'jigsaw']) {
    for (const diagonal of [false, true]) {
      for (const hyper of size === 9 ? [false, true] : [false]) {
        rules.push({ size, regions, diagonal, hyper });
      }
    }
  }
}

const reachable = {};
let ok = 0, total = 0, slowest = 0, slowestName = '';
for (const spec of rules) {
  const key = specKey(spec);
  reachable[key] = [];
  for (const band of BANDS) {
    for (const sym of SYMMETRIES) {
      total++;
      // Сочетание считается рабочим, если полоса берётся хотя бы с одного
      // сида: разброс есть, и одного неудачного сида мало для приговора.
      let hit = false;
      for (let s = 0; s < SEEDS && !hit; s++) {
        const t0 = Date.now();
        let r = null;
        try { r = generate(spec, band.key, mulberry32(total * 7919 + s), { symmetry: sym.key, attempts: 3 }); }
        catch { r = null; }
        const ms = Date.now() - t0;
        if (ms > slowest) { slowest = ms; slowestName = `${key} / ${band.name} / ${sym.name}`; }
        if (r && r.band.key === band.key) hit = true;
      }
      if (hit) { reachable[key].push(`${band.key}:${sym.key}`); ok++; }
    }
  }
  console.log(`${key.padEnd(24)} ${reachable[key].length}/25`);
}

console.log(`\nвсего сочетаний: ${total} · достижимо: ${ok} · недостижимо: ${total - ok}`);
console.log(`самая долгая попытка: ${slowest} мс — ${slowestName}`);

writeFileSync(new URL('../src/combos.js', import.meta.url),
`// Достижимые сочетания правил, сложности и симметрии.
// Сгенерировано tools/vet-combos.mjs (${SEEDS} сида на сочетание).
//
// Конструктор обязан сверяться с этой таблицей и не предлагать того, чего
// на выбранных правилах не существует. Это не только честность интерфейса:
// самая долгая генерация уходила именно на попытки добыть недостижимую
// полосу — до 15,8 секунды впустую.
//
// Достижимо ${ok} сочетаний из ${total}.

export const REACHABLE = ${JSON.stringify(reachable, null, 2)};

/** Доступна ли пара «сложность + симметрия» на этом наборе правил. */
export function isReachable(key, band, symmetry) {
  return (REACHABLE[key] || []).includes(\`\${band}:\${symmetry}\`);
}

/** Сколько всего рабочих сочетаний — число из описания игры. */
export const TOTAL_REACHABLE = ${ok};
`);
console.log('записано: src/combos.js');
