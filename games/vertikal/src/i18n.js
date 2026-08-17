// Только русский. Сатира держится на речевых регистрах, которым нет
// английского эквивалента, а половинчатая локализация — риск отказа по §2.10.
// Английская версия появится, если релиз выживет.
//
// Структура словаря сохранена под будущий второй язык.

const RU = {
  title: 'Вертикаль',
  tagline: 'Расейская Федерация',

  play: 'Начать службу',
  how: 'Как это работает',
  back: 'Назад',
  resign: 'Уйти по собственному',
  again: 'Ещё раз, но иначе',

  turn: 'Ход',
  points: 'Дела',
  rubles: 'Бубли',
  papers: 'Листы',
  rank: 'Ранг',
  endTurn: 'Закончить день',

  work: 'Работа',
  ad_note: 'смотреть рекламу',
  ad_wait: 'Подработка будет через',
  ad_take: 'Подработать',

  people: 'Люди',
  greet: 'Зайти поздороваться',
  gift: 'Подарок',
  giftTaste: 'Подарок по вкусу',
  party: 'Позвать в баню',
  cover: 'Привести бумаги в порядок',
  scheme: 'Провести схему',
  schemeCareful: 'Осторожно',
  schemeGreedy: 'Жадно',

  band_enemy: 'Враг',
  band_grudge: 'Обида',
  band_neutral: 'Ровно',
  band_friend: 'Свой',
  band_inner: 'Ближний круг',

  gauge: 'Ощущение',
  gauge_0: 'Тихо',
  gauge_1: 'Спрашивали',
  gauge_2: 'Интересуются',
  gauge_3: 'Смотрят',
  gauge_4: 'Ждут у подъезда',

  noise_silent: 'День прошёл незаметно',
  noise_quiet: 'Тихий день',
  noise_noticeable: 'Шумновато',
  noise_loud: 'Шумный день',
  noise_blaring: 'Про вас говорили',

  promoted: 'Назначение',
  needLoyalty: 'Нужна поддержка',
  needTurns: 'Нужно выслужить',

  peek: 'Позвонить в Пригляд',
  peekResult: 'Про вас говорят на',
  peekUsed: 'Больше он не поднимет трубку',

  prologueTitle: 'Первое дело',
  prologueText: 'Вам принесли бумаги по тендеру на урны для сквера. Урны позолоченные. По документам каждая стоит как автомобиль. Сумма не сходится на четыреста тысяч бублей.',
  prologueReport: 'Доложить начальнику',
  prologueSilent: 'Промолчать',
  prologueSign: 'Подшить как есть',

  endTitle_caught: 'За вами пришли',
  endTitle_quiet: 'Вы ушли сами',
  endTitle_quiet_list: 'Вы ушли, но не один',

  endScore: 'Тихий уход',
  endDefendants: 'Вместе с вами проходят',
  endNobody: 'Никто не сел. Никто и не вспомнит.',
  endRoza: 'Роза Марковна не знала, во что была вписана. Ей дали два года условно, и она не понимает за что.',

  spared: 'Кого вы не подставили',
  disclaimer: 'Сатира. Все лица, ведомства и события вымышлены. Взятки, подлог и хищение в этой игре ведут туда же, куда ведут в жизни.',
};

export const DICTS = { ru: RU };
export const LANGS = Object.keys(DICTS);
let current = 'ru';

export function setLang(lang) {
  current = DICTS[lang] ? lang : 'ru';
  if (typeof document !== 'undefined') document.documentElement.setAttribute('lang', current);
  return current;
}

export function getLang() { return current; }

export function t(key, vars) {
  const s = DICTS[current]?.[key] ?? key;
  if (!vars) return s;
  return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
}
