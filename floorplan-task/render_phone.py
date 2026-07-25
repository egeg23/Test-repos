#!/usr/bin/env python3
"""Рендер двух комнат квартиры 43 — только стандартная библиотека Python.

Ничего ставить не нужно (ни requests, ни curl, ни perl), поэтому работает
и в терминале на телефоне (iOS: a-Shell; Android: Termux), и на любом
компьютере с python3.

Запуск:
    python3 render_phone.py <ключ>
или:
    OPENAI_API_KEY=<ключ> python3 render_phone.py

Результат: living_room_render_v2.png и bedroom_render_v2.png рядом со скриптом.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

CROPS = ("https://raw.githubusercontent.com/egeg23/Test-repos/"
         "8f3a02ce331aed154aaff5518c74dc59ac60743e/floorplan-task")

KEEP = ("photorealistic top-down 2D floor plan render, interior magazine style, "
        "soft realistic shadows, richly textured materials, keep the exact wall "
        "layout, room labels and furniture positions of the input plan unchanged")

PROMPTS = {
    "living_room": KEEP + (
        ". Floor: pale blonde oak wide planks laid in straight parallel rows, NOT "
        "herringbone, light warm beige tone. Large corner sectional sofa in dove-grey "
        "velvet with deep button tufting, chesterfield style, scattered with colourful "
        "cushions: multicolour pixel-check, red and orange chevron zigzag, "
        "black-and-white polka dot, plus a cream fringed throw. White rectangular rug "
        "with one large red circle on it. Round beige leather pouf and a round coffee "
        "table with dark marble top. A wooden table-football (foosball) table standing "
        "on the floor. Low oak TV console with a large flat-screen TV. Dining table "
        "covered with a cream tablecloth, surrounded by beige velvet chairs. Kitchen "
        "along the bottom wall: honey-oak upper cabinets, glossy white lower cabinets, "
        "dark countertop, white oven, white fridge, stainless steel sink. A few potted "
        "green plants."),
    "bedroom": KEEP + (
        ". Floor: light oak wide planks laid in straight parallel rows, NOT herringbone. "
        "Large double bed with a beige-taupe velvet buttoned tufted headboard and a "
        "honeycomb-quilted base, white duvet, mustard-ochre knitted throw with fringe "
        "across the foot of the bed, white and mint-green pillows plus one "
        "black-and-white patterned cushion. Large cream shaggy rug under the bed. Two "
        "bedside tables with white dome table lamps. White writing desk with a cream "
        "velvet chair and a round gold-framed mirror above it. Walk-in wardrobe with "
        "white shelving. Warm beige walls, dark brown floor-length curtains at the "
        "terrace window."),
}


def post_multipart(url: str, api_key: str, fields: dict, png: bytes) -> dict:
    """Собирает multipart/form-data вручную — без сторонних библиотек."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="plan.png"\r\n'
        f"Content-Type: image/png\r\n\r\n".encode()
    )
    parts.append(png)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    api_key = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OPENAI_API_KEY", "")).strip()
    if not api_key:
        print("Укажите ключ: python3 render_phone.py <ключ>", file=sys.stderr)
        return 1

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1").rstrip("/")

    for name, prompt in PROMPTS.items():
        print(f"→ {name}: скачиваю план…", flush=True)
        with urllib.request.urlopen(f"{CROPS}/{name}.png", timeout=120) as r:
            png = r.read()

        print(f"→ {name}: генерирую рендер (несколько минут, не прерывайте)…", flush=True)
        fields = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "input_fidelity": "high",
            "size": "1024x1536",
            "quality": "high",
        }
        try:
            payload = post_multipart(f"{base_url}/images/edits", api_key, fields, png)
        except urllib.error.HTTPError as e:
            print(f"✗ {name}: ошибка API {e.code}: {e.read().decode()[:600]}", file=sys.stderr)
            return 1

        try:
            image = base64.b64decode(payload["data"][0]["b64_json"])
        except (KeyError, IndexError, TypeError):
            print(f"✗ {name}: неожиданный ответ: {str(payload)[:600]}", file=sys.stderr)
            return 1

        out = f"{name}_render_v2.png"
        with open(out, "wb") as f:
            f.write(image)
        print(f"✓ {out} готов ({len(image) // 1024} КБ)", flush=True)

    print(f"\nГотово. Файлы здесь: {os.getcwd()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
