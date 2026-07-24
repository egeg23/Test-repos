---
name: floorplan-render
description: Превращает векторный/схематичный план квартиры (SVG или PNG) в фотореалистичный top-down рендер через OpenAI gpt-image-1. Применять, когда просят фотореализм, рендер или «как у дизайнера» для планировки.
---

# Floorplan Render

Превращает схематичный план квартиры (SVG или PNG) в фотореалистичный top-down
рендер через OpenAI gpt-image-1 (endpoint `/v1/images/edits`).

## Требования

- Переменная окружения `OPENAI_API_KEY`. Если она не задана — **не запускай**
  скрипт: он завершится с понятной ошибкой, рендер невозможен.
- (Опционально) `OPENAI_BASE_URL` — базовый URL API. По умолчанию
  `https://api.openai.com/v1` (OpenAI напрямую). Для RU-реселлера укажите его
  endpoint, например proxyapi: `OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1`.
- Python 3 с библиотекой `requests`.
- Для SVG-входа: `rsvg-convert` (librsvg) или `cairosvg`.

## Шаги

1. **Если вход — SVG, сначала конвертируй его в PNG** (белый фон, разрешение
   порядка 2048 px по ширине, чтобы сохранить детали):

   ```bash
   rsvg-convert -w 2048 -b white plan.svg -o plan.png
   ```

   или, если librsvg недоступен:

   ```bash
   python3 -c "import cairosvg; cairosvg.svg2png(url='plan.svg', write_to='plan.png', output_width=2048, background_color='white')"
   ```

2. **Вызови скрипт рендера** (лежит в этом скилле, `scripts/render.py`):

   ```bash
   python3 scripts/render.py plan.png
   ```

   Дополнительные детали можно дописать к базовому промпту вторым аргументом:

   ```bash
   python3 scripts/render.py plan.png "scandinavian style, light gray walls"
   ```

3. Результат сохраняется рядом с входным файлом как `<имя>_render.png`.
   **Покажи готовый рендер пользователю** (открой/отправь файл).

## Примечания

- `input_fidelity=high` критичен — он сохраняет точную геометрию стен и
  позиции мебели; не убирай этот параметр.
- Размер `1536x1024` и `quality=high` зафиксированы в скрипте.
