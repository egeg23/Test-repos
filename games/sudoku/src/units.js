// Области судоку.
//
// Ключевая мысль, на которой держится весь проект: классика, диагональ,
// кривые области, гипер и 6×6 — это ОДИН движок с разным списком областей.
// Область — просто набор клеток, где каждое значение встречается ровно раз.
// Решатель, счётчик решений и оценщик сложности про варианты не знают
// вообще ничего. Новый вариант стоит одну функцию, а не новую игру.

export const ALL = 0b111111111;          // маска «возможны все девять»
export const bit = (v) => 1 << (v - 1);
export const popcount = (m) => { let c = 0; while (m) { m &= m - 1; c++; } return c; };
export const firstValue = (m) => Math.log2(m & -m) + 1;

function rowsCols(n) {
  const out = [];
  for (let r = 0; r < n; r++) out.push([...Array(n)].map((_, c) => r * n + c));
  for (let c = 0; c < n; c++) out.push([...Array(n)].map((_, r) => r * n + c));
  return out;
}

function boxes(n, bh, bw) {
  const out = [];
  for (let br = 0; br < n / bh; br++) {
    for (let bc = 0; bc < n / bw; bc++) {
      const u = [];
      for (let r = 0; r < bh; r++) for (let c = 0; c < bw; c++) {
        u.push((br * bh + r) * n + bc * bw + c);
      }
      out.push(u);
    }
  }
  return out;
}

// Кривые области: девять связных кусков по девять клеток.
//
// Выращивать их от случайных зёрен — тупиковый путь: рост регулярно оставляет
// клетки, до которых не дотягивается ни одна голодная область, и генератор
// уходит в перезапуски. Идём от обратного: берём классические квадраты 3×3,
// у которых размер и связность верны по построению, и many раз меняем местами
// две пограничные клетки соседних областей. Обмен сохраняет размер ровно
// девять навсегда, а связность проверяем после каждого шага и откатываем.
function connected(cellsOfRegion, n) {
  const set = new Set(cellsOfRegion);
  const seen = new Set([cellsOfRegion[0]]);
  const stack = [cellsOfRegion[0]];
  while (stack.length) {
    const c = stack.pop(), r = Math.floor(c / n), q = c % n;
    for (const [dr, dq] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      const nr = r + dr, nq = q + dq;
      if (nr < 0 || nq < 0 || nr >= n || nq >= n) continue;
      const p = nr * n + nq;
      if (set.has(p) && !seen.has(p)) { seen.add(p); stack.push(p); }
    }
  }
  return seen.size === set.size;
}

export function growRegions(rnd, n = 9, swaps = 1200) {
  // Стартовая нарезка — обычные блоки: у них размер и связность верны
  // по построению. На 6x6 блок 2x3, на 9x9 — 3x3.
  const [bh, bw] = n === 6 ? [2, 3] : [3, 3];
  const owner = new Int8Array(n * n);
  for (let c = 0; c < n * n; c++) {
    owner[c] = Math.floor(Math.floor(c / n) / bh) * (n / bw) + Math.floor((c % n) / bw);
  }
  const members = (i) => [...Array(n * n).keys()].filter((c) => owner[c] === i);
  const nbrsOf = (c) => {
    const r = Math.floor(c / n), q = c % n, out = [];
    if (r > 0) out.push(c - n);
    if (r < n - 1) out.push(c + n);
    if (q > 0) out.push(c - 1);
    if (q < n - 1) out.push(c + 1);
    return out;
  };

  // Обмен идёт в два шага, а не «поменять местами соседей». Соседняя пара
  // не работает вовсе: отданная клетка держится за новую область только
  // через ту, что ушла навстречу, и обе рвутся — из квадратов 3×3 не
  // выходило ни одного принятого хода. Поэтому: сперва отдаём клетку с
  // границы, затем забираем ЛЮБУЮ клетку соседа, касающуюся нас.
  for (let step = 0; step < swaps; step++) {
    const a = Math.floor(rnd() * n * n);
    const ia = owner[a];
    const cross = nbrsOf(a).filter((b) => owner[b] !== ia);
    if (!cross.length) continue;
    const ib = owner[cross[Math.floor(rnd() * cross.length)]];

    owner[a] = ib;
    if (!connected(members(ia), n)) { owner[a] = ia; continue; }

    const back = members(ib).filter((c) =>
      c !== a && nbrsOf(c).some((x) => owner[x] === ia));
    if (!back.length) { owner[a] = ia; continue; }
    const b = back[Math.floor(rnd() * back.length)];

    owner[b] = ia;
    if (!connected(members(ib), n)) { owner[b] = ib; owner[a] = ia; }
  }

  return [...Array(n).keys()].map(members);
}

const diagonals = (n) => [
  [...Array(n)].map((_, i) => i * n + i),
  [...Array(n)].map((_, i) => i * n + (n - 1 - i)),
];

// Четыре дополнительных квадрата, сдвинутых внутрь поля.
const hyper = (n) => {
  const out = [];
  for (const or of [1, 5]) for (const oc of [1, 5]) {
    const u = [];
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) u.push((or + r) * n + oc + c);
    out.push(u);
  }
  return out;
};

// Правила складываются, а не выбираются из списка. Это и есть основа
// конструктора: диагональ, гипер и кривые области — независимые галочки,
// а не пять отдельных игр. Движок про их смысл по-прежнему не знает.
export const PRESETS = {
  classic:  { size: 9, regions: 'boxes' },
  diagonal: { size: 9, regions: 'boxes',  diagonal: true },
  hyper:    { size: 9, regions: 'boxes',  hyper: true },
  jigsaw:   { size: 9, regions: 'jigsaw' },
  small:    { size: 6, regions: 'boxes' },
};

/** Читаемый и устойчивый ключ набора правил — для витрины и лидерборда. */
export function specKey(spec) {
  const s = normalize(spec);
  return [`${s.size}x${s.size}`, s.regions, s.diagonal && 'diag', s.hyper && 'hyper']
    .filter(Boolean).join('-');
}

export function normalize(spec) {
  const raw = typeof spec === 'string' ? PRESETS[spec] : spec;
  if (!raw) throw new Error('неизвестные правила: ' + spec);
  const s = { size: 9, regions: 'boxes', diagonal: false, hyper: false, ...raw };
  if (s.size !== 6 && s.size !== 9) throw new Error('размер только 6 или 9');
  // Гипер-квадраты сдвинуты внутрь поля 9x9 и на 6x6 просто не помещаются.
  if (s.hyper && s.size !== 9) throw new Error('гипер только на поле 9x9');
  return s;
}

/** Поле по набору правил: области, области каждой клетки и её соседи. */
export function makeBoard(spec, rnd = Math.random) {
  const s = normalize(spec);
  const n = s.size, cells = n * n;
  const [bh, bw] = n === 6 ? [2, 3] : [3, 3];

  const units = [...rowsCols(n)];
  units.push(...(s.regions === 'jigsaw' ? growRegions(rnd, n) : boxes(n, bh, bw)));
  if (s.diagonal) units.push(...diagonals(n));
  if (s.hyper) units.push(...hyper(n));

  const unitsOf = [...Array(cells)].map(() => []);
  units.forEach((u) => u.forEach((c) => unitsOf[c].push(u)));

  const peers = [...Array(cells)].map((_, c) => {
    const t = new Set();
    unitsOf[c].forEach((u) => u.forEach((x) => { if (x !== c) t.add(x); }));
    return [...t];
  });

  // Инварианты набора правил. Кривые области растятся случайно — без проверки
  // битая нарезка молча уехала бы в генератор и дала поле без решений.
  if (units.some((u) => u.length !== n)) throw new Error('область не из ' + n + ' клеток');
  if (unitsOf.some((u) => !u.length)) throw new Error('клетка вне областей');

  return { spec: s, variant: s.regions === 'jigsaw' ? 'jigsaw' : 'boxes', key: specKey(s),
           n, cells, units, unitSets: units.map((u) => new Set(u)), unitsOf, peers,
           full: (1 << n) - 1 };
}
