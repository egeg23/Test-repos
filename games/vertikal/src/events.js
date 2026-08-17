// События. Форма выбора почти всегда одна: заплатить и остаться либо
// спуститься. Но спуск — ВСЕГДА явный выбор игрока, никогда не бросок
// и никогда не следствие пустого кошелька: у каждого события обязан быть
// вариант, проходимый при нуле бублей. Это проверяется тестом.

export const EVENTS = [
  {
    id: 'urns',
    title: 'Позолоченные урны',
    text: 'Закупили урны для сквера. По документам — как автомобиль каждая. Приехала комиссия смотреть на урны.',
    minRank: 5,
    options: [
      { id: 'pay',   label: 'Доплатить комиссии за понимание', cost: 12000, suspicion: 4, papers: 1 },
      { id: 'blame', label: 'Свалить на подрядчика',           cost: 0, suspicion: 2, papers: 1, blame: 'garik' },
      { id: 'own',   label: 'Признать ошибку и вернуть',       cost: 0, suspicion: 0, papers: 0, demote: 1 },
    ],
  },
  {
    id: 'sauna',
    title: 'Приглядчик обижен',
    text: 'В субботу была баня. Прошкина не позвали. Он не сказал ни слова, и это хуже всего.',
    minRank: 5,
    requires: { person: 'proshkin' },
    options: [
      { id: 'invite', label: 'Позвать в следующую субботу', cost: 6000, suspicion: 0, loyalty: { proshkin: 10 } },
      { id: 'gift',   label: 'Путёвка детям в лагерь',      cost: 15000, suspicion: 1, loyalty: { proshkin: 18 } },
      { id: 'ignore', label: 'Сделать вид, что не заметил', cost: 0, suspicion: 0, loyalty: { proshkin: -6 } },
    ],
  },
  {
    id: 'fountain',
    title: 'Фонтан к приезду',
    text: 'К приезду комиссии решено починить фонтан. Фонтан не работает с девяностых. Комиссия приедет в четверг.',
    minRank: 5,
    options: [
      { id: 'real',  label: 'Действительно починить',        cost: 40000, suspicion: 0, papers: 0 },
      { id: 'paint', label: 'Покрасить и не включать',       cost: 5000, suspicion: 6, papers: 2 },
      { id: 'sign',  label: 'Повесить табличку «на реконструкции»', cost: 0, suspicion: 2, papers: 1 },
    ],
  },
  {
    id: 'nephew',
    title: 'Машина не по средствам',
    text: 'Племянник Розы Марковны купил машину. Соседи считают, что на зарплату кладовщика такую не берут. Соседи считают вслух.',
    minRank: 6,
    options: [
      { id: 'hush',  label: 'Попросить Гарика поговорить с соседями', cost: 8000, suspicion: 3, papers: 1 },
      { id: 'papers',label: 'Оформить машину задним числом на фирму', cost: 20000, suspicion: 8, papers: 2 },
      { id: 'sell',  label: 'Пусть продаёт',                          cost: 0, suspicion: 0, loyalty: { roza: -10 } },
    ],
  },
  {
    id: 'journalist',
    title: 'Энтузиаст',
    text: 'Местный журналист написал про урны. Прочитали одиннадцать человек. Один из них работает в Пригляде.',
    minRank: 6,
    options: [
      { id: 'buy',    label: 'Предложить ему место в пресс-службе', cost: 25000, suspicion: 3, papers: 1 },
      { id: 'press',  label: 'Попросить Хвата надавить',            cost: 0, suspicion: 5, papers: 2, loyalty: { hvat: -10 } },
      { id: 'ignore', label: 'Ничего не делать',                    cost: 0, suspicion: 7, papers: 1 },
    ],
  },
];

export function available(rank, turn, seen) {
  return EVENTS.filter((e) => e.minRank <= rank && !seen.includes(e.id));
}

export function pick(rank, turn, seen, rnd) {
  const pool = available(rank, turn, seen);
  if (!pool.length) return null;
  return pool[Math.floor(rnd() * pool.length)];
}

// Вариант, доступный при нуле бублей. Гарантия того, что игрок никогда
// не окажется заперт без выхода.
export function freeOption(event) {
  return event.options.find((o) => (o.cost || 0) === 0) || null;
}
