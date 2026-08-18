// Отбор нарезок кривых областей.
//
// Растить нарезку в рантайме нельзя: замер по сорока штукам дал медиану 64 мс
// и максимум около двух с половиной часов на одной. Бюджет узлов сбивает
// максимум до двух секунд, но и это на телефоне превращается в десяток.
//
// Поэтому платим один раз здесь: перебираем нарезки, считаем НЕ миллисекунды,
// а узлы перебора (они одинаковы на любом устройстве), и оставляем самые
// дешёвые. Результат — данные, а не картинка: инвариант «ноль растровых
// ассетов» не задет.
import { growRegions, boardFromUnits, linesOf } from '../src/units.js';
import { fullGrid, countSolutions } from '../src/solver.js';
import { grade } from '../src/techniques.js';
import { mulberry32 } from '../src/rng.js';
import { writeFileSync } from 'node:fs';

const CANDIDATES = Number(process.argv[2] || 160);
const KEEP = Number(process.argv[3] || 40);

const cost = (b) => {
  const sol = fullGrid(b, mulberry32(12345));
  if (!sol) return null;                       // не уложилась даже в полную сетку
  const p = sol.slice();
  let nodes = 0;
  for (let c = 0; c < b.cells; c++) {
    const keep = p[c]; p[c] = 0;
    const r = countSolutions(b, p, 2);
    nodes += r.nodes;
    if (r.exhausted) return null;              // дорогая нарезка, выбрасываем
    if (r.count !== 1) { p[c] = keep; continue; }
    const g = grade(b, p);
    if (!g.solved || g.level > 4) p[c] = keep;
  }
  return nodes;
};

// Поле строим сами из свежевыращенной нарезки, а НЕ через makeBoard: тот уже
// берёт нарезки из отобранного списка, и отбор замкнулся бы сам на себя —
// 300 кандидатов оказались бы теми же двадцатью, что уже отобраны.
const scored = [], seen = new Set();
for (let s = 0; s < CANDIDATES; s++) {
  const regions = growRegions(mulberry32(s * 7919 + 13), 9);
  const owner = new Array(81);
  regions.forEach((u, i) => u.forEach((c) => { owner[c] = i; }));
  const layout = owner.join('');
  if (seen.has(layout)) continue;              // одинаковые нарезки не копим
  seen.add(layout);

  const nodes = cost(boardFromUnits([...linesOf(9), ...regions], 9, { regions: 'jigsaw' }));
  if (nodes == null) continue;
  scored.push({ nodes, layout });
}

scored.sort((a, b) => a.nodes - b.nodes);
const kept = scored.slice(0, KEEP);
const q = (f) => scored[Math.floor(scored.length * f)]?.nodes;

console.log(`кандидатов: ${CANDIDATES} · прошли бюджет: ${scored.length} · оставлено: ${kept.length}`);
console.log(`узлов на резку — медиана ${q(0.5)}, p90 ${q(0.9)}, максимум ${scored.at(-1).nodes}`);
console.log(`у отобранных — от ${kept[0].nodes} до ${kept.at(-1).nodes}`);

writeFileSync(new URL('../src/jigsawLayouts.js', import.meta.url),
`// Отобранные нарезки кривых областей. Сгенерированы tools/vet-layouts.mjs.
//
// Каждая строка — 81 символ: номер области для каждой клетки. Нарезки отобраны
// по числу узлов перебора, а не по времени: узлы одинаковы на любом устройстве.
// Случайные нарезки использовать нельзя — среди них попадаются такие, на
// которых решатель уходит в часы.
//
// Оставлено ${kept.length} из ${CANDIDATES} кандидатов, цена резки
// от ${kept[0].nodes} до ${kept.at(-1).nodes} узлов.

export const JIGSAW_LAYOUTS = [
${kept.map((k) => `  '${k.layout}',`).join('\n')}
];

/** Области из строки нарезки. */
export function layoutUnits(layout) {
  const units = [...Array(9)].map(() => []);
  for (let c = 0; c < 81; c++) units[Number(layout[c])].push(c);
  return units;
}
`);
console.log('записано: src/jigsawLayouts.js');
