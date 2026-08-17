// Процедурная графика. Ни одного растрового ассета: всё рисуется кодом.
//
// Стиль — трафаретная печать позднесоветской ведомственной брошюры:
// ограниченная палитра, но у каждой краски есть светлая и теневая ступень,
// красная «форма» печатается со сдвигом (приводка не сошлась), поверх лежит
// растровая сетка. Раньше правило было «ноль градиентов, шесть плоских
// красок» — оно и делало картинку похожей на заглушку.
//
// Чего здесь сознательно нет: feTurbulence и вообще SVG-фильтров. Фильтр
// растеризуется заново на каждой перерисовке, а render() переписывает весь
// innerHTML — на слабом Android это фризы (§1.15). Текстура сделана
// на <pattern> и градиентах: они уходят на GPU и перерисовки не боятся.

export const PALETTE = {
  paper:  '#F2E4C9',
  ink:    '#1A1A18',
  red:    '#C8452F',
  brass:  '#D9A441',
  slate:  '#2B4C5C',
  khaki:  '#7A8F6B',
};

const P = PALETTE;

// Ступени краски. Осветление и затемнение считаются от базы, чтобы у любой
// поверхности были свет и тень одной и той же краской, а не новым цветом.
function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) =>
    Math.max(0, Math.min(255, Math.round(k < 0 ? c * (1 + k) : c + (255 - c) * k))));
  return '#' + ch.map((c) => c.toString(16).padStart(2, '0')).join('');
}

// Идентификаторы градиентов и паттернов обязаны быть уникальными: на экране
// одновременно живёт несколько svg, а render() пересоздаёт их целиком.
let uid = 0;

const ART_W = 400, ART_H = 200;
const FLOOR = 132;

// ------------------------------------------------------------------ кабинеты
//
// Пять рангов — пять узнаваемо разных комнат. Это не украшательство:
// повышение игрок должен видеть, а не вычитывать из строки статуса.
// Предыдущая версия рисовала одну и ту же коробку на все ранги.

const ROOMS = [
  { wall: P.khaki, floor: P.slate, ceil: 0.20, desk: 96,  chair: 0,  light: 'bulb',
    title: 'подвальная канцелярия' },
  { wall: P.khaki, floor: P.slate, ceil: 0.14, desk: 116, chair: 26, light: 'window',
    title: 'комната с окном' },
  { wall: P.paper, floor: P.slate, ceil: 0.10, desk: 132, chair: 40, light: 'window',
    title: 'свой кабинет' },
  { wall: P.slate, floor: P.ink,   ceil: 0.08, desk: 148, chair: 54, light: 'window',
    title: 'кабинет с ковром' },
  { wall: P.slate, floor: P.ink,   ceil: 0.06, desk: 168, chair: 68, light: 'chandelier',
    title: 'кабинет заместителя' },
];

const o = `stroke="${P.ink}" stroke-width="2.5" stroke-linejoin="round"`;
const thin = `stroke="${P.ink}" stroke-width="1.5"`;

// Стеллаж с корешками дел. Плотность папок растёт с рангом — на нижнем
// ранге дела чужие и их много, на верхнем они уже не здесь.
function shelf(x, y, h, rows) {
  const out = [`<rect x="${x}" y="${y}" width="58" height="${h}" fill="${shade(P.paper, -0.25)}" ${o}/>`];
  for (let i = 0; i < rows; i++) {
    const ry = y + (h / rows) * i;
    for (let k = 0; k < 4; k++) {
      out.push(`<rect x="${x + 6 + k * 12}" y="${ry + 4}" width="9" height="${h / rows - 9}"
        fill="${k % 2 ? P.red : P.brass}" ${thin}/>`);
    }
    out.push(`<line x1="${x}" y1="${ry + h / rows - 3}" x2="${x + 58}" y2="${ry + h / rows - 3}" ${thin}/>`);
  }
  return out.join('');
}

function window_(x, y, w, h) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${shade(P.slate, 0.55)}" ${o}/>
    <rect x="${x}" y="${y}" width="${w}" height="${h * 0.45}" fill="${shade(P.slate, 0.7)}"/>
    <line x1="${x + w / 2}" y1="${y}" x2="${x + w / 2}" y2="${y + h}" ${o}/>
    <line x1="${x}" y1="${y + h / 2}" x2="${x + w}" y2="${y + h / 2}" ${o}/>
    <rect x="${x - 4}" y="${y + h}" width="${w + 8}" height="5" fill="${P.brass}" ${o}/>`;
}

// Рама на стене. До восьмого ранга она пустая: гвоздь есть, портрета нет.
function frame(x, y, w, h, filled) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${P.brass}" ${o}/>
    <rect x="${x + 5}" y="${y + 5}" width="${w - 10}" height="${h - 10}"
      fill="${filled ? shade(P.slate, 0.15) : shade(P.khaki, -0.2)}" ${thin}/>
    ${filled ? `<circle cx="${x + w / 2}" cy="${y + h * 0.42}" r="${w * 0.13}" fill="${P.ink}" opacity="0.55"/>
      <path d="M${x + w * 0.28} ${y + h - 6} q${w * 0.22} -${h * 0.3} ${w * 0.44} 0 z" fill="${P.ink}" opacity="0.55"/>` : ''}
    <circle cx="${x + w / 2}" cy="${y - 5}" r="2.5" fill="${P.ink}"/>`;
}

function flag(x, y, h) {
  return `<line x1="${x}" y1="${y}" x2="${x}" y2="${y + h}" stroke="${P.ink}" stroke-width="3"/>
    <path d="M${x} ${y} l26 5 l-26 6 z" fill="${P.red}" ${thin}/>
    <circle cx="${x}" cy="${y - 3}" r="3.5" fill="${P.brass}" ${thin}/>`;
}

// Герой за столом. Кресло растёт вместе с рангом — на табурете сидят прямо,
// в кресле заместителя откидываются.
function hero(cx, deskTop, chairH, rank) {
  const seat = deskTop + 26;
  const lean = rank >= 3 ? 4 : 0;
  return `
    ${chairH ? `<rect x="${cx - 26}" y="${seat - chairH}" width="52" height="${chairH}" rx="4"
      fill="${shade(P.brass, -0.45)}" ${o}/>
      ${rank >= 4 ? `<line x1="${cx - 26}" y1="${seat - chairH * 0.55}" x2="${cx + 26}" y2="${seat - chairH * 0.55}" ${thin}/>` : ''}` : ''}
    <path d="M${cx - 21 - lean} ${deskTop + 4} q1 -26 21 -28 q20 2 21 28 z" fill="${P.slate}" ${o}/>
    <rect x="${cx - 5}" y="${deskTop - 30}" width="10" height="9" fill="${shade(P.paper, -0.32)}"/>
    <circle cx="${cx}" cy="${deskTop - 38}" r="12" fill="${shade(P.paper, -0.22)}" ${o}/>
    <path d="M${cx - 12} ${deskTop - 41} q12 -11 24 0 q-4 -12 -12 -12 q-8 0 -12 12 z" fill="${P.ink}"/>`;
}

function deskUnit(cx, w, rank) {
  const top = FLOOR - 4;
  const x = cx - w / 2;
  return `
    ${hero(cx, top, ROOMS[rank].chair, rank)}
    <rect x="${x}" y="${top}" width="${w}" height="9" fill="${P.brass}" ${o}/>
    <rect x="${x}" y="${top + 9}" width="${w}" height="${ART_H - top - 9}"
      fill="${shade(P.brass, -0.5)}" ${o}/>
    ${rank >= 2 ? `<rect x="${x + 8}" y="${top + 18}" width="${w * 0.3}" height="4" fill="${P.ink}" opacity="0.5"/>
      <rect x="${x + 8}" y="${top + 30}" width="${w * 0.3}" height="4" fill="${P.ink}" opacity="0.5"/>` : ''}
    <rect x="${x + w - 40}" y="${top - 7}" width="30" height="7" fill="${shade(P.paper, 0.35)}" ${thin}/>
    <rect x="${x + w - 43}" y="${top - 11}" width="30" height="7" fill="${P.paper}" ${thin}/>
    ${rank >= 3 ? `<rect x="${x + 12}" y="${top - 13}" width="9" height="13" fill="${P.red}" ${thin}/>
      <rect x="${x + 9}" y="${top - 16}" width="15" height="4" fill="${shade(P.red, -0.3)}" ${thin}/>` : ''}`;
}

function fixtures(rank, id) {
  const r = ROOMS[rank];
  if (r.light === 'bulb') {
    return `<line x1="${ART_W * 0.5}" y1="0" x2="${ART_W * 0.5}" y2="26" stroke="${P.ink}" stroke-width="2"/>
      <circle cx="${ART_W * 0.5}" cy="32" r="8" fill="${P.brass}" ${o}/>`;
  }
  if (r.light === 'chandelier') {
    return `<line x1="${ART_W * 0.5}" y1="0" x2="${ART_W * 0.5}" y2="14" stroke="${P.ink}" stroke-width="3"/>
      <path d="M${ART_W * 0.5 - 30} 20 q30 22 60 0 z" fill="${P.brass}" ${o}/>
      <circle cx="${ART_W * 0.5 - 22}" cy="26" r="4" fill="${shade(P.brass, 0.4)}" ${thin}/>
      <circle cx="${ART_W * 0.5}" cy="31" r="4" fill="${shade(P.brass, 0.4)}" ${thin}/>
      <circle cx="${ART_W * 0.5 + 22}" cy="26" r="4" fill="${shade(P.brass, 0.4)}" ${thin}/>`;
  }
  return `<line x1="${ART_W * 0.5}" y1="0" x2="${ART_W * 0.5}" y2="18" stroke="${P.ink}" stroke-width="2"/>
    <rect x="${ART_W * 0.5 - 26}" y="18" width="52" height="7" fill="${P.paper}" ${o}/>
    <rect x="${ART_W * 0.5 - 26}" y="18" width="52" height="3" fill="${shade(P.brass, 0.2)}"/>`;
}

// Обстановка по рангу. Список читается сверху вниз как карьера:
// ведро под протечкой → окно → сейф → ковёр и портрет → флаги и панели.
function decor(rank) {
  const parts = [];
  if (rank === 0) {
    parts.push(shelf(24, 34, 96, 4));
    parts.push(`<path d="M328 ${FLOOR - 2} l32 0 l-4 22 l-24 0 z" fill="${shade(P.slate, 0.3)}" ${o}/>
      <path d="M330 ${FLOOR + 4} l28 0" stroke="${shade(P.paper, 0.2)}" stroke-width="3" opacity="0.6"/>`);
    parts.push(`<circle cx="344" cy="52" r="3" fill="${shade(P.paper, 0.3)}" opacity="0.75"/>
      <circle cx="344" cy="78" r="3.5" fill="${shade(P.paper, 0.3)}" opacity="0.6"/>
      <circle cx="344" cy="104" r="4" fill="${shade(P.paper, 0.3)}" opacity="0.45"/>
      <path d="M336 30 q8 -7 16 0 q-8 5 -16 0 z" fill="${shade(P.ink, 0.1)}" ${thin}/>`);
  }
  if (rank === 1) { parts.push(shelf(24, 44, 86, 3)); parts.push(window_(300, 40, 70, 56)); }
  if (rank === 2) {
    parts.push(window_(296, 34, 74, 60));
    parts.push(`<rect x="24" y="${FLOOR - 46}" width="46" height="46" fill="${shade(P.ink, 0.15)}" ${o}/>
      <circle cx="47" cy="${FLOOR - 23}" r="9" fill="${P.brass}" ${o}/>`);
    parts.push(frame(150, 30, 46, 40, false));
  }
  if (rank === 3) {
    parts.push(window_(300, 30, 74, 62));
    parts.push(frame(30, 26, 54, 48, true));
    parts.push(flag(120, 34, 62));
    parts.push(`<rect y="${FLOOR + 26}" width="${ART_W}" height="26" fill="${P.red}" opacity="0.75"/>
      <rect y="${FLOOR + 26}" width="${ART_W}" height="4" fill="${shade(P.red, -0.35)}"/>`);
  }
  if (rank === 4) {
    parts.push(`<rect y="${FLOOR - 46}" width="${ART_W}" height="46" fill="${shade(P.brass, -0.74)}"/>
      <line x1="0" y1="${FLOOR - 46}" x2="${ART_W}" y2="${FLOOR - 46}" ${o}/>`);
    for (let i = 0; i < 7; i++) {
      parts.push(`<line x1="${i * 58 + 14}" y1="${FLOOR - 46}" x2="${i * 58 + 14}" y2="${FLOOR}" ${thin}/>`);
    }
    parts.push(frame(26, 22, 60, 54, true));
    parts.push(flag(300, 26, 70));
    parts.push(flag(340, 26, 70));
    parts.push(`<rect y="${FLOOR + 22}" width="${ART_W}" height="30" fill="${P.red}" opacity="0.8"/>
      <rect y="${FLOOR + 22}" width="${ART_W}" height="4" fill="${shade(P.red, -0.35)}"/>`);
  }
  return parts.join('');
}

/**
 * Кадр кабинета по индексу ранга (0..4).
 * Второй аргумент оставлен для совместимости со старыми вызовами и не влияет
 * на разметку: размер задаёт viewBox, а не атрибуты.
 */
export function location(rank) {
  const i = Math.max(0, Math.min(ROOMS.length - 1, Number(rank) || 0));
  const r = ROOMS[i];
  const id = 'a' + (++uid);
  const lit = r.light === 'window';

  return `<svg viewBox="0 0 ${ART_W} ${ART_H}" class="scene" role="img"
      aria-label="${r.title}" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="w${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${shade(r.wall, -0.28)}"/>
        <stop offset="0.55" stop-color="${r.wall}"/>
        <stop offset="1" stop-color="${shade(r.wall, 0.12)}"/>
      </linearGradient>
      <linearGradient id="f${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${shade(r.floor, -0.35)}"/>
        <stop offset="1" stop-color="${shade(r.floor, 0.18)}"/>
      </linearGradient>
      <radialGradient id="v${id}" cx="0.5" cy="0.45" r="0.78">
        <stop offset="0.55" stop-color="${P.ink}" stop-opacity="0"/>
        <stop offset="1" stop-color="${P.ink}" stop-opacity="0.42"/>
      </radialGradient>
      <!-- Растровая сетка вместо шума: паттерн не пересчитывается при
           перерисовке, в отличие от feTurbulence. -->
      <pattern id="h${id}" width="4" height="4" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="0.8" fill="${P.ink}"/>
      </pattern>
    </defs>

    <rect width="${ART_W}" height="${ART_H}" fill="url(#w${id})"/>
    <rect y="${ART_H * r.ceil}" width="${ART_W}" height="3" fill="${P.ink}" opacity="0.25"/>
    <rect y="${FLOOR}" width="${ART_W}" height="${ART_H - FLOOR}" fill="url(#f${id})"/>

    ${fixtures(i, id)}
    ${decor(i)}

    <line x1="0" y1="${FLOOR}" x2="${ART_W}" y2="${FLOOR}" stroke="${P.ink}" stroke-width="3"/>
    <rect y="${FLOOR - 12}" width="${ART_W}" height="12" fill="${P.ink}" opacity="0.16"/>

    ${lit ? `<path d="M300 40 L374 40 L${ART_W} ${ART_H} L150 ${ART_H} z"
      fill="${shade(P.paper, 0.5)}" opacity="0.13"/>` : ''}

    ${deskUnit(ART_W * 0.5, r.desk, i)}

    <rect width="${ART_W}" height="${ART_H}" fill="url(#h${id})" opacity="0.07"/>
    <rect width="${ART_W}" height="${ART_H}" fill="url(#v${id})"/>
  </svg>`;
}

// ------------------------------------------------------------------ портреты
//
// Лицо меняется вместе с отношением. Раньше все пятеро смотрели одинаково,
// и состояние связи читалось только из подписи под именем.

const SILHOUETTES = {
  suit:    { collar: 'M30 96 q0 -26 18 -30 l0 -7 l12 0 l0 7 q18 4 18 30 z', tie: true },
  dress:   { collar: 'M28 96 q2 -28 20 -31 l0 -7 l12 0 l0 7 q18 3 20 31 z', tie: false },
  uniform: { collar: 'M28 96 q0 -28 20 -30 l0 -7 l12 0 l0 7 q20 2 20 30 z', tie: false },
  plain:   { collar: 'M31 96 q0 -25 17 -29 l0 -7 l12 0 l0 7 q17 4 17 29 z', tie: false },
};

const MOODS = {
  enemy:   { brow: 'M34 41 l12 5 M62 41 l-12 5', mouth: 'M38 66 q10 -7 20 0' },
  grudge:  { brow: 'M34 40 l12 3 M62 40 l-12 3', mouth: 'M39 65 q9 -4 18 0' },
  neutral: { brow: 'M34 41 l12 0 M62 41 l-12 0', mouth: 'M39 64 l18 0' },
  friend:  { brow: 'M34 42 l12 -3 M62 42 l-12 -3', mouth: 'M39 62 q9 6 18 0' },
  inner:   { brow: 'M34 43 l12 -4 M62 43 l-12 -4', mouth: 'M37 61 q11 9 20 0' },
};

export function portrait(kind, color, initials, size = 96, mood = 'neutral') {
  const s = SILHOUETTES[kind] || SILHOUETTES.plain;
  const m = MOODS[mood] || MOODS.neutral;
  const id = 'p' + (++uid);
  const skin = shade(P.paper, -0.16);
  return `<svg viewBox="0 0 96 96" width="${size}" height="${size}" class="face" role="img"
      aria-label="${initials}">
    <defs><clipPath id="c${id}"><circle cx="48" cy="48" r="45"/></clipPath></defs>
    <circle cx="48" cy="48" r="45" fill="${shade(color, 0.18)}"/>
    <g clip-path="url(#c${id})">
      <rect y="52" width="96" height="44" fill="${shade(color, -0.3)}"/>
      <path d="${s.collar}" fill="${color}" ${thin}/>
      ${s.tie ? `<path d="M48 59 l5 5 l-5 24 l-5 -24 z" fill="${P.red}" ${thin}/>` : ''}
      <path d="M32 40 q0 -22 16 -22 q16 0 16 22 q0 20 -16 20 q-16 0 -16 -20 z" fill="${skin}" ${thin}/>
      <circle cx="41" cy="47" r="2.6" fill="${P.ink}"/>
      <circle cx="55" cy="47" r="2.6" fill="${P.ink}"/>
      <path d="${m.brow}" stroke="${P.ink}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
      <path d="${m.mouth}" stroke="${P.ink}" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <path d="M30 34 q18 -16 36 0 q-6 -20 -18 -20 q-12 0 -18 20 z" fill="${P.ink}" opacity="0.9"/>
    </g>
    <circle cx="48" cy="48" r="45" fill="none" stroke="${P.ink}" stroke-width="3"/>
  </svg>`;
}

// ------------------------------------------------------------------ печати

// Круглая печать. Красная форма печатается со сдвигом — приводка не сошлась,
// как на настоящем ведомственном бланке.
export function stamp(text, size = 120, angle = -9) {
  const id = 's' + (++uid);
  // Геометрия: внешнее кольцо 54, внутреннее 38, надпись сидит базовой линией
  // на радиусе 41 и растёт наружу — так буквы попадают ровно в поясок между
  // кольцами. Дуга разомкнутая и слева направо: на замкнутой окружности
  // нижняя половина надписи вставала вверх ногами.
  return `<svg viewBox="0 0 120 120" width="${size}" height="${size}" class="stamp" role="img"
      aria-label="${text}">
    <defs><path id="r${id}" d="M19 60 A41 41 0 0 1 101 60" fill="none"/></defs>
    <g transform="rotate(${angle} 60 60)" fill="none" stroke="${P.red}" opacity="0.85">
      <circle cx="60" cy="60" r="54" stroke-width="4"/>
      <circle cx="60" cy="60" r="38" stroke-width="2"/>
      <text font-size="9.5" font-family="Georgia,serif" font-weight="700"
        fill="${P.red}" stroke="none" letter-spacing="0.6">
        <textPath href="#r${id}" startOffset="50%" text-anchor="middle">${text}</textPath>
      </text>
      <path d="M43 61 l10 11 l25 -25" stroke-width="6" stroke-linecap="round"/>
      <line x1="40" y1="80" x2="80" y2="78" stroke-width="2.5"/>
    </g>
  </svg>`;
}

// Герб вымышленной федерации: циркуль над печатью в венке из скрепок.
export function emblem(size = 72) {
  const id = 'e' + (++uid);
  return `<svg viewBox="0 0 72 72" width="${size}" height="${size}" aria-hidden="true">
    <defs>
      <radialGradient id="g${id}" cx="0.38" cy="0.32" r="0.75">
        <stop offset="0" stop-color="${shade(P.brass, 0.4)}"/>
        <stop offset="1" stop-color="${shade(P.brass, -0.28)}"/>
      </radialGradient>
    </defs>
    <circle cx="36" cy="36" r="31" fill="url(#g${id})" stroke="${P.ink}" stroke-width="3"/>
    <circle cx="36" cy="36" r="25" fill="none" stroke="${P.ink}" stroke-width="1" opacity="0.45"/>
    <path d="M36 17 L25 47 M36 17 L47 47" stroke="${P.ink}" stroke-width="4" fill="none"/>
    <circle cx="36" cy="17" r="4.5" fill="${P.ink}"/>
    <rect x="23" y="47" width="26" height="8" fill="${P.red}" stroke="${P.ink}" stroke-width="2"/>
    <rect x="23" y="47" width="26" height="3" fill="${shade(P.red, 0.3)}"/>
  </svg>`;
}
