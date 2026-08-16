// Коллекция из 40 бочонков-достижений. Хранится битовой маской в base64:
// облачное сохранение перезаписывается целиком, поэтому состояние держим компактным.

import { SIZE } from './scoring.js';

// id — позиция бита, менять порядок нельзя: сломает сохранения игроков.
export const ACHIEVEMENTS = [
  { id: 0,  key: 'first_game',   need: (c) => c.gamesPlayed >= 1 },
  { id: 1,  key: 'games_5',      need: (c) => c.gamesPlayed >= 5 },
  { id: 2,  key: 'games_25',     need: (c) => c.gamesPlayed >= 25 },
  { id: 3,  key: 'games_100',    need: (c) => c.gamesPlayed >= 100 },
  { id: 4,  key: 'score_50',     need: (c) => c.score >= 50 },
  { id: 5,  key: 'score_100',    need: (c) => c.score >= 100 },
  { id: 6,  key: 'score_150',    need: (c) => c.score >= 150 },
  { id: 7,  key: 'score_200',    need: (c) => c.score >= 200 },
  { id: 8,  key: 'score_250',    need: (c) => c.score >= 250 },
  { id: 9,  key: 'row_full',     need: (c) => c.fullRows >= 1 },
  { id: 10, key: 'row_full_2',   need: (c) => c.fullRows >= 2 },
  { id: 11, key: 'row_full_3',   need: (c) => c.fullRows >= 3 },
  { id: 12, key: 'row_full_all', need: (c) => c.fullRows >= SIZE },
  { id: 13, key: 'col_full',     need: (c) => c.fullCols >= 1 },
  { id: 14, key: 'col_full_2',   need: (c) => c.fullCols >= 2 },
  { id: 15, key: 'col_full_3',   need: (c) => c.fullCols >= 3 },
  { id: 16, key: 'diag_full',    need: (c) => c.fullDiags >= 1 },
  { id: 17, key: 'diag_both',    need: (c) => c.fullDiags >= 2 },
  { id: 18, key: 'rows_only',    need: (c) => c.rowPoints >= 60 },
  { id: 19, key: 'cols_only',    need: (c) => c.colPoints >= 60 },
  { id: 20, key: 'diags_only',   need: (c) => c.diagPoints >= 24 },
  { id: 21, key: 'balanced',     need: (c) => c.rowPoints >= 30 && c.colPoints >= 30 && c.diagPoints >= 12 },
  { id: 22, key: 'daily_1',      need: (c) => c.dailyPlayed >= 1 },
  { id: 23, key: 'daily_3',      need: (c) => c.streak >= 3 },
  { id: 24, key: 'daily_7',      need: (c) => c.streak >= 7 },
  { id: 25, key: 'daily_30',     need: (c) => c.streak >= 30 },
  { id: 26, key: 'no_undo',      need: (c) => c.usedUndo === false && c.score >= 100 },
  { id: 27, key: 'beat_best',    need: (c) => c.newBest === true },
  { id: 28, key: 'beat_median',  need: (c) => c.percentile !== null && c.percentile >= 80 },
  { id: 29, key: 'perfect_row',  need: (c) => c.ascendingFull >= 1 },
  { id: 30, key: 'decade_five',  need: (c) => c.decadeFive >= 1 },
  { id: 31, key: 'parity_five',  need: (c) => c.parityFive >= 1 },
  { id: 32, key: 'lotto_win',    need: (c) => c.lottoWins >= 1 },
  { id: 33, key: 'lotto_win_5',  need: (c) => c.lottoWins >= 5 },
  { id: 34, key: 'lotto_clean',  need: (c) => c.lottoMissed === 0 && c.lottoWon === true },
  { id: 35, key: 'both_modes',   need: (c) => c.lottoWins >= 1 && c.gamesPlayed >= 1 },
  { id: 36, key: 'low_score',    need: (c) => c.score > 0 && c.score <= 20 },
  { id: 37, key: 'comeback',     need: (c) => c.improvedBy >= 50 },
  { id: 38, key: 'all_rules',    need: (c) => c.rulesActive >= 3 },
  { id: 39, key: 'collector',    need: (c, unlockedCount) => unlockedCount >= 30 },
];

export const TOTAL = ACHIEVEMENTS.length;

export function decode(str) {
  const bits = new Uint8Array(Math.ceil(TOTAL / 8));
  if (!str) return bits;
  try {
    const bin = atob(str);
    for (let i = 0; i < bits.length && i < bin.length; i++) bits[i] = bin.charCodeAt(i);
  } catch { /* повреждённое сохранение — начинаем с пустой коллекции */ }
  return bits;
}

export function encode(bits) {
  let bin = '';
  for (const b of bits) bin += String.fromCharCode(b);
  try { return btoa(bin); } catch { return ''; }
}

export function has(bits, id) {
  return !!(bits[id >> 3] & (1 << (id & 7)));
}

export function set(bits, id) {
  bits[id >> 3] |= 1 << (id & 7);
}

export function countUnlocked(bits) {
  let n = 0;
  for (let i = 0; i < TOTAL; i++) if (has(bits, i)) n++;
  return n;
}

// Возвращает список новых достижений, которые открылись этой партией.
export function evaluate(saveStr, ctx) {
  const bits = decode(saveStr);
  const already = countUnlocked(bits);
  const fresh = [];
  for (const a of ACHIEVEMENTS) {
    if (has(bits, a.id)) continue;
    let ok = false;
    try { ok = !!a.need(ctx, already + fresh.length); } catch { ok = false; }
    if (ok) { set(bits, a.id); fresh.push(a); }
  }
  return { encoded: encode(bits), fresh, unlocked: countUnlocked(bits) };
}
