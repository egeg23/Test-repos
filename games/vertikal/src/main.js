// Точка входа.

import * as sdk from './sdk.js';
import * as store from './storage.js';
import { t, setLang } from './i18n.js';
import * as B from './balance.js';
import * as G from './state.js';
import * as Loy from './loyalty.js';
import * as Susp from './suspicion.js';
import * as Clk from './clicker.js';
import * as Art from './art.js';
import { sfx, setMuted, isMuted, suspend as audioSuspend, resume as audioResume } from './audio.js';

const app = document.getElementById('app');
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

let save = null;
let view = 'menu';
let g = null;
let peeked = null;
let flash = '';

const PLAY_VIEWS = ['play', 'event', 'end'];
const isPlay = (v) => PLAY_VIEWS.includes(v);

const FACE = {
  alla: ['dress', Art.PALETTE.brass, 'АТ'],
  proshkin: ['uniform', Art.PALETTE.slate, 'ВП'],
  garik: ['plain', Art.PALETTE.red, 'ГП'],
  hvat: ['suit', Art.PALETTE.khaki, 'РХ'],
  roza: ['dress', Art.PALETTE.khaki, 'РМ'],
};

// ---------------------------------------------------------------- запуск

async function boot() {
  await sdk.init();
  save = store.loadLocal();
  setLang('ru');
  setMuted(!!save.muted);

  go('menu');
  // Требование 1.19: сигнал ровно в кадре, где меню появилось на экране.
  requestAnimationFrame(() => sdk.loadingReady());

  sdk.initDeferred()
    .then(() => store.syncCloud())
    .then((changed) => { save = store.get(); if (changed && view === 'menu') render(); })
    .catch(() => {});

  window.addEventListener('beforeunload', () => store.flush());
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { store.flush(); audioSuspend(); } else audioResume();
  });
  window.addEventListener('blur', audioSuspend);
  window.addEventListener('focus', audioResume);
  app.addEventListener('contextmenu', (e) => e.preventDefault());
}

function go(next) {
  if (isPlay(view)) sdk.gameplayStop();
  view = next;
  render();
  if (isPlay(view)) { sdk.gameplayStart(); sdk.hideBanner(); } else sdk.showBanner();
}

function render() {
  app.innerHTML = ({
    menu: renderMenu, prologue: renderPrologue, play: renderPlay,
    event: renderEvent, end: renderEnd, how: renderHow,
  }[view])();
}

// ---------------------------------------------------------------- меню

function renderMenu() {
  const spared = (save.spared || []).length;
  return `
  <div class="bar"><div class="bar__spacer"></div>
    <button class="iconbtn" data-act="sound">${isMuted() ? '🔇' : '🔊'}</button></div>
  <div class="menu">
    ${Art.emblem(72)}
    <h1>${esc(t('title'))}</h1>
    <p class="menu__sub">${esc(t('tagline'))}</p>
    <button class="btn btn--main" data-act="start">${esc(t('play'))}</button>
    <button class="btn" data-act="how">${esc(t('how'))}</button>
    ${save.runs ? `<p class="note">Служб пройдено: ${save.runs}${spared ? ` · не подставлено: ${spared}` : ''}</p>` : ''}
    <p class="disclaimer">${esc(t('disclaimer'))}</p>
  </div>`;
}

function renderHow() {
  return `
  <div class="bar"><button class="iconbtn" data-act="menu">←</button><div class="bar__spacer"></div></div>
  <div class="scroll">
    <h3>Деньги видно. Себя — нет</h3>
    <p class="note">Сколько у вас бублей, вы знаете точно. Насколько вами интересуются — никогда.
    Есть только ощущение: пять делений, и они отстают от правды на несколько дней.</p>
    <h3>Люди — это зрение</h3>
    <p class="note">Свой человек предупредит о проверке. Обиженный промолчит.
    Лояльность не даёт скидок — она даёт возможность увидеть то, чего вы не видите.</p>
    <h3>Работа честная и работа настоящая</h3>
    <p class="note">За смену вам платят оклад. За одну схему — в сотни раз больше.
    В этом вся арифметика игры.</p>
    <h3>Считают не деньги</h3>
    <p class="note">В конце вам покажут не сколько вы заработали, а кто сел вместе с вами.</p>
    <div class="actions"><button class="btn btn--main" data-act="menu">${esc(t('back'))}</button></div>
  </div>`;
}

// ---------------------------------------------------------------- пролог

function renderPrologue() {
  return `<div class="scroll"><div class="sheet">
    <h2>${esc(t('prologueTitle'))}</h2>
    ${Art.location(0)}
    <p>${esc(t('prologueText'))}</p>
    <div class="actions">
      <button class="btn" data-act="pro" data-v="report">${esc(t('prologueReport'))}</button>
      <button class="btn" data-act="pro" data-v="silent">${esc(t('prologueSilent'))}</button>
      <button class="btn btn--main" data-act="pro" data-v="sign">${esc(t('prologueSign'))}</button>
    </div>
  </div></div>`;
}

// ---------------------------------------------------------------- партия

function renderPlay() {
  const r = G.rank(g);
  const req = G.nextRequirement(g);
  const gauge = Susp.gauge(g.susp);
  const now = Date.now();
  const adReady = Clk.canWatchAd(g.clicker, now);
  const wait = Math.ceil(Clk.adCooldownLeft(g.clicker, now) / 1000);

  const cells = [0, 1, 2, 3, 4]
    .map((i) => `<span class="gauge__c${i <= gauge ? ' on' : ''}"></span>`).join('');

  const people = Loy.PEOPLE.map((p) => {
    const st = g.people[p.id];
    const [kind, color, ini] = FACE[p.id];
    const bnd = Loy.band(st.value);
    return `<div class="person person--${bnd}">${Art.portrait(kind, color, ini, 48, bnd)}
      <div><div class="person__n">${esc(p.name)}</div>
      <div class="person__b">${esc(t('band_' + Loy.band(st.value)))}${st.defendant ? ' · фигурант' : ''}</div></div></div>`;
  }).join('');

  const acts = [
    ['greet', t('greet'), `1 дело`],
    ['gift', t('giftTaste'), `1 дело · ${B.COSTS.giftTaste} б.`],
    ['cover', t('cover'), `1 дело · ${B.COSTS.coverTracks} б.`],
    ['careful', `${t('scheme')}: ${t('schemeCareful')}`, `2 дела · +${B.SCHEMES[0].income} б.`],
    ['greedy', `${t('scheme')}: ${t('schemeGreedy')}`, `2 дела · +${B.SCHEMES[1].income} б.`],
  ].map(([a, label, note]) =>
    `<button class="act" data-act="do" data-a="${a}">${esc(label)}<b>${esc(note)}</b></button>`).join('');

  return `
  <div class="bar bar--top">
    <div class="pill"><span class="pill__k">${esc(t('rank'))}</span><span class="pill__v">${r.id}</span></div>
    <div class="pill"><span class="pill__k">${esc(t('rubles'))}</span><span class="pill__v">${g.rubles}</span></div>
    <div class="pill"><span class="pill__k">${esc(t('points'))}</span><span class="pill__v">${g.points}</span></div>
    <div class="pill"><span class="pill__k">${esc(t('papers'))}</span><span class="pill__v">${g.susp.papers}</span></div>
    <div class="bar__spacer"></div>
    <button class="iconbtn" data-act="sound">${isMuted() ? '🔇' : '🔊'}</button>
  </div>

  <div class="stage">${Art.location(g.rankIndex)}
    <div class="plate"><span>${esc(r.name)}</span><span class="plate__l"></span>
      <span>${esc(t('rank'))} ${r.id}</span></div></div>

  <div class="gauge">${cells}<span class="gauge__t">${esc(t('gauge_' + gauge))}</span></div>

  <div class="work">
    <button class="work__click" data-act="click">${esc(r.click)} <b>+${B.CLICK_REWARD}</b></button>
    <button class="btn" style="width:auto;min-width:150px" data-act="ad" ${adReady ? '' : 'disabled'}>
      ${adReady ? esc(t('ad_take')) : `${esc(t('ad_wait'))} ${wait} с`}
      ${adReady && sdk.hasAds() ? `<span class="btn__note">▶ ${esc(t('ad_note'))}</span>` : ''}
    </button>
  </div>

  <div class="scroll">
    <div class="hint">${esc(flash || r.name)}</div>
    <div class="acts">${acts}</div>
    <div class="people">${people}</div>
    ${req ? `<p class="note">${esc(t('needLoyalty'))}: ${req.loyaltyHave}/${req.loyaltyNeed} ·
      ${esc(t('needTurns'))}: ${req.turnsHave}/${req.turnsNeed} дней</p>`
      : '<p class="note">Выше в этой службе не поднимают</p>'}
    ${peeked !== null ? `<p class="note note--red">${esc(t('peekResult'))} ${peeked} из 100</p>` : ''}
    <div class="log">${g.log.slice(0, 6).map((l) => `<div>${esc(l.text)}</div>`).join('')}</div>
  </div>

  <div class="bar bar--foot">
    <button class="btn btn--main" data-act="end">${esc(t('endTurn'))} · ${g.turn}</button>
    <button class="btn" data-act="peek" ${peeked !== null ? 'disabled' : ''} title="${esc(t('peek'))}">☎
      ${sdk.hasAds() ? `<span class="btn__note">▶</span>` : ''}</button>
    <button class="btn btn--red" data-act="resign" title="${esc(t('resign'))}">✕</button>
  </div>`;
}

function renderEvent() {
  const e = g.pending;
  const opts = e.options.map((o) => {
    const poor = (o.cost || 0) > g.rubles;
    return `<button class="btn" data-act="opt" data-o="${o.id}" ${poor ? 'disabled' : ''}>
      ${esc(o.label)}<span class="btn__note">${o.cost ? `${o.cost} бублей` : 'без затрат'}${o.demote ? ' · понижение' : ''}</span></button>`;
  }).join('');
  return `<div class="scroll"><div class="sheet">
    <h2>${esc(e.title)}</h2>
    ${Art.location(g.rankIndex)}
    <p>${esc(e.text)}</p>
    <div class="actions">${opts}</div>
  </div></div>`;
}

// ---------------------------------------------------------------- финал

function renderEnd() {
  const s = G.score(g);
  const caught = g.ending === 'caught';
  const roza = s.defendants.some((d) => d.id === 'roza');
  const list = s.defendants.length
    ? `<div class="rows">${s.defendants.map((d) =>
        `<div class="row"><span>${esc(d.name)}</span><b>${d.weight === 2 ? '×2' : '—'}</b></div>`).join('')}</div>`
    : `<p class="note center">${esc(t('endNobody'))}</p>`;

  const title = caught ? t('endTitle_caught')
    : (s.defendants.length ? t('endTitle_quiet_list') : t('endTitle_quiet'));

  return `<div class="scroll"><div class="sheet">
    ${Art.stamp(caught ? 'ДЕЛО ЗАВЕДЕНО' : 'ДЕЛО ЗАКРЫТО', 116)}
    <h2 class="center">${esc(title)}</h2>
    <div class="big">${s.points}</div>
    <p class="note center">${esc(t('endScore'))}</p>
    <h3>${esc(t('endDefendants'))}</h3>
    ${list}
    ${roza ? `<p class="note note--red">${esc(t('endRoza'))}</p>` : ''}
    <div class="rows">
      <div class="row"><span>${esc(t('rank'))}</span><b>${s.rank.id} · ${esc(s.rank.name)}</b></div>
      <div class="row"><span>${esc(t('papers'))}</span><b>${s.papers}</b></div>
      <div class="row"><span>Дней на службе</span><b>${s.turns}</b></div>
    </div>
    <div class="actions">
      <button class="btn btn--main" data-act="start">${esc(t('again'))}</button>
      <button class="btn" data-act="menu">${esc(t('back'))}</button>
    </div>
  </div></div>`;
}

// ---------------------------------------------------------------- ввод

function startRun() {
  g = G.create((Math.floor(Math.random() * 1e9) | 0));
  peeked = null; flash = '';
  go('prologue');
}

function finish() {
  const s = G.score(g);
  const spared = Loy.PEOPLE.filter((p) => !g.people[p.id].defendant).map((p) => p.name);
  store.update({ spared });
  store.recordRun({ score: s.points, rank: s.rank.id, ending: g.ending });
  save = store.get();
  sdk.submitScore('quiet', Math.max(0, s.points));
  store.flush();
  if (g.ending === 'caught') sfx.lose(); else sfx.win();
  go('end');
}

function afterTurn(res) {
  if (!res) return;
  if (res.caught) { finish(); return; }
  flash = t('noise_' + Susp.noiseLabel(res.noise));
  if (res.promoted) { flash = `${t('promoted')}: ${res.promoted.name}`; sfx.good(); }
  if (g.pending) { go('event'); return; }
  render();
}

app.addEventListener('click', (e) => {
  const b = e.target.closest('[data-act]');
  if (!b || b.disabled) return;
  const act = b.dataset.act;

  if (act === 'menu')  return go('menu');
  if (act === 'how')   return go('how');
  if (act === 'start') return startRun();
  if (act === 'sound') { setMuted(!isMuted()); store.update({ muted: isMuted() }); save = store.get(); return render(); }

  if (act === 'pro') { g.prologue = b.dataset.v; go('play'); return; }

  if (act === 'click') { G.click(g); sfx.tick(); return render(); }

  if (act === 'ad') {
    const grant = () => { if (G.watchAd(g, Date.now())) sfx.good(); };
    if (!sdk.hasAds()) { grant(); return render(); }
    sdk.gameplayStop();
    return sdk.showRewarded(grant, () => { sdk.gameplayStart(); render(); });
  }

  if (act === 'peek') {
    const grant = () => { peeked = Math.round(g.susp.value); };
    if (!sdk.hasAds()) { grant(); return render(); }
    sdk.gameplayStop();
    return sdk.showRewarded(grant, () => { sdk.gameplayStart(); render(); });
  }

  if (act === 'do') {
    const a = b.dataset.a;
    if (a === 'greet') G.greet(g, 'alla');
    else if (a === 'gift') G.gift(g, 'proshkin', true);
    else if (a === 'cover') G.coverTracks(g);
    else if (a === 'careful' || a === 'greedy') G.runScheme(g, a);
    sfx.place();
    return render();
  }

  if (act === 'end')    return afterTurn(G.endTurn(g));
  if (act === 'opt')    { G.resolveEvent(g, b.dataset.o); sfx.place(); return go('play'); }
  if (act === 'resign') { G.resign(g); return finish(); }
});

boot().catch((err) => {
  console.error(err);
  app.innerHTML = `<div class="menu"><h1>${esc(t('title'))}</h1>
    <p class="menu__sub">Не удалось загрузить. Обновите страницу.</p></div>`;
  sdk.loadingReady();
});
