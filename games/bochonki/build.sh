#!/usr/bin/env sh
# Собирает архив для загрузки в консоль разработчика Яндекс Игр.
# В архив попадает только то, что нужно игре: тесты, скриншоты и материалы
# магазина остаются снаружи.
set -e
cd "$(dirname "$0")"
OUT=build/bochonki.zip
rm -rf build && mkdir -p build
zip -q -r "$OUT" index.html styles.css src -x '*.DS_Store'
SIZE=$(wc -c < "$OUT")
printf 'Архив: %s (%s КБ)\n' "$OUT" "$((SIZE / 1024))"
[ "$SIZE" -lt 104857600 ] || { echo 'ОШИБКА: архив больше лимита в 100 МБ'; exit 1; }
