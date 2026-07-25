#!/usr/bin/env bash
# Рендер двух комнат квартиры 43 БЕЗ установки чего-либо: нужны только curl,
# perl и base64 — они есть в базовой macOS (Xcode Command Line Tools НЕ нужны).
#
# Запуск:
#   OPENAI_API_KEY=... bash -c "$(curl -fsSL <raw-url этого файла>)"
#
# Результат: living_room_render.png и bedroom_render.png в текущей папке.
set -euo pipefail

: "${OPENAI_API_KEY:?задайте OPENAI_API_KEY}"
BASE_URL="${OPENAI_BASE_URL:-https://api.proxyapi.ru/openai/v1}"
RAW="https://raw.githubusercontent.com/egeg23/Test-repos/8f3a02ce331aed154aaff5518c74dc59ac60743e/floorplan-task"

BASE_PROMPT="photorealistic top-down 2D floor plan render, oak herringbone parquet, terracotta kitchen tiles, soft realistic shadows, textured furniture, interior magazine style, keep exact wall layout and furniture positions unchanged"

render() {
  local name="$1" extra="$2"

  echo "→ ${name}: скачиваю план…"
  curl -fsSL "${RAW}/${name}.png" -o "${name}.png"

  echo "→ ${name}: генерирую рендер (несколько минут, не прерывайте)…"
  curl -sS -X POST "${BASE_URL%/}/images/edits" \
    -H "Authorization: Bearer ${OPENAI_API_KEY}" \
    -F "model=gpt-image-1" \
    -F "image=@${name}.png;type=image/png" \
    -F "prompt=${BASE_PROMPT}, ${extra}" \
    -F "input_fidelity=high" \
    -F "size=1024x1536" \
    -F "quality=high" \
    -o "${name}_response.json"

  # Извлекаем и декодируем b64_json штатным perl (MIME::Base64 — core-модуль).
  perl -MMIME::Base64 -0777 -ne '
    if (/"b64_json"\s*:\s*"([^"]+)"/) { print decode_base64($1) }
  ' "${name}_response.json" > "${name}_render.png"

  if [[ ! -s "${name}_render.png" ]]; then
    rm -f "${name}_render.png"
    echo "✗ ${name}: рендер не получен. Ответ сервера:" >&2
    head -c 600 "${name}_response.json" >&2
    echo >&2
    return 1
  fi
  rm -f "${name}_response.json"
  echo "✓ ${name}_render.png готов"
}

render living_room "open-plan living and dining room with corner sofa, dining table for eight, kitchen along the bottom wall with sink and stove, potted plants"
render bedroom "bedroom with large double bed, desk by the terrace window, walk-in wardrobe with shelving"

echo
echo "Готово. Файлы в текущей папке: $(pwd)"
ls -la ./*_render.png
