#!/usr/bin/env python3
"""Фотореалистичный top-down рендер плана квартиры через OpenAI gpt-image-1.

Использование:
    python3 render.py <план.png> [дополнительные детали промпта]

Результат сохраняется рядом с входным файлом как <имя>_render.png.
Ключ API берётся строго из переменной окружения OPENAI_API_KEY.
"""

import base64
import os
import sys
from pathlib import Path

import requests

API_URL = "https://api.openai.com/v1/images/edits"

BASE_PROMPT = (
    "photorealistic top-down 2D floor plan render, oak herringbone parquet, "
    "terracotta kitchen tiles, soft realistic shadows, textured furniture, "
    "interior magazine style, keep exact wall layout and furniture positions unchanged"
)


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Использование: render.py <план.png> [дополнительные детали промпта]",
            file=sys.stderr,
        )
        return 2

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "Ошибка: переменная окружения OPENAI_API_KEY не задана.\n"
            "Экспортируйте ключ и повторите: export OPENAI_API_KEY=sk-...",
            file=sys.stderr,
        )
        return 1

    input_path = Path(sys.argv[1])
    if not input_path.is_file():
        print(f"Ошибка: файл не найден: {input_path}", file=sys.stderr)
        return 1
    if input_path.suffix.lower() != ".png":
        print(
            f"Ошибка: ожидается PNG, получено: {input_path.name}. "
            "SVG сначала конвертируйте в PNG (rsvg-convert или cairosvg).",
            file=sys.stderr,
        )
        return 1

    extra = " ".join(sys.argv[2:]).strip()
    prompt = f"{BASE_PROMPT}, {extra}" if extra else BASE_PROMPT

    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "input_fidelity": "high",
        "size": "1536x1024",
        "quality": "high",
    }

    with input_path.open("rb") as f:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"image": (input_path.name, f, "image/png")},
            timeout=300,
        )

    if response.status_code != 200:
        print(f"Ошибка API ({response.status_code}): {response.text}", file=sys.stderr)
        return 1

    payload = response.json()
    try:
        image_b64 = payload["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError):
        print(f"Неожиданный ответ API: {payload}", file=sys.stderr)
        return 1

    output_path = input_path.with_name(input_path.stem + "_render.png")
    output_path.write_bytes(base64.b64decode(image_b64))
    print(f"Готово: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
