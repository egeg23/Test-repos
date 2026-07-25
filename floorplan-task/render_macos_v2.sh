#!/usr/bin/env bash
# Версия 2: промпты собраны по реальным фотографиям квартиры с Airbnb
# (светлый прямой дуб вместо ёлочки, честерфилд, красный ковёр, настольный
# футбол, ТВ-тумба; в спальне — капитоне-изголовье, горчичный плед, белый стол).
#
# Нужны только curl, perl и base64 — они есть в базовой macOS.
# Запуск:
#   OPENAI_API_KEY=... bash -c "$(curl -fsSL <raw-url этого файла>)"
#
# Результат: living_room_render.png и bedroom_render.png в текущей папке.
set -euo pipefail

: "${OPENAI_API_KEY:?задайте OPENAI_API_KEY}"
BASE_URL="${OPENAI_BASE_URL:-https://api.proxyapi.ru/openai/v1}"
RAW="https://raw.githubusercontent.com/egeg23/Test-repos/8f3a02ce331aed154aaff5518c74dc59ac60743e/floorplan-task"

KEEP="photorealistic top-down 2D floor plan render, interior magazine style, soft realistic shadows, richly textured materials, keep the exact wall layout, room labels and furniture positions of the input plan unchanged"

LIVING_PROMPT="${KEEP}. Floor: pale blonde oak wide planks laid in straight parallel rows, NOT herringbone, light warm beige tone. Large corner sectional sofa in dove-grey velvet with deep button tufting, chesterfield style, scattered with colourful cushions: multicolour pixel-check, red and orange chevron zigzag, black-and-white polka dot, plus a cream fringed throw. White rectangular rug with one large red circle on it. Round beige leather pouf and a round coffee table with dark marble top. A wooden table-football (foosball) table standing on the floor. Low oak TV console with a large flat-screen TV. Dining table covered with a cream tablecloth, surrounded by beige velvet chairs. Kitchen along the bottom wall: honey-oak upper cabinets, glossy white lower cabinets, dark countertop, white oven, white fridge, stainless steel sink. A few potted green plants."

BEDROOM_PROMPT="${KEEP}. Floor: light oak wide planks laid in straight parallel rows, NOT herringbone. Large double bed with a beige-taupe velvet buttoned tufted headboard and a honeycomb-quilted base, white duvet, mustard-ochre knitted throw with fringe across the foot of the bed, white and mint-green pillows plus one black-and-white patterned cushion. Large cream shaggy rug under the bed. Two bedside tables with white dome table lamps. White writing desk with a cream velvet chair and a round gold-framed mirror above it. Walk-in wardrobe with white shelving. Warm beige walls, dark brown floor-length curtains at the terrace window."

render() {
  local name="$1" prompt="$2"

  echo "→ ${name}: скачиваю план…"
  curl -fsSL "${RAW}/${name}.png" -o "${name}.png"

  echo "→ ${name}: генерирую рендер (несколько минут, не прерывайте)…"
  curl -sS -X POST "${BASE_URL%/}/images/edits" \
    -H "Authorization: Bearer ${OPENAI_API_KEY}" \
    -F "model=gpt-image-1" \
    -F "image=@${name}.png;type=image/png" \
    -F "prompt=${prompt}" \
    -F "input_fidelity=high" \
    -F "size=1024x1536" \
    -F "quality=high" \
    -o "${name}_response.json"

  perl -MMIME::Base64 -0777 -ne '
    if (/"b64_json"\s*:\s*"([^"]+)"/) { print decode_base64($1) }
  ' "${name}_response.json" > "${name}_render_v2.png"

  if [[ ! -s "${name}_render_v2.png" ]]; then
    rm -f "${name}_render_v2.png"
    echo "✗ ${name}: рендер не получен. Ответ сервера:" >&2
    head -c 600 "${name}_response.json" >&2
    echo >&2
    return 1
  fi
  rm -f "${name}_response.json"
  echo "✓ ${name}_render_v2.png готов"
}

render living_room "$LIVING_PROMPT"
render bedroom "$BEDROOM_PROMPT"

echo
echo "Готово. Файлы в текущей папке: $(pwd)"
ls -la ./*_render_v2.png
