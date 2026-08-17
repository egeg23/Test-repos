// Процедурная графика. Ни одного растрового ассета: всё рисуется кодом
// в шести красках. Стиль выбран инженерно, а не по вкусу — он полностью
// описывается конечным списком (шесть цветов, одна толщина контура,
// ноль градиентов), поэтому его держит код, а не глаз.

import { mulberry32 } from './rng.js';

export const PALETTE = {
  paper:  '#F2E4C9',
  ink:    '#1A1A18',
  red:    '#C8452F',
  brass:  '#D9A441',
  slate:  '#2B4C5C',
  khaki:  '#7A8F6B',
};

const P = PALETTE;

// Локации. Раскладка детерминирована хешем идентификатора, поэтому одна
// и та же локация всегда выглядит одинаково, а разные — по-разному.
const LOCATIONS = {
  office:   { wall: P.khaki, floor: P.slate, props: ['desk', 'window', 'portrait'] },
  corridor: { wall: P.paper, floor: P.slate, props: ['door', 'plant', 'door'] },
  bath:     { wall: P.brass, floor: P.khaki, props: ['bench', 'bucket', 'window'] },
  office2:  { wall: P.slate, floor: P.ink,   props: ['desk', 'safe', 'portrait'] },
  chancel:  { wall: P.khaki, floor: P.slate, props: ['shelf', 'desk', 'portrait'] },
};

const hash = (s) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);

function prop(kind, x, base, rnd) {
  // Все высоты — доли от линии пола, поэтому предметы всегда помещаются
  // в кадр любой пропорции. Фиксированные значения раньше вылезали
  // за верхний край, когда полоса становилась узкой.
  const u = base;
  const o = `stroke="${P.ink}" stroke-width="3"`;
  const w = 44 + Math.floor(rnd() * 22);
  switch (kind) {
    case 'window':
      return `<rect x="${x}" y="${u * 0.18}" width="${w + 16}" height="${u * 0.42}" fill="${P.paper}" ${o}/>
              <line x1="${x + (w + 16) / 2}" y1="${u * 0.18}" x2="${x + (w + 16) / 2}" y2="${u * 0.6}" ${o}/>`;
    case 'portrait':
      // Рама на стене всегда пустая: портрета нет, а гвоздь остался.
      return `<rect x="${x}" y="${u * 0.14}" width="${w}" height="${u * 0.34}" fill="${P.paper}" ${o}/>
              <rect x="${x + 6}" y="${u * 0.18}" width="${w - 12}" height="${u * 0.26}" fill="${P.khaki}" ${o}/>
              <circle cx="${x + w / 2}" cy="${u * 0.11}" r="3" fill="${P.ink}"/>`;
    case 'desk':
      return `<rect x="${x}" y="${u * 0.78}" width="${w + 40}" height="${u * 0.05}" fill="${P.brass}" ${o}/>
              <rect x="${x + 6}" y="${u * 0.83}" width="9" height="${u * 0.17}" fill="${P.ink}"/>
              <rect x="${x + w + 25}" y="${u * 0.83}" width="9" height="${u * 0.17}" fill="${P.ink}"/>`;
    case 'safe':
      return `<rect x="${x}" y="${u * 0.62}" width="${w}" height="${u * 0.38}" fill="${P.ink}" ${o}/>
              <circle cx="${x + w / 2}" cy="${u * 0.81}" r="${u * 0.07}" fill="${P.brass}" ${o}/>`;
    case 'shelf': {
      // Стеллаж с корешками папок: без них читался как окно.
      const top = u * 0.16, hgt = u * 0.84, rows = 3;
      const files = [];
      for (let i = 0; i < rows; i++) {
        const y = top + (hgt / rows) * i;
        for (let k = 0; k < 4; k++) {
          files.push(`<rect x="${x + 7 + k * 11}" y="${y + hgt / rows * 0.18}"
            width="8" height="${hgt / rows * 0.55}" fill="${k % 2 ? P.red : P.brass}"
            stroke="${P.ink}" stroke-width="1.5"/>`);
        }
        files.push(`<line x1="${x}" y1="${y + hgt / rows * 0.82}" x2="${x + 54}" y2="${y + hgt / rows * 0.82}" ${o}/>`);
      }
      return `<rect x="${x}" y="${top}" width="54" height="${hgt}" fill="${P.paper}" ${o}/>${files.join('')}`;
    }
    case 'door':
      return `<rect x="${x}" y="${u * 0.1}" width="${w + 12}" height="${u * 0.9}" fill="${P.brass}" ${o}/>
              <circle cx="${x + w}" cy="${u * 0.55}" r="4" fill="${P.ink}"/>`;
    case 'plant':
      return `<rect x="${x + 10}" y="${u * 0.8}" width="28" height="${u * 0.2}" fill="${P.red}" ${o}/>
              <path d="M${x + 24} ${u * 0.8} q -22 -${u * 0.3} -4 -${u * 0.48} q 20 ${u * 0.18} 4 ${u * 0.48} z" fill="${P.khaki}" ${o}/>`;
    case 'bench':
      return `<rect x="${x}" y="${u * 0.82}" width="${w + 60}" height="${u * 0.05}" fill="${P.brass}" ${o}/>`;
    default:
      return `<rect x="${x}" y="${u * 0.6}" width="${w}" height="${u * 0.4}" fill="${P.brass}" ${o}/>`;
  }
}

// Кадр всегда рисуется в одной логической системе координат 400×300:
// предметы имеют фиксированные высоты (стеллаж — 140), и при меньшем
// viewBox они уходили за верхний край. Видимый размер задаётся стилями,
// масштабированием занимается сам viewBox.
const ART_W = 400, ART_H = 170;

export function location(id, w = ART_W, h = ART_H) {
  const cfg = LOCATIONS[id] || LOCATIONS.office;
  const rnd = mulberry32(hash(id));
  const floorY = Math.round(ART_H * 0.68);
  const props = cfg.props
    .map((k, i) => prop(k, 30 + i * Math.round((ART_W - 90) / cfg.props.length), floorY, rnd))
    .join('');
  // preserveAspectRatio с slice: при узкой полосе кадр обрезается по бокам,
  // а не сплющивается, и линия пола остаётся на месте.
  return `<svg viewBox="0 0 ${ART_W} ${ART_H}" class="scene" aria-hidden="true"
      preserveAspectRatio="xMidYMid meet">
    <rect width="${ART_W}" height="${ART_H}" fill="${cfg.wall}"/>
    <rect y="${floorY}" width="${ART_W}" height="${ART_H - floorY}" fill="${cfg.floor}"/>
    <line x1="0" y1="${floorY}" x2="${ART_W}" y2="${floorY}" stroke="${P.ink}" stroke-width="4"/>
    <rect y="${floorY - 10}" width="${ART_W}" height="10" fill="${P.ink}" opacity="0.18"/>
    ${props}
  </svg>`;
}

// Портрет: круг по рангу плюс силуэт. Заглушка сохраняет ровно те признаки,
// по которым персонаж опознаётся — силуэт, цвет, инициалы, — поэтому подмена
// на растр не потребует переверстки.
const SILHOUETTES = {
  suit:    'M32 62 q0 -20 16 -22 l0 -6 q-8 -4 -8 -14 q0 -12 12 -12 q12 0 12 12 q0 10 -8 14 l0 6 q16 2 16 22 z',
  dress:   'M32 62 q2 -22 18 -24 l0 -6 q-8 -4 -8 -14 q0 -12 12 -12 q12 0 12 12 q0 10 -8 14 l0 6 q16 2 18 24 z',
  uniform: 'M30 62 q0 -22 18 -23 l0 -7 q-8 -4 -8 -14 q0 -12 12 -12 q12 0 12 12 q0 10 -8 14 l0 7 q18 1 18 23 z',
  plain:   'M33 62 q0 -19 15 -21 l0 -7 q-7 -4 -7 -13 q0 -11 11 -11 q11 0 11 11 q0 9 -7 13 l0 7 q15 2 15 21 z',
};

export function portrait(kind, color, initials, size = 96) {
  const d = SILHOUETTES[kind] || SILHOUETTES.plain;
  return `<svg viewBox="0 0 96 96" width="${size}" height="${size}" class="face" aria-hidden="true">
    <circle cx="48" cy="48" r="46" fill="${color}" stroke="${P.ink}" stroke-width="3"/>
    <path d="${d}" fill="${P.ink}" opacity="0.85"/>
    <text x="48" y="90" text-anchor="middle" font-size="14" fill="${P.ink}"
      font-family="serif" font-weight="700">${initials}</text>
  </svg>`;
}

// Герб вымышленной федерации: циркуль над печатью в венке из скрепок.
export function emblem(size = 72) {
  return `<svg viewBox="0 0 72 72" width="${size}" height="${size}" aria-hidden="true">
    <circle cx="36" cy="36" r="30" fill="${P.brass}" stroke="${P.ink}" stroke-width="3"/>
    <path d="M36 18 L26 46 M36 18 L46 46" stroke="${P.ink}" stroke-width="4" fill="none"/>
    <circle cx="36" cy="18" r="4" fill="${P.ink}"/>
    <rect x="24" y="46" width="24" height="8" fill="${P.red}" stroke="${P.ink}" stroke-width="2"/>
  </svg>`;
}
