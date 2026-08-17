// Точка входа: загрузка, экраны, оба режима.

import * as sdk from './sdk.js';
import * as store from './storage.js';
import { t, setLang, achTitle } from './i18n.js';
import { daySeed, dayKey } from './rng.js';
import { SIZE, EMPTY } from './scoring.js';
import * as M from './master.js';
import * as D from './drum.js';
import * as L from './lotto.js';
import * as ach from './achievements.js';
import * as stats from './stats.js';
import { sfx, setMuted, isMuted, suspend as audioSuspend, resume as audioResume } from './audio.js';

const app = document.getElementById('app');

let save = null;
let view = 'menu';
let game = null;        // партия «Карточки мастера»
let lotto = null;
let lottoTimer = null;
let lastResult = null;
let peeked = null;
let adCounter = 0;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const isMobile = () => sdk.state.deviceType === 'mobile' || matchMedia('(pointer: coarse)').matches;

// ---------------------------------------------------------------- запуск

async function boot() {
  // Только быстрая часть SDK: язык и тип устройства. Ни одного сетевого
  // запроса — иначе меню ждало бы сеть, а Game Ready API вызывался бы
  // с опозданием (требование 1.19).
  await sdk.init();

  // Локальное сохранение читается синхронно. Облако догоняет позже.
  save = store.loadLocal();

  // Требование 2.14: язык берётся из environment.i18n.lang при запуске.
  // Сохранённое значение НЕ должно перебивать язык платформы — иначе модерация,
  // переключая языки через debug-панель, не увидит изменений.
  setLang(sdk.state.lang);
  setMuted(!!save.muted);

  go('menu');

  // Требование 1.19: сигнал ровно в момент, когда игрок может начать играть —
  // то есть когда меню отрисовано на экране. Раньше нельзя (ещё видна загрузка),
  // позже нельзя (игра уже играбельна). requestAnimationFrame попадает
  // в кадр, в котором меню появляется.
  requestAnimationFrame(() => sdk.loadingReady());

  // Всё сетевое — после того, как игра стала доступна: серверное время,
  // игрок, лидерборды и облачное сохранение.
  sdk.initDeferred()
    .then(() => store.syncCloud())
    .then((changed) => {
      save = store.get();
      if (changed && view === 'menu') render();
    })
    .catch(() => {});

  window.addEventListener('beforeunload', () => { store.flush(); });

  // Требование 1.3: при уходе со вкладки звук замолкает. Заодно замораживаем
  // розыгрыш лото — иначе ведущий доставал бы бочонки, пока игрока нет,
  // и он вернулся бы к проигранной партии.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      store.flush();
      audioSuspend();
      stopLottoTimer();
    } else {
      audioResume();
      if (view === 'lotto' && lotto && !lotto.finished) scheduleLotto(1200);
    }
  });
  window.addEventListener('blur', audioSuspend);
  window.addEventListener('focus', audioResume);

  // Требование 1.6: контекстное меню браузера не должно перехватывать
  // правый клик и долгий тап по игровому полю.
  app.addEventListener('contextmenu', (e) => e.preventDefault());
}

const PLAY_VIEWS = ['master', 'lotto', 'drum'];
const isPlayView = (v) => PLAY_VIEWS.includes(v);

function go(next) {
  if (isPlayView(view)) sdk.gameplayStop();
  stopLottoTimer();
  view = next;
  render();
  if (isPlayView(view)) {
    sdk.gameplayStart();
    // Баннер убираем на время партии: поле занимает экран целиком,
    // и перекрытие мешало бы попадать по клеткам.
    sdk.hideBanner();
  } else {
    sdk.showBanner();
  }
}

function render() {
  const html = {
    menu: renderMenu, master: renderMaster, lotto: renderLotto, drum: renderDrum,
    result: renderResult, achievements: renderAch, stats: renderStats, how: renderHow,
  }[view]();
  app.innerHTML = html;
}

// ---------------------------------------------------------------- меню

function todayKey() { return dayKey(sdk.now()); }

function renderMenu() {
  const done = save.lastDailyKey === todayKey();
  const unlocked = ach.countUnlocked(ach.decode(save.achievements));
  return `
  <div class="bar">
    <div class="bar__spacer"></div>
    <button class="iconbtn" data-act="sound" aria-label="${esc(t(isMuted() ? 'sound_off' : 'sound_on'))}">${isMuted() ? '🔇' : '🔊'}</button>
  </div>
  <div class="menu">
    <h1>${esc(t('title'))}</h1>
    <p class="menu__sub">${esc(t('tagline'))}</p>
    <button class="btn btn--main" data-act="lotto">${esc(t('play_lotto'))}</button>
    <button class="btn" data-act="daily" ${done ? 'disabled' : ''}>
      ${esc(t('play_daily'))}
      <span class="btn__note">${done ? esc(t('daily_done')) : esc(t('play_master'))}</span>
    </button>
    <button class="btn" data-act="free">${esc(t('play_free'))}
      <span class="btn__note">${esc(t('play_master'))}</span></button>
    <button class="btn" data-act="drum">${esc(t('play_drum'))}
      <span class="btn__note">${esc(t('drum_sub'))}</span></button>
    <button class="btn btn--ghost" data-act="how">${esc(t('how_to'))}</button>
    <button class="btn btn--ghost" data-act="ach">${esc(t('achievements'))} · ${unlocked}/${ach.TOTAL}</button>
    <button class="btn btn--ghost" data-act="stats">${esc(t('stats'))}</button>
  </div>`;
}

// Кнопка бонуса за рекламу. Требование 4.5: игрок должен явно согласиться,
// поэтому на самой кнопке написано, что последует ролик. Пометка не рисуется,
// когда реклама недоступна — тогда бонус выдаётся бесплатно и обещать нечего.
function adBtn(act, label, disabled) {
  const note = sdk.hasAds() ? `<span class="btn__note">▶ ${esc(t('ad_note'))}</span>` : '';
  return `<button class="btn btn--ghost" data-act="${act}" ${disabled ? 'disabled' : ''}>${esc(label)}${note}</button>`;
}

// ---------------------------------------------------------------- карточка мастера

function startMaster(mode) {
  const seed = mode === 'daily' ? daySeed(sdk.now()) : (Math.floor(Math.random() * 1e9) | 0);
  game = M.createGame({ seed, gamesPlayed: save.gamesPlayed || 0, mode });
  peeked = null;
  go('master');
  sfx.roll();
}

function renderMaster() {
  const value = M.currentBarrel(game);
  const sc = M.score(game);
  const preview = new Map();
  for (const p of M.previewAll(game)) preview.set(p.row * SIZE + p.cell, p);

  let cells = '';
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const v = game.grid[r][c];
      if (v !== EMPTY) {
        cells += `<div class="cell" data-r="${r}" data-c="${c}">${v}</div>`;
      } else {
        const p = preview.get(r * SIZE + c);
        const d = p ? p.delta : 0;
        const cls = d > 0 ? '' : (d < 0 ? ' cell__delta--bad' : ' cell__delta--zero');
        const badge = `<span class="cell__delta${cls}">${d > 0 ? '+' : ''}${d}</span>`;
        cells += `<button class="cell cell--empty" data-act="place" data-r="${r}" data-c="${c}"
          aria-label="${r + 1}-${c + 1}">${badge}</button>`;
      }
    }
  }

  const rules = game.rules.map((k) => t('rule_' + k)).join(' · ');
  // На первом ходу все клетки равноценны — честно об этом говорим,
  // иначе игрок ищет смысл в двадцати пяти нулях.
  const hint = game.placements.length === 0
    ? t('first_move')
    : `${isMobile() ? t('place_hint_mobile') : t('place_hint')} — ${rules}`;
  const peekRow = peeked
    ? `<div class="hint">${peeked.map((n) => `<b>${n}</b>`).join(' · ')}</div>` : '';

  return `
  <div class="bar">
    <button class="iconbtn" data-act="menu" aria-label="${esc(t('back'))}">←</button>
    <div class="pill"><span class="pill__k">${esc(t('bag_left'))}</span>
      <span class="pill__v">${M.barrelsLeft(game)}</span></div>
    <div class="bar__spacer"></div>
    <div class="pill"><span class="pill__k">${esc(t('score'))}</span>
      <span class="pill__v">${sc.total}</span></div>
    <button class="iconbtn" data-act="sound">${isMuted() ? '🔇' : '🔊'}</button>
  </div>

  <div class="play">
    <div class="barrel barrel--lg barrel--roll" aria-label="${esc(t('current_barrel'))} ${value ?? ''}">${value ?? ''}</div>
    <div class="grid">${cells}</div>
  </div>

  <div class="hint">${esc(hint)}</div>
  ${peekRow}

  <div class="bar">
    ${adBtn('undo', t('undo'), game.undoUsed || !game.placements.length)}
    ${adBtn('peek', t('peek'), game.peekUsed)}
  </div>`;
}

function doPlace(r, c) {
  const res = M.place(game, r, c);
  if (!res) return;
  sfx.place();

  const gained = res.changed.filter((l) => l.delta > 0);
  render();

  // Волна подсветки по сработавшим линиям — 40 мс на клетку.
  if (gained.length) {
    sfx.line();
    const cellsOf = (l) => {
      const out = [];
      for (let i = 0; i < SIZE; i++) {
        if (l.kind === 'row') out.push([l.index, i]);
        else if (l.kind === 'col') out.push([i, l.index]);
        else out.push(l.index === 0 ? [i, i] : [i, SIZE - 1 - i]);
      }
      return out;
    };
    gained.forEach((l) => {
      cellsOf(l).forEach(([rr, cc], i) => {
        setTimeout(() => {
          const el = app.querySelector(`[data-r="${rr}"][data-c="${cc}"]`);
          if (el) el.classList.add('cell--lit');
        }, i * 40);
      });
    });
  }

  if (res.finished) setTimeout(finishMaster, gained.length ? 600 : 250);
}

function finishMaster() {
  const s = M.summary(game);
  const prev = save.best || 0;
  const newBest = s.total > prev;
  const pct = stats.percentile(save.history, s.total);
  const today = todayKey();

  let streak = save.streak || 0;
  if (game.mode === 'daily') streak = stats.nextStreak(streak, save.lastDailyKey, today);

  const patch = { streak };
  if (game.mode === 'daily') patch.lastDailyKey = today;

  const prevAvg = stats.summarize(save.history);
  const improvedBy = prevAvg ? s.total - prevAvg.median : 0;

  const result = ach.evaluate(save.achievements, {
    gamesPlayed: (save.gamesPlayed || 0) + 1,
    score: s.total,
    fullRows: s.fullRows, fullCols: s.fullCols, fullDiags: s.fullDiags,
    rowPoints: s.rowPoints, colPoints: s.colPoints, diagPoints: s.diagPoints,
    dailyPlayed: game.mode === 'daily' ? 1 : 0,
    streak,
    usedUndo: game.undoUsed,
    newBest,
    percentile: pct,
    ascendingFull: s.ascendingFull, decadeFive: s.decadeFive, parityFive: s.parityFive,
    lottoWins: save.lottoWins || 0,
    lottoMissed: null, lottoWon: false,
    improvedBy,
    rulesActive: game.rules.length,
  });

  store.update({ ...patch, achievements: result.encoded });
  store.recordGame({ score: s.total, day: today, mode: game.mode });
  save = store.get();

  // В лидерборд уходит только счёт реально сыгранной партии. Раньше сюда шёл
  // save.best — поле из localStorage, которое игрок правит руками, и подменённое
  // значение попадало в таблицу. Рекорд отправляем лишь когда он действительно побит.
  if (game.mode === 'daily' && sdk.state.timeVerified) sdk.submitScore('daily', s.total);
  if (newBest) sdk.submitScore('best', s.total);

  lastResult = { kind: 'master', s, newBest, pct, fresh: result.fresh };
  if (newBest) sfx.win(); else sfx.good();

  store.flush();
  maybeFullscreenAd(() => go('result'));
}

// Полноэкранная реклама только между партиями, где геймплей объективно остановлен,
// и не на каждом результате.
function maybeFullscreenAd(done) {
  adCounter++;
  if (adCounter % 2 === 0 && sdk.hasAds()) {
    sdk.gameplayStop();
    sdk.showFullscreen(() => done());
  } else done();
}

// ---------------------------------------------------------------- барабан

let drum = null;

function startDrum() {
  drum = D.createGame({ seed: (Math.floor(Math.random() * 1e9) | 0), gamesPlayed: save.gamesPlayed || 0 });
  go('drum');
  sfx.roll();
}

function renderDrum() {
  const g = drum;
  const sc = D.score(g);
  const held = D.currentBarrel(g);

  // Пока бочонок не выбран — поле показывает готовые числа без подсказок:
  // подсказывать некуда, ставить нечего.
  let cells = '';
  const preview = new Map();
  if (held != null) {
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE; c++) {
        if (g.grid[r][c] !== EMPTY) continue;
        preview.set(r * SIZE + c, scoreDeltaFor(g, r, c, held));
      }
    }
  }
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const v = g.grid[r][c];
      if (v !== EMPTY) { cells += `<div class="cell" data-r="${r}" data-c="${c}">${v}</div>`; continue; }
      if (held == null) { cells += `<div class="cell cell--empty" data-r="${r}" data-c="${c}"></div>`; continue; }
      const d = preview.get(r * SIZE + c) ?? 0;
      const cls = d > 0 ? '' : (d < 0 ? ' cell__delta--bad' : ' cell__delta--zero');
      cells += `<button class="cell cell--empty" data-act="drumplace" data-r="${r}" data-c="${c}"
        aria-label="${r + 1}-${c + 1}"><span class="cell__delta${cls}">${d > 0 ? '+' : ''}${d}</span></button>`;
    }
  }

  const deltas = g.cands.map((v) => D.bestDelta(g, v));
  const allZero = deltas.every((d) => d === 0);

  const stage = held == null
    ? `<div class="cands">${g.cands.map((v, i) => {
         const d = deltas[i];
         return `<button class="cand" data-act="drumpick" data-i="${i}">
           <span class="barrel barrel--lg barrel--roll">${v}</span>
           <span class="cand__d${d > 0 ? ' cand__d--good' : ''}">${d > 0 ? '+' : ''}${d}</span>
         </button>`;
       }).join('')}</div>`
    : `<div class="barrel barrel--lg barrel--roll">${held}</div>`;

  // Когда все кандидаты дают ноль, «выберите один» звучит издевательски —
  // вместо этого объясняем, чем они на самом деле различаются.
  const hint = held == null
    ? (allZero ? t('drum_early') : `${t('drum_pick')}. ${t('drum_note')}`)
    : (isMobile() ? t('place_hint_mobile') : t('place_hint'));

  return `
  <div class="bar">
    <button class="iconbtn" data-act="menu" aria-label="${esc(t('back'))}">←</button>
    <div class="pill"><span class="pill__k">${esc(t('bag_left'))}</span>
      <span class="pill__v">${D.barrelsLeft(g)}</span></div>
    <div class="bar__spacer"></div>
    <div class="pill pill--opt"><span class="pill__k">${esc(t('drum_returned'))}</span>
      <span class="pill__v">${g.skipped}</span></div>
    <div class="pill"><span class="pill__k">${esc(t('score'))}</span>
      <span class="pill__v">${sc.total}</span></div>
    <button class="iconbtn" data-act="sound">${isMuted() ? '🔇' : '🔊'}</button>
  </div>
  <div class="play">
    ${stage}
    <div class="grid">${cells}</div>
  </div>
  <div class="hint">${esc(hint)}</div>
  <div class="bar">
    ${adBtn('reroll', t('reroll'), g.rerollUsed || held != null)}
  </div>`;
}

// Дельта для клетки при выбранном бочонке — тот же расчёт, что и везде.
function scoreDeltaFor(g, r, c, value) {
  const before = D.score(g).total;
  g.grid[r][c] = value;
  const after = D.score(g).total;
  g.grid[r][c] = EMPTY;
  return after - before;
}

function doDrumPlace(r, c) {
  const res = D.place(drum, r, c);
  if (!res) return;
  sfx.place();
  const gained = res.changed.filter((l) => l.delta > 0);
  render();
  if (gained.length) sfx.line();
  if (res.finished) setTimeout(finishDrum, gained.length ? 600 : 250);
}

function finishDrum() {
  const s = M.summary(drum);
  const prev = save.best || 0;
  const pct = stats.percentile(save.history, s.total);
  const prevAvg = stats.summarize(save.history);

  const result = ach.evaluate(save.achievements, {
    gamesPlayed: (save.gamesPlayed || 0) + 1,
    score: s.total,
    fullRows: s.fullRows, fullCols: s.fullCols, fullDiags: s.fullDiags,
    rowPoints: s.rowPoints, colPoints: s.colPoints, diagPoints: s.diagPoints,
    dailyPlayed: 0, streak: save.streak || 0,
    usedUndo: true, newBest: s.total > prev, percentile: pct,
    ascendingFull: s.ascendingFull, decadeFive: s.decadeFive, parityFive: s.parityFive,
    lottoWins: save.lottoWins || 0, lottoMissed: null, lottoWon: false,
    improvedBy: prevAvg ? s.total - prevAvg.median : 0,
    rulesActive: drum.rules.length,
  });

  store.update({ achievements: result.encoded });
  store.recordGame({ score: s.total, day: todayKey(), mode: 'drum' });
  save = store.get();

  // Отдельная таблица: очки барабана и «Карточки мастера» несопоставимы.
  sdk.submitScore('drum', s.total);

  lastResult = { kind: 'master', s, newBest: s.total > prev, pct, fresh: result.fresh, again: 'drum' };
  if (s.total > prev) sfx.win(); else sfx.good();
  store.flush();
  maybeFullscreenAd(() => go('result'));
}

// ---------------------------------------------------------------- лото

function startLotto() {
  lotto = L.createLotto({ seed: (Math.floor(Math.random() * 1e9) | 0) });
  go('lotto');
  scheduleLotto(1200);
}

function scheduleLotto(delay = 2600) {
  stopLottoTimer();
  lottoTimer = setTimeout(() => {
    const n = L.callNext(lotto);
    if (n != null) sfx.roll();
    if (lotto.finished) { finishLotto(); return; }
    render();
    scheduleLotto();
  }, delay);
}

function stopLottoTimer() {
  if (lottoTimer) { clearTimeout(lottoTimer); lottoTimer = null; }
}

function renderLotto() {
  const p = L.progress(lotto);
  const cur = L.current(lotto);

  let cells = '';
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 9; c++) {
      const n = lotto.playerCard[r][c];
      if (!n) { cells += `<div class="lcell lcell--blank"></div>`; continue; }
      const marked = lotto.marked.has(n);
      const hit = !marked && lotto.pending === n;
      cells += `<button class="lcell${marked ? ' lcell--marked' : ''}${hit ? ' lcell--hit' : ''}"
        ${hit ? 'data-act="mark" data-n="' + n + '"' : ''}>${n}</button>`;
    }
  }

  const rivals = p.rivals.map((v, i) => `
    <div class="rival${v > p.player ? ' rival--lead' : ''}">
      <span class="rival__n">${esc(t('lotto_rival'))} ${i + 1}</span>
      <span class="rival__v">${v}/${L.TO_CLOSE}</span></div>`).join('');

  return `
  <div class="bar">
    <button class="iconbtn" data-act="menu" aria-label="${esc(t('back'))}">←</button>
    <div class="pill"><span class="pill__k">${esc(t('lotto_called'))}</span>
      <span class="pill__v">${p.called}</span></div>
    <div class="bar__spacer"></div>
    <div class="pill"><span class="pill__k">${esc(t('lotto_missed'))}</span>
      <span class="pill__v">${p.missed}</span></div>
    <button class="iconbtn" data-act="sound">${isMuted() ? '🔇' : '🔊'}</button>
  </div>

  <div class="play">
    <div class="barrel barrel--lg barrel--roll">${cur ?? ''}</div>
    <div class="rivals">
      <div class="rival"><span class="rival__n">${esc(t('lotto_your_card'))}</span>
        <span class="rival__v">${p.player}/${L.TO_CLOSE}</span></div>
      ${rivals}
    </div>
    <div class="lcard">${cells}</div>
  </div>
  <div class="hint">${esc(t('lotto_mark'))}</div>
  <div class="bar">
    ${adBtn('recover', t('recover'), !L.canRecover(lotto))}
  </div>`;
}

function finishLotto() {
  stopLottoTimer();
  const p = L.progress(lotto);
  const won = lotto.result === 'player';
  const wins = (save.lottoWins || 0) + (won ? 1 : 0);

  const result = ach.evaluate(save.achievements, {
    gamesPlayed: save.gamesPlayed || 0,
    score: 0, fullRows: 0, fullCols: 0, fullDiags: 0,
    rowPoints: 0, colPoints: 0, diagPoints: 0,
    dailyPlayed: 0, streak: save.streak || 0,
    usedUndo: true, newBest: false, percentile: null,
    ascendingFull: 0, decadeFive: 0, parityFive: 0,
    lottoWins: wins, lottoMissed: p.missed, lottoWon: won,
    improvedBy: 0, rulesActive: 0,
  });

  store.update({ lottoWins: wins, achievements: result.encoded });
  save = store.get();

  lastResult = { kind: 'lotto', won, missed: p.missed, player: p.player, fresh: result.fresh };
  if (won) sfx.win(); else sfx.lose();

  store.flush();
  maybeFullscreenAd(() => go('result'));
}

// ---------------------------------------------------------------- результат

function renderResult() {
  const r = lastResult;
  const fresh = (r.fresh || []).map((a) =>
    `<div class="row"><span>${esc(achTitle(a.key))}</span><b>★</b></div>`).join('');

  if (r.kind === 'lotto') {
    return `<div class="scroll"><div class="sheet">
      <h2>${esc(r.won ? t('lotto_win') : t('lotto_lose'))}</h2>
      <div class="big">${r.player}/${L.TO_CLOSE}</div>
      <div class="rows">
        <div class="row"><span>${esc(t('lotto_missed'))}</span><b>${r.missed}</b></div>
        ${fresh}
      </div>
      <p class="note center">${esc(t('lotto_unlock'))}</p>
      <div class="actions">
        <button class="btn btn--main" data-act="free">${esc(t('play_master'))}</button>
        <button class="btn btn--ghost" data-act="lotto">${esc(t('play_again'))}</button>
        <button class="btn btn--ghost" data-act="menu">${esc(t('to_menu'))}</button>
      </div>
    </div></div>`;
  }

  const s = r.s;
  const line = (key, val) => `<div class="row"><span>${esc(t(key))}</span><b>${val}</b></div>`;
  return `<div class="scroll"><div class="sheet">
    <h2>${esc(t('result_title'))}</h2>
    ${r.newBest ? `<span class="badge">${esc(t('result_best_new'))}</span>` : ''}
    <div class="big">${s.total}</div>
    <div class="rows">
      ${s.rowPoints ? line('result_rows', s.rowPoints) : ''}
      ${s.colPoints ? line('result_cols', s.colPoints) : ''}
      ${s.diagPoints ? line('result_diags', s.diagPoints) : ''}
      <div class="row"><span>${esc(t('best'))}</span><b>${save.best}</b></div>
      ${r.pct !== null ? `<div class="row"><span>${esc(t('median_today'))}</span><b>${r.pct}%</b></div>` : ''}
      ${fresh}
    </div>
    <div class="actions">
      <button class="btn btn--main" data-act="${r.again === 'drum' ? 'drum' : 'free'}">${esc(t('play_again'))}</button>
      <button class="btn btn--ghost" data-act="stats">${esc(t('stats'))}</button>
      <button class="btn btn--ghost" data-act="menu">${esc(t('to_menu'))}</button>
    </div>
  </div></div>`;
}

// ---------------------------------------------------------------- коллекция и статистика

function renderAch() {
  const bits = ach.decode(save.achievements);
  const items = ach.ACHIEVEMENTS.map((a, i) => {
    const on = ach.has(bits, a.id);
    return `<div class="ach${on ? ' ach--on' : ''}" title="${esc(achTitle(a.key))}">
      <span class="ach__i">${on ? i + 1 : '·'}</span>${on ? esc(achTitle(a.key)) : esc(t('ach_locked'))}</div>`;
  }).join('');

  return `
  <div class="bar">
    <button class="iconbtn" data-act="menu" aria-label="${esc(t('back'))}">←</button>
    <div class="bar__spacer"></div>
  </div>
  <div class="scroll">
    <h3 class="center">${esc(t('ach_progress', { a: ach.countUnlocked(bits), b: ach.TOTAL }))}</h3>
    <div class="achs">${items}</div>
  </div>`;
}

function renderStats() {
  const sum = stats.summarize(save.history);
  if (!sum) {
    return `<div class="bar"><button class="iconbtn" data-act="menu">←</button></div>
      <div class="scroll"><p class="note center">${esc(t('no_stats'))}</p></div>`;
  }
  const dist = stats.distribution(save.history, 20);
  const max = Math.max(...dist.map((b) => b.count), 1);
  const bars = dist.map((b) => {
    const mine = sum.last >= b.lo && sum.last <= b.hi;
    return `<div class="hist__b${mine ? ' hist__b--me' : ''}" style="height:${Math.round((b.count / max) * 100)}%"></div>`;
  }).join('');
  const labels = dist.map((b) => `<span>${b.lo}</span>`).join('');

  const row = (k, v) => `<div class="stat-row"><span>${esc(t(k))}</span><b>${v}</b></div>`;
  return `
  <div class="bar"><button class="iconbtn" data-act="menu" aria-label="${esc(t('back'))}">←</button>
    <div class="bar__spacer"></div></div>
  <div class="scroll">
    <h3>${esc(t('distribution'))}</h3>
    <div class="hist">${bars}</div>
    <div class="hist__l">${labels}</div>
    ${row('games_played', sum.games)}
    ${row('your_best', sum.best)}
    ${row('median_today', sum.median)}
    ${row('streak', save.streak || 0)}
    ${sdk.state.authorized ? '' : `<p class="note">${esc(t('leaderboard_guest'))}</p>`}
  </div>`;
}

// ---------------------------------------------------------------- как играть

// Экран объясняет схемами, а не текстом: миниатюрное поле 5×5 с подсвеченной
// линией показывает правило нагляднее любого описания.
// Сетка строится кодом, поэтому в билд не добавляется ни одной картинки.

function miniGrid(cells, highlight) {
  const on = new Set(highlight.map(([r, c]) => r * SIZE + c));
  let out = '';
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const v = cells[r * SIZE + c];
      const cls = on.has(r * SIZE + c) ? ' mg__c--on' : (v ? ' mg__c--set' : '');
      out += `<i class="mg__c${cls}">${v || ''}</i>`;
    }
  }
  return `<div class="mg" aria-hidden="true">${out}</div>`;
}

const blank = () => Array(SIZE * SIZE).fill(0);

function ruleRow() {
  const g = blank();
  [4, 18, 29, 46, 72].forEach((v, i) => { g[2 * SIZE + i] = v; });
  return miniGrid(g, [[2, 0], [2, 1], [2, 2], [2, 3], [2, 4]]);
}
function ruleCol() {
  const g = blank();
  [31, 35, 33, 38, 30].forEach((v, i) => { g[i * SIZE + 2] = v; });
  return miniGrid(g, [[0, 2], [1, 2], [2, 2], [3, 2], [4, 2]]);
}
function ruleDiag() {
  const g = blank();
  [4, 18, 46, 72, 90].forEach((v, i) => { g[i * SIZE + i] = v; });
  return miniGrid(g, [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4]]);
}

function hintDemo() {
  // Клетка с подсказкой: показываем ровно то, что игрок увидит в партии.
  const g = blank();
  g[1 * SIZE + 1] = 18;
  g[1 * SIZE + 3] = 46;
  let out = '';
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const v = g[r * SIZE + c];
      if (v) { out += `<i class="mg__c mg__c--set">${v}</i>`; continue; }
      const good = r === 1 && c === 2;
      out += `<i class="mg__c"><b class="mg__d${good ? ' mg__d--good' : ''}">${good ? '+6' : '0'}</b></i>`;
    }
  }
  return `<div class="mg" aria-hidden="true">${out}</div>`;
}

function step(diagram, text, points) {
  return `<div class="how__b">
    <div class="how__dia">${diagram}${points ? `<span class="pts">${points}</span>` : ''}</div>
    <p class="how__t">${esc(text)}</p>
  </div>`;
}

function renderHow() {
  const lottoCard = `<div class="mgl" aria-hidden="true">${
    [[0, 14, 0, 36, 44, 0, 0, 77, 83],
     [8, 17, 0, 0, 47, 52, 63, 0, 0],
     [0, 0, 28, 0, 48, 0, 68, 78, 86]]
      .flatMap((row) => row.map((n) =>
        n === 63 ? `<i class="mg__c mg__c--hit">63</i>`
                 : `<i class="mg__c${n ? ' mg__c--set' : ' mg__c--blank'}">${n || ''}</i>`)).join('')
  }</div>`;

  const drum = `<div class="how__cands" aria-hidden="true">
      <span class="barrel barrel--sm">33</span>
      <span class="barrel barrel--sm barrel--take">7</span>
      <span class="barrel barrel--sm">54</span>
    </div>`;

  const master = `<div class="how__pair" aria-hidden="true">
      <span class="barrel barrel--sm">29</span><span class="how__arr">→</span>${
        miniGrid((() => { const g = blank(); g[2 * SIZE + 0] = 4; g[2 * SIZE + 1] = 18; return g; })(),
                 [[2, 2]])}
    </div>`;

  return `
  <div class="bar">
    <button class="iconbtn" data-act="menu" aria-label="${esc(t('back'))}">←</button>
    <div class="bar__spacer"></div>
  </div>
  <div class="scroll how">
    <h3>${esc(t('play_lotto'))}</h3>
    ${step(lottoCard, t('how_lotto'))}

    <h3>${esc(t('play_master'))}</h3>
    ${step(master, t('how_master'))}
    ${step(hintDemo(), t('how_hint'))}

    <h3>${esc(t('play_drum'))}</h3>
    ${step(drum, t('how_drum'))}

    <h3>${esc(t('how_rules'))}</h3>
    ${step(ruleRow(), t('how_rows'), '+25')}
    ${step(ruleCol(), t('how_cols'), '+30')}
    ${step(ruleDiag(), t('how_diags'), '+18')}
    <p class="note center">${esc(t('how_more'))}</p>
    <p class="note center">${esc(t('how_ladder'))}</p>
    <div class="actions"><button class="btn btn--main" data-act="menu">${esc(t('back'))}</button></div>
  </div>`;
}

// ---------------------------------------------------------------- ввод

app.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-act]');
  if (!btn || btn.disabled) return;
  const act = btn.dataset.act;

  if (act === 'menu')  return go('menu');
  if (act === 'lotto') return startLotto();
  if (act === 'daily') return startMaster('daily');
  if (act === 'free')  return startMaster('free');
  if (act === 'drum')  return startDrum();
  if (act === 'ach')   return go('achievements');
  if (act === 'stats') return go('stats');
  if (act === 'how')   return go('how');

  if (act === 'sound') {
    setMuted(!isMuted());
    store.update({ muted: isMuted() });
    save = store.get();
    return render();
  }

  if (act === 'place') return doPlace(+btn.dataset.r, +btn.dataset.c);
  if (act === 'drumpick') { D.pick(drum, +btn.dataset.i); sfx.roll(); return render(); }
  if (act === 'drumplace') return doDrumPlace(+btn.dataset.r, +btn.dataset.c);

  if (act === 'mark') {
    if (L.markPlayer(lotto, +btn.dataset.n)) { sfx.tick(); if (lotto.finished) finishLotto(); else render(); }
    return;
  }

  // Rewarded — только по явному нажатию игрока, награда по onRewarded.
  if (act === 'undo') {
    if (!sdk.hasAds()) { if (M.undo(game)) render(); return; }
    sdk.gameplayStop();
    return sdk.showRewarded(
      () => { M.undo(game); },
      () => { sdk.gameplayStart(); render(); }
    );
  }
  if (act === 'reroll') {
    stopLottoTimer();
    if (!sdk.hasAds()) { D.reroll(drum); sfx.roll(); return render(); }
    sdk.gameplayStop();
    return sdk.showRewarded(
      () => { D.reroll(drum); },
      () => { sdk.gameplayStart(); sfx.roll(); render(); }
    );
  }
  if (act === 'recover') {
    // Пауза в розыгрыше на время ролика — иначе ведущий продолжит доставать бочонки.
    stopLottoTimer();
    const resume = () => { sdk.gameplayStart(); render(); if (!lotto.finished) scheduleLotto(); };
    if (!sdk.hasAds()) { L.recoverMissed(lotto); sfx.good(); return resume(); }
    sdk.gameplayStop();
    return sdk.showRewarded(
      () => { L.recoverMissed(lotto); sfx.good(); },
      () => { if (lotto.finished) finishLotto(); else resume(); }
    );
  }
  if (act === 'peek') {
    if (!sdk.hasAds()) { peeked = M.peek(game); render(); return; }
    sdk.gameplayStop();
    return sdk.showRewarded(
      () => { peeked = M.peek(game); },
      () => { sdk.gameplayStart(); render(); }
    );
  }
});

boot().catch((e) => {
  console.error(e);
  // Даже аварийный экран показываем на языке игрока: непереведённая строка
  // на любом из заявленных языков — нарушение требования 2.14.
  try { setLang(sdk.state.lang); } catch {}
  app.innerHTML = `<div class="menu"><h1>${esc(t('title'))}</h1>
    <p class="menu__sub">${esc(t('load_failed'))}</p></div>`;
  sdk.loadingReady();
});
