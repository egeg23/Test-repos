#!/usr/bin/env bash
# Рендер двух комнат квартиры 43 (гостиная-столовая + спальня 17.20 м²)
# в стиле референса Sunwave через gpt-image-1.
#
# Запуск НА СЕРВЕРЕ seller-ai (там ключ уже лежит в .env):
#   cd <папка репозитория>/floorplan-task
#   pip3 install requests   # если ещё не стоит
#   ./run_render.sh /opt/seller-ai/.env
#
# Либо на любой машине с ключом в окружении:
#   OPENAI_API_KEY=... OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1 ./run_render.sh
#
# Результат: living_room_render.png и bedroom_render.png в этой папке.
set -euo pipefail

ENV_FILE="${1:-}"
# Без аргумента — ищем .env проекта seller-ai сами.
if [[ -z "$ENV_FILE" && -z "${OPENAI_API_KEY:-}" ]]; then
  ENV_FILE=$(ls -1 /opt/seller-ai*/.env /srv/seller-ai*/.env /root/seller-ai*/.env 2>/dev/null | head -1 || true)
  [[ -n "$ENV_FILE" ]] && echo "Использую ключ из $ENV_FILE"
fi

if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
  # В .env seller-ai ключ для gpt-image может лежать в GPT_IMAGE_API_KEY
  export OPENAI_API_KEY="${GPT_IMAGE_API_KEY:-${OPENAI_API_KEY:?в $ENV_FILE нет ни GPT_IMAGE_API_KEY, ни OPENAI_API_KEY}}"
  export OPENAI_BASE_URL="${GPT_IMAGE_BASE_URL:-${OPENAI_BASE_URL:-https://api.proxyapi.ru/openai/v1}}"
fi
: "${OPENAI_API_KEY:?задайте OPENAI_API_KEY или передайте путь к .env первым аргументом}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.proxyapi.ru/openai/v1}"

cd "$(dirname "$0")"
RENDER="../.claude/skills/floorplan-render/scripts/render.py"

python3 "$RENDER" living_room.png "open-plan living and dining room with corner sofa, dining table for eight, kitchen along the bottom wall with sink and stove, potted plants"
python3 "$RENDER" bedroom.png "bedroom with large double bed, desk by the terrace window, walk-in wardrobe with shelving"

echo "Готово: floorplan-task/living_room_render.png и floorplan-task/bedroom_render.png"
