// Единственный источник правды по числам. Любая величина, влияющая на баланс,
// живёт здесь — иначе код разъедется с проектным документом, как это уже
// случилось на этапе четырёх противоречащих таблиц.

export const SUSPICION_MAX = 100;

// Распад подозрения в конце хода: S -= DECAY_FLAT + DECAY_RATE * S.
// Отсюда равновесие: S* = (приток - DECAY_FLAT) / DECAY_RATE.
export const DECAY_FLAT = 1;
export const DECAY_RATE = 0.03;

// Очки хода: сколько действий помещается в один ход.
export const ACTION_POINTS = 3;

// Кликер. Диегетический: это та работа, которую игрок всё ещё обязан делать.
export const CLICK_REWARD = 2;
export const AD_REWARD = 1000;
export const AD_COOLDOWN_MS = 60_000;

// Ступени. rank — что открывается, income — оклад за ход,
// need — что требуется для перехода на следующую.
export const RANKS = [
  { id: 5,  name: 'Помощник юриста',        income: 300,   click: 'Подшить дело' },
  { id: 6,  name: 'Специалист канцелярии',  income: 700,   click: 'Завизировать' },
  { id: 7,  name: 'Главный специалист',     income: 1500,  click: 'Согласовать' },
  { id: 8,  name: 'Помощник префекта',      income: 2500,  click: 'Подписать' },
  { id: 9,  name: 'Заместитель префекта',   income: 4000,  click: 'Утвердить' },
];

// Требования к повышению. Бубли НЕ входят: ранг не покупается деньгами,
// иначе бесконечный кликер превратил бы игру в тест на выносливость пальца.
// Пороги считаются от суммы лояльности четырёх небытовых связей (максимум 400).
// Стартовая сумма — 170, поэтому первый порог обязан быть выше неё, иначе
// повышение выдаётся мгновенно на первом же ходу.
export const PROMOTION = {
  6: { loyaltySum: 200, turns: 4 },
  7: { loyaltySum: 245, turns: 10 },
  8: { loyaltySum: 290, turns: 18 },
  9: { loyaltySum: 335, turns: 28 },
};

// Схемы — источник денег и подозрения. Размен всей игры: скорость
// покупается риском, а не деньгами.
export const SCHEMES = [
  { id: 'careful', label: 'Осторожно', income: 80000,  suspicion: 2,  papers: 1, points: 2 },
  { id: 'greedy',  label: 'Жадно',     income: 400000, suspicion: 11, papers: 3, points: 2 },
];

export const ACTION_COSTS = { greet: 1, gift: 1, party: 1, cover: 1, scheme: 2 };

export const PROMOTION_SUSPICION = 5;

// Стоки бублей. Все ограничены ходами, а не деньгами — поэтому даже игрок
// с миллионом продвигается с той же скоростью.
export const COSTS = {
  giftPlain: 800,
  giftTaste: 1500,
  coverTracks: 3000,
  event: 5000,
};

export const COVER_TRACKS_RELIEF = 10;
export const COVER_TRACKS_PER_TURN = 2;

// Потолок роста лояльности: не более +LOYALTY_CAP за LOYALTY_WINDOW ходов
// на одну связь. Единственный шлюз, и он временной, а не денежный.
export const LOYALTY_CAP = 20;
export const LOYALTY_WINDOW = 5;

export const LOYALTY_BANDS = [
  { from: 0,  to: 14,  key: 'enemy' },
  { from: 15, to: 34,  key: 'grudge' },
  { from: 35, to: 54,  key: 'neutral' },
  { from: 55, to: 74,  key: 'friend' },
  { from: 75, to: 100, key: 'inner' },
];

// Метка шума: качественная оценка цены только что сделанного хода.
// Считается из того же числа, которое применяется к подозрению.
export const NOISE_LABELS = [
  { max: 0,   key: 'silent' },
  { max: 4,   key: 'quiet' },
  { max: 9,   key: 'noticeable' },
  { max: 19,  key: 'loud' },
  { max: 1e9, key: 'blaring' },
];

// Косвенная шкала: показывает не текущее подозрение, а то, что было
// GAUGE_DELAY ходов назад, забакеченное с гистерезисом. Задержка нужна,
// чтобы игрок не мог вывести точное S дифференцированием шкалы по ходам.
export const GAUGE_DELAY = 3;
export const GAUGE_BUCKETS = [24, 44, 64, 84, 100];
export const GAUGE_HYSTERESIS = 5;

// Итоговый счёт: высота минус цена. Стратегии «украсть побольше»
// не существует арифметически.
export const SCORE_PER_RANK = 10;
export const SCORE_PER_DEFENDANT = 25;
