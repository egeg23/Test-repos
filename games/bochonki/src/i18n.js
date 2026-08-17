// Локализация RU / EN / TR.
//
// Платформа требует полного перевода заявленных языков: частично переведённая
// игра — типовая причина отказа. Поэтому ключи одни и те же во всех словарях,
// а проверка полноты вынесена в тесты.

const RU = {
  title: 'Бочонки',
  tagline: 'Лото и карточка мастера',
  play_lotto: 'Классическое лото',
  play_master: 'Карточка мастера',
  play_drum: 'Барабан',
  drum_sub: 'Выбор из трёх',
  drum_pick: 'Барабан выкатил три бочонка — возьмите один',
  drum_note: 'Два других вернутся в мешок',
  drum_early: 'Очков пока не даст ни один. Малые числа удобны слева в строке, большие — справа',
  drum_returned: 'Возвращено',
  play_daily: 'Партия дня',
  play_free: 'Свободная партия',
  how_to: 'Как играть',
  achievements: 'Коллекция',
  stats: 'Статистика',
  back: 'Назад',
  close: 'Закрыть',
  sound_on: 'Звук включён',
  sound_off: 'Звук выключен',

  bag_left: 'В мешке',
  current_barrel: 'Бочонок',
  score: 'Очки',
  best: 'Рекорд',
  place_hint: 'Выберите клетку',
  first_move: 'Первый бочонок ставьте куда угодно — очки пойдут со второго',
  place_hint_mobile: 'Коснитесь клетки',

  rule_rows: 'Строки: числа по возрастанию слева направо',
  rule_cols: 'Столбцы: числа из одного столбца карточки лото',
  rule_diags: 'Диагонали: числа одной чётности',
  rule_new: 'Новое правило',

  result_title: 'Партия окончена',
  result_score: 'Ваш счёт',
  result_best_new: 'Новый рекорд!',
  result_rows: 'За строки',
  result_cols: 'За столбцы',
  result_diags: 'За диагонали',
  play_again: 'Ещё партия',
  to_menu: 'В меню',

  daily_done: 'Партия дня сыграна',
  daily_next: 'Новый мешок через',
  streak: 'Серия дней',
  median_today: 'Медиана ваших партий',
  your_best: 'Ваш рекорд',
  distribution: 'Распределение результатов',
  games_played: 'Партий сыграно',
  no_stats: 'Сыграйте несколько партий — здесь появится ваша статистика',
  leaderboard: 'Таблица лидеров',
  leaderboard_guest: 'Войдите в аккаунт Яндекса, чтобы попасть в таблицу лидеров. Пока показываем вашу личную статистику.',

  undo: 'Отменить ход',
  peek: 'Подсмотреть три бочонка',
  ad_reward_undo: 'Посмотреть рекламу и вернуть ход',
  ad_reward_peek: 'Посмотреть рекламу и увидеть следующие бочонки',
  ad_unavailable: 'Реклама сейчас недоступна',
  used_up: 'Уже использовано в этой партии',

  lotto_your_card: 'Ваша карточка',
  lotto_rival: 'Соперник',
  lotto_called: 'Выпало',
  lotto_mark: 'Отмечайте выпавшие числа',
  lotto_win: 'Вы закрыли карточку первым!',
  lotto_lose: 'Соперник закрыл карточку раньше',
  lotto_missed: 'Пропущено',
  lotto_speed: 'Скорость',
  lotto_unlock: 'Откройте «Карточку мастера» — ту же игру, но бочонки расставляете вы',

  ach_unlocked: 'Открыто',
  ach_locked: 'Закрыто',
  ach_progress: 'Открыто {a} из {b}',
};

const EN = {
  title: 'Barrels',
  tagline: 'Lotto and the master card',
  play_lotto: 'Classic lotto',
  play_master: 'Master card',
  play_drum: 'The drum',
  drum_sub: 'Pick one of three',
  drum_pick: 'The drum rolled out three barrels — take one',
  drum_note: 'The other two go back into the bag',
  drum_early: 'None of them scores yet. Low numbers work on the left of a row, high ones on the right',
  drum_returned: 'Returned',
  play_daily: 'Daily game',
  play_free: 'Free game',
  how_to: 'How to play',
  achievements: 'Collection',
  stats: 'Statistics',
  back: 'Back',
  close: 'Close',
  sound_on: 'Sound on',
  sound_off: 'Sound off',

  bag_left: 'In the bag',
  current_barrel: 'Barrel',
  score: 'Score',
  best: 'Best',
  place_hint: 'Pick a square',
  first_move: 'Place the first barrel anywhere — scoring starts with the second',
  place_hint_mobile: 'Tap a square',

  rule_rows: 'Rows: numbers ascending left to right',
  rule_cols: 'Columns: numbers from one lotto card column',
  rule_diags: 'Diagonals: numbers of the same parity',
  rule_new: 'New rule',

  result_title: 'Game over',
  result_score: 'Your score',
  result_best_new: 'New best!',
  result_rows: 'Rows',
  result_cols: 'Columns',
  result_diags: 'Diagonals',
  play_again: 'Play again',
  to_menu: 'Menu',

  daily_done: 'Daily game played',
  daily_next: 'New bag in',
  streak: 'Day streak',
  median_today: 'Median of your games',
  your_best: 'Your best',
  distribution: 'Score distribution',
  games_played: 'Games played',
  no_stats: 'Play a few games and your statistics will appear here',
  leaderboard: 'Leaderboard',
  leaderboard_guest: 'Sign in to your Yandex account to join the leaderboard. Meanwhile, here are your own statistics.',

  undo: 'Undo move',
  peek: 'Peek at three barrels',
  ad_reward_undo: 'Watch an ad and take the move back',
  ad_reward_peek: 'Watch an ad and see the next barrels',
  ad_unavailable: 'No ad available right now',
  used_up: 'Already used this game',

  lotto_your_card: 'Your card',
  lotto_rival: 'Rival',
  lotto_called: 'Called',
  lotto_mark: 'Mark the numbers as they are called',
  lotto_win: 'You closed your card first!',
  lotto_lose: 'Your rival closed their card first',
  lotto_missed: 'Missed',
  lotto_speed: 'Speed',
  lotto_unlock: 'Try the Master card — same barrels, but you place them yourself',

  ach_unlocked: 'Unlocked',
  ach_locked: 'Locked',
  ach_progress: '{a} of {b} unlocked',
};

const TR = {
  title: 'Fıçılar',
  tagline: 'Tombala ve usta kartı',
  play_lotto: 'Klasik tombala',
  play_master: 'Usta kartı',
  play_drum: 'Tambur',
  drum_sub: 'Üçünden birini seçin',
  drum_pick: 'Tambur üç fıçı çıkardı — birini alın',
  drum_note: 'Diğer ikisi torbaya geri döner',
  drum_early: 'Henüz hiçbiri puan vermez. Küçük sayılar satırın solunda, büyükler sağında işe yarar',
  drum_returned: 'Geri dönen',
  play_daily: 'Günün oyunu',
  play_free: 'Serbest oyun',
  how_to: 'Nasıl oynanır',
  achievements: 'Koleksiyon',
  stats: 'İstatistik',
  back: 'Geri',
  close: 'Kapat',
  sound_on: 'Ses açık',
  sound_off: 'Ses kapalı',

  bag_left: 'Torbada',
  current_barrel: 'Fıçı',
  score: 'Puan',
  best: 'Rekor',
  place_hint: 'Bir kare seçin',
  first_move: 'İlk fıçıyı istediğiniz yere koyun — puan ikinciden başlar',
  place_hint_mobile: 'Bir kareye dokunun',

  rule_rows: 'Satırlar: soldan sağa artan sayılar',
  rule_cols: 'Sütunlar: tombala kartının aynı sütunundan sayılar',
  rule_diags: 'Çaprazlar: aynı tek/çift sayılar',
  rule_new: 'Yeni kural',

  result_title: 'Oyun bitti',
  result_score: 'Puanınız',
  result_best_new: 'Yeni rekor!',
  result_rows: 'Satırlar',
  result_cols: 'Sütunlar',
  result_diags: 'Çaprazlar',
  play_again: 'Tekrar oyna',
  to_menu: 'Menü',

  daily_done: 'Günün oyunu oynandı',
  daily_next: 'Yeni torba',
  streak: 'Gün serisi',
  median_today: 'Oyunlarınızın ortancası',
  your_best: 'Rekorunuz',
  distribution: 'Puan dağılımı',
  games_played: 'Oynanan oyun',
  no_stats: 'Birkaç oyun oynayın, istatistikleriniz burada görünecek',
  leaderboard: 'Liderlik tablosu',
  leaderboard_guest: 'Liderlik tablosuna katılmak için Yandex hesabınıza giriş yapın. Şimdilik kendi istatistikleriniz burada.',

  undo: 'Hamleyi geri al',
  peek: 'Üç fıçıya göz at',
  ad_reward_undo: 'Reklam izle ve hamleyi geri al',
  ad_reward_peek: 'Reklam izle ve sonraki fıçıları gör',
  ad_unavailable: 'Şu anda reklam yok',
  used_up: 'Bu oyunda zaten kullanıldı',

  lotto_your_card: 'Kartınız',
  lotto_rival: 'Rakip',
  lotto_called: 'Çıkan',
  lotto_mark: 'Çıkan sayıları işaretleyin',
  lotto_win: 'Kartınızı ilk siz kapattınız!',
  lotto_lose: 'Rakibiniz kartını önce kapattı',
  lotto_missed: 'Kaçırılan',
  lotto_speed: 'Hız',
  lotto_unlock: 'Usta kartını deneyin — aynı fıçılar, ama yerleştiren sizsiniz',

  ach_unlocked: 'Açıldı',
  ach_locked: 'Kilitli',
  ach_progress: '{b} içinden {a} açıldı',
};

export const DICTS = { ru: RU, en: EN, tr: TR };
export const LANGS = Object.keys(DICTS);

let current = 'ru';

export function setLang(lang) {
  current = DICTS[lang] ? lang : 'en';
  document.documentElement.setAttribute('lang', current);
  return current;
}

export function getLang() { return current; }

export function t(key, vars) {
  const s = DICTS[current]?.[key] ?? DICTS.en[key] ?? key;
  if (!vars) return s;
  return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
}

// Названия достижений. Ключи совпадают с ACHIEVEMENTS в achievements.js.
export const ACH_TITLES = {
  ru: {
    first_game:'Первая партия', games_5:'Пять партий', games_25:'Двадцать пять', games_100:'Сто партий',
    score_50:'50 очков', score_100:'100 очков', score_150:'150 очков', score_200:'200 очков', score_250:'250 очков',
    row_full:'Полная строка', row_full_2:'Две строки', row_full_3:'Три строки', row_full_all:'Все пять строк',
    col_full:'Полный столбец', col_full_2:'Два столбца', col_full_3:'Три столбца',
    diag_full:'Диагональ', diag_both:'Обе диагонали',
    rows_only:'Мастер строк', cols_only:'Мастер столбцов', diags_only:'Мастер диагоналей', balanced:'Ровная игра',
    daily_1:'Партия дня', daily_3:'Три дня подряд', daily_7:'Неделя подряд', daily_30:'Месяц подряд',
    no_undo:'Без отмены', beat_best:'Личный рекорд', beat_median:'Выше обычного',
    perfect_row:'Чистое возрастание', decade_five:'Пять одного столбца', parity_five:'Пять одной чётности',
    lotto_win:'Победа в лото', lotto_win_5:'Пять побед', lotto_clean:'Ни одного пропуска',
    both_modes:'Оба режима', low_score:'Скромный итог', comeback:'Рывок',
    all_rules:'Все правила открыты', collector:'Собиратель',
  },
  en: {
    first_game:'First game', games_5:'Five games', games_25:'Twenty-five', games_100:'A hundred games',
    score_50:'50 points', score_100:'100 points', score_150:'150 points', score_200:'200 points', score_250:'250 points',
    row_full:'Full row', row_full_2:'Two rows', row_full_3:'Three rows', row_full_all:'All five rows',
    col_full:'Full column', col_full_2:'Two columns', col_full_3:'Three columns',
    diag_full:'Diagonal', diag_both:'Both diagonals',
    rows_only:'Master of rows', cols_only:'Master of columns', diags_only:'Master of diagonals', balanced:'Even game',
    daily_1:'Daily game', daily_3:'Three days running', daily_7:'A week running', daily_30:'A month running',
    no_undo:'No undo', beat_best:'Personal best', beat_median:'Above your usual',
    perfect_row:'Clean ascent', decade_five:'Five from one column', parity_five:'Five of one parity',
    lotto_win:'Lotto win', lotto_win_5:'Five wins', lotto_clean:'Not a single miss',
    both_modes:'Both modes', low_score:'A modest result', comeback:'Leap forward',
    all_rules:'All rules unlocked', collector:'Collector',
  },
  tr: {
    first_game:'İlk oyun', games_5:'Beş oyun', games_25:'Yirmi beş', games_100:'Yüz oyun',
    score_50:'50 puan', score_100:'100 puan', score_150:'150 puan', score_200:'200 puan', score_250:'250 puan',
    row_full:'Tam satır', row_full_2:'İki satır', row_full_3:'Üç satır', row_full_all:'Beş satırın hepsi',
    col_full:'Tam sütun', col_full_2:'İki sütun', col_full_3:'Üç sütun',
    diag_full:'Çapraz', diag_both:'Her iki çapraz',
    rows_only:'Satır ustası', cols_only:'Sütun ustası', diags_only:'Çapraz ustası', balanced:'Dengeli oyun',
    daily_1:'Günün oyunu', daily_3:'Üst üste üç gün', daily_7:'Üst üste bir hafta', daily_30:'Üst üste bir ay',
    no_undo:'Geri alma yok', beat_best:'Kişisel rekor', beat_median:'Her zamankinden iyi',
    perfect_row:'Temiz yükseliş', decade_five:'Bir sütundan beş', parity_five:'Aynı çiftlikten beş',
    lotto_win:'Tombala galibiyeti', lotto_win_5:'Beş galibiyet', lotto_clean:'Tek bir kaçırma yok',
    both_modes:'Her iki mod', low_score:'Mütevazı sonuç', comeback:'Sıçrayış',
    all_rules:'Tüm kurallar açık', collector:'Koleksiyoncu',
  },
};

export function achTitle(key) {
  return ACH_TITLES[current]?.[key] ?? ACH_TITLES.en[key] ?? key;
}
