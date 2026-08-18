// Достижимые сочетания правил, сложности и симметрии.
// Сгенерировано tools/vet-combos.mjs (6 сидов, порог надёжности 0.5).
//
// Значение — ДОЛЯ попаданий в заказанную полосу, а не факт «сработало хоть
// раз». Разница принципиальная: критерий «хотя бы раз из трёх» помечал
// достижимым и то, что берётся в трети случаев, и игрок регулярно получал бы
// не ту полосу, что заказывал. Поймано тестом на живой таблице.
//
// Конструктор обязан сверяться с таблицей и не предлагать того, чего на
// выбранных правилах нет: самая долгая генерация уходила ровно на попытки
// добыть недостижимую полосу — больше десяти секунд впустую.
//
// Достижимо 137 сочетаний из 300 при пороге 0.5.

export const REACHABLE = {
  "9x9-boxes": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 1,
    "light:vertical": 1,
    "light:diagonal": 1,
    "hard:none": 0.5
  },
  "9x9-boxes-hyper": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 1,
    "light:vertical": 1,
    "light:diagonal": 1,
    "medium:none": 1,
    "medium:central": 1,
    "medium:horizontal": 1,
    "medium:vertical": 1,
    "medium:diagonal": 1
  },
  "9x9-boxes-diag": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 1,
    "light:vertical": 1,
    "light:diagonal": 1,
    "medium:none": 0.6666666666666666,
    "medium:central": 0.5,
    "medium:horizontal": 0.6666666666666666,
    "medium:vertical": 0.6666666666666666,
    "medium:diagonal": 0.5,
    "hard:diagonal": 1
  },
  "9x9-boxes-diag-hyper": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 1,
    "light:vertical": 1,
    "light:diagonal": 1,
    "medium:none": 1,
    "medium:central": 0.8333333333333334,
    "medium:horizontal": 1,
    "medium:vertical": 1,
    "medium:diagonal": 1,
    "hard:none": 0.5,
    "hard:central": 0.5,
    "hard:diagonal": 0.5
  },
  "9x9-jigsaw": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 1,
    "light:vertical": 1,
    "light:diagonal": 1,
    "medium:none": 1,
    "medium:central": 1,
    "medium:horizontal": 1,
    "medium:vertical": 1,
    "medium:diagonal": 0.8333333333333334,
    "hard:central": 0.5,
    "hard:diagonal": 0.5
  },
  "9x9-jigsaw-hyper": {
    "easy:none": 0.5,
    "easy:central": 0.5,
    "easy:horizontal": 0.5,
    "easy:diagonal": 0.6666666666666666,
    "light:none": 0.5,
    "light:central": 0.6666666666666666,
    "light:horizontal": 0.6666666666666666,
    "light:vertical": 0.5,
    "light:diagonal": 0.6666666666666666,
    "medium:horizontal": 0.6666666666666666,
    "medium:vertical": 0.6666666666666666,
    "medium:diagonal": 0.5,
    "hard:none": 0.5
  },
  "9x9-jigsaw-diag": {
    "easy:none": 0.8333333333333334,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 0.8333333333333334,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 0.8333333333333334,
    "light:vertical": 1,
    "light:diagonal": 1,
    "medium:none": 1,
    "medium:central": 1,
    "medium:horizontal": 0.5,
    "medium:vertical": 1,
    "medium:diagonal": 0.8333333333333334,
    "hard:none": 0.5,
    "hard:diagonal": 0.6666666666666666
  },
  "9x9-jigsaw-diag-hyper": {},
  "6x6-boxes": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 0.5,
    "light:diagonal": 0.5
  },
  "6x6-boxes-diag": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 0.8333333333333334,
    "light:horizontal": 1,
    "light:vertical": 0.8333333333333334,
    "light:diagonal": 1,
    "medium:diagonal": 0.6666666666666666
  },
  "6x6-jigsaw": {
    "easy:none": 1,
    "easy:central": 1,
    "easy:horizontal": 1,
    "easy:vertical": 1,
    "easy:diagonal": 1,
    "light:none": 1,
    "light:central": 1,
    "light:horizontal": 1,
    "light:vertical": 1,
    "light:diagonal": 1,
    "medium:none": 0.8333333333333334,
    "medium:central": 0.5
  },
  "6x6-jigsaw-diag": {}
};

/** Доля попаданий в заказанную полосу, 0 — сочетание не предлагаем. */
export function hitRate(key, band, symmetry) {
  return (REACHABLE[key] || {})[`${band}:${symmetry}`] || 0;
}

export const isReachable = (key, band, symmetry) => hitRate(key, band, symmetry) > 0;

/** Сколько всего рабочих сочетаний — число из описания игры. */
export const TOTAL_REACHABLE = 137;
