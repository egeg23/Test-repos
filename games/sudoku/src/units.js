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
  const owner = new Int8Array(n * n);
  for (let c = 0; c < n * n; c++) {
    owner[c] = Math.floor(Math.floor(c / n) / 3) * 3 + Math.floor((c % n) / 3);
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

export const VARIANTS = {
  classic:  { n: 9, build: () => [...rowsCols(9), ...boxes(9, 3, 3)] },
  diagonal: { n: 9, build: () => [...rowsCols(9), ...boxes(9, 3, 3), ...diagonals(9)] },
  hyper:    { n: 9, build: () => [...rowsCols(9), ...boxes(9, 3, 3), ...hyper(9)] },
  jigsaw:   { n: 9, build: (rnd) => [...rowsCols(9), ...growRegions(rnd)] },
  small:    { n: 6, build: () => [...rowsCols(6), ...boxes(6, 2, 3)] },
};

/** Поле варианта: области, области каждой клетки и её соседи. */
export function makeBoard(variant, rnd = Math.random) {
  const v = VARIANTS[variant];
  if (!v) throw new Error('неизвестный вариант: ' + variant);
  const n = v.n, cells = n * n;
  const units = v.build(rnd);

  const unitsOf = [...Array(cells)].map(() => []);
  units.forEach((u) => u.forEach((c) => unitsOf[c].push(u)));

  const peers = [...Array(cells)].map((_, c) => {
    const s = new Set();
    unitsOf[c].forEach((u) => u.forEach((x) => { if (x !== c) s.add(x); }));
    return [...s];
  });

  // Инвариант варианта: у каждой клетки есть хотя бы одна область, и в любой
  // области ровно n клеток. Кривые области растятся случайно — без проверки
  // кривой генератор молча выдаст поле без решения.
  if (units.some((u) => u.length !== n)) throw new Error('область не из ' + n + ' клеток');
  if (unitsOf.some((u) => !u.length)) throw new Error('клетка вне областей');

  // Множества для горячего пути: проверка «клетка в области» идёт
  // тысячи раз за одну задачу, по массиву это заметно дороже.
  const unitSets = units.map((u) => new Set(u));

  return { variant, n, cells, units, unitSets, unitsOf, peers, full: (1 << n) - 1 };
}
