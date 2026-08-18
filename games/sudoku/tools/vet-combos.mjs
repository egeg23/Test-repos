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

const SEEDS = Number(process.argv[2] || 6);
// Порог надёжности: ниже — сочетание в конструкторе не показываем.
const MIN_RATE = Number(process.argv[3] || 0.5);

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
  reachable[key] = {};
  for (const band of BANDS) {
    for (const sym of SYMMETRIES) {
      total++;
      // Считаем ДОЛЮ попаданий, а не факт «сработало хоть раз». Разница
      // принципиальная: критерий «хотя бы на одном сиде из трёх» помечает
      // достижимым и то, что берётся в трети случаев — игрок выбирал бы
      // сочетание и регулярно получал не ту полосу, что заказывал.
      let hits = 0, tried = 0;
      for (let s = 0; s < SEEDS; s++) {
        // Ранний выход. Если порог уже недостижим арифметически — даже
        // попадание на всех оставшихся сидах не вытянет долю до MIN_RATE —
        // добивать бессмысленно. Именно недостижимые сочетания стоят дороже
        // всего: генератор честно жжёт все попытки и уходит ни с чем.
        if ((hits + (SEEDS - s)) / SEEDS < MIN_RATE) break;
        const t0 = Date.now();
        let r = null;
        try { r = generate(spec, band.key, mulberry32(total * 7919 + s), { symmetry: sym.key, attempts: 2 }); }
        catch { r = null; }
        const ms = Date.now() - t0;
        if (ms > slowest) { slowest = ms; slowestName = `${key} / ${band.name} / ${sym.name}`; }
        if (r && r.band.key === band.key) hits++;
        tried++;
      }
      // Доля считается от опробованных сидов: при раннем выходе делить на
      // полное число сидов значило бы занизить долю у рабочих сочетаний.
      const rate = tried ? hits / tried : 0;
      if (rate >= MIN_RATE) { reachable[key][`${band.key}:${sym.key}`] = rate; ok++; }
    }
  }
  console.log(`${key.padEnd(24)} ${Object.keys(reachable[key]).length}/25`);
}

console.log(`\nвсего сочетаний: ${total} · достижимо: ${ok} · недостижимо: ${total - ok}`);
console.log(`самая долгая попытка: ${slowest} мс — ${slowestName}`);

writeFileSync(new URL('../src/combos.js', import.meta.url),
`// Достижимые сочетания правил, сложности и симметрии.
// Сгенерировано tools/vet-combos.mjs (${SEEDS} сидов, порог надёжности ${MIN_RATE}).
//
// Значение — ДОЛЯ попаданий в заказанную полосу, а не факт «сработало хоть
// раз». Разница принципиальная: критерий «хотя бы раз из трёх» помечал
// достижимым и то, что берётся в трети случаев, и игрок регулярно получал бы
// не ту полосу, что заказывал. Поймано тестом на живой таблице.
//
// Конструктор обязан сверяться с таблицей и не предлагать того, чего на
// выбранных правилах нет: самая долгая генерация уходила ровно на попытки
// добыть недостижимую полосу — больше десяти секунд впустую.
//
// Достижимо ${ok} сочетаний из ${total} при пороге ${MIN_RATE}.

export const REACHABLE = ${JSON.stringify(reachable, null, 2)};

/** Доля попаданий в заказанную полосу, 0 — сочетание не предлагаем. */
export function hitRate(key, band, symmetry) {
  return (REACHABLE[key] || {})[\`\${band}:\${symmetry}\`] || 0;
}

export const isReachable = (key, band, symmetry) => hitRate(key, band, symmetry) > 0;

/** Сколько всего рабочих сочетаний — число из описания игры. */
export const TOTAL_REACHABLE = ${ok};
`);
console.log('записано: src/combos.js');
