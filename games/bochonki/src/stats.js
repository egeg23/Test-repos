// Локальная статистика — осмысленный заменитель лидерборда для неавторизованных.
//
// Значимая доля трафика платформы играет без входа в аккаунт, и для них
// таблица лидеров пуста. Тогда игрок сравнивается сам с собой: медиана
// последних партий, распределение результатов и личный рекорд.

export function median(values) {
  if (!values.length) return 0;
  const s = [...values].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
}

export function summarize(history) {
  const scores = (history || []).map((h) => h.score).filter((n) => Number.isFinite(n));
  if (!scores.length) return null;
  return {
    games: scores.length,
    best: Math.max(...scores),
    worst: Math.min(...scores),
    median: median(scores),
    average: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
    last: scores[scores.length - 1],
  };
}

// Гистограмма по корзинам фиксированной ширины — показываем, куда попал
// последний результат относительно остальных.
export function distribution(history, bucketSize = 20) {
  const scores = (history || []).map((h) => h.score).filter((n) => Number.isFinite(n));
  if (!scores.length) return [];
  const max = Math.max(...scores);
  const buckets = [];
  for (let lo = 0; lo <= max; lo += bucketSize) {
    buckets.push({ lo, hi: lo + bucketSize - 1, count: 0 });
  }
  for (const s of scores) {
    const i = Math.min(Math.floor(s / bucketSize), buckets.length - 1);
    buckets[i].count++;
  }
  return buckets;
}

// Какую долю своих прошлых партий побил этот результат.
export function percentile(history, score) {
  const scores = (history || []).map((h) => h.score).filter((n) => Number.isFinite(n));
  if (scores.length < 2) return null;
  const below = scores.filter((s) => s < score).length;
  return Math.round((below / scores.length) * 100);
}

// Серия дней: продолжается, если прошлая партия дня была вчера.
export function nextStreak(prevStreak, lastKey, todayKey) {
  if (!lastKey) return 1;
  if (lastKey === todayKey) return prevStreak || 1;
  const d = (k) => Date.UTC(+k.slice(0, 4), +k.slice(5, 7) - 1, +k.slice(8, 10));
  const gapDays = Math.round((d(todayKey) - d(lastKey)) / 86400000);
  return gapDays === 1 ? (prevStreak || 0) + 1 : 1;
}
