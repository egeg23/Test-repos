#!/usr/bin/env python3
"""Версия 3: планы дополнены белыми полями до пропорции 2:3, чтобы модель не
перекомпоновывала кадр (в v2 из-за этого спальня развалилась на два куска),
плюс жёсткие требования к проекции и к тексту подписей.

Только стандартная библиотека Python — работает в a-Shell на iPhone,
в Termux на Android и на любом компьютере с python3.

Запуск:
    python3 render_phone_v3.py <ключ>

Результат: living_room_render_v3.png и bedroom_render_v3.png рядом со скриптом.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

CROPS = ("https://raw.githubusercontent.com/egeg23/Test-repos/"
         "58383386663695d5f4cce5768feefb4e7c8ce5ba/floorplan-task")

# Жёсткие правила: ортогональная проекция, никакой самодеятельности с планировкой.
KEEP = (
    "Photorealistic top-down floor plan render in the style of an interior design "
    "magazine. STRICTLY ORTHOGRAPHIC BIRD'S-EYE VIEW, camera pointing straight down "
    "at 90 degrees: no perspective, no tilt, no visible fronts or sides of furniture, "
    "every object seen purely from above. Keep the exact wall layout, room proportions "
    "and furniture positions of the input plan — do NOT invent extra rooms, doors, "
    "corridors or partitions, do NOT split the image into panels or change scale "
    "between areas. Render the whole plan at ONE consistent scale. Leave the white "
    "margins around the plan pure white and empty. Reproduce the existing label text "
    "exactly as printed, same spelling and position. Soft realistic shadows, richly "
    "textured materials"
)

PROMPTS = {
    "living_room_pad": KEEP + (
        ". Floor: pale blonde oak wide planks laid in straight parallel rows, NOT "
        "herringbone, light warm beige tone. Large corner sectional sofa in dove-grey "
        "velvet with deep button tufting, chesterfield style, with colourful cushions: "
        "multicolour pixel-check, red and orange chevron zigzag, black-and-white polka "
        "dot, and a cream fringed throw. Cream rectangular rug; a large red circle sits "
        "on the rug OFF-CENTRE, and the small round dark-marble coffee table stands to "
        "the side of that circle, not on top of it. Round beige leather pouf. A wooden "
        "table-football table. Low oak TV console with a large flat-screen TV. Dining "
        "table with a cream tablecloth, plates and a small vase of flowers on it, "
        "surrounded by beige velvet chairs. Kitchen along the bottom wall: honey-oak "
        "cabinets, glossy white lower units, dark countertop, white oven, white fridge, "
        "stainless steel sink. A few potted green plants."),
    "bedroom_pad": KEEP + (
        ". Floor: light oak wide planks laid in straight parallel rows, NOT herringbone. "
        "Large double bed with a beige-taupe velvet buttoned tufted headboard and a "
        "honeycomb-quilted base, white duvet, mustard-ochre knitted throw with fringe "
        "across the foot of the bed, white and mint-green pillows plus one "
        "black-and-white patterned cushion. Large cream shaggy rug under the bed. Two "
        "bedside tables with white dome table lamps. White writing desk with a cream "
        "velvet chair and a round gold-framed mirror. Walk-in wardrobe with white "
        "shelving and folded linen. Warm beige walls, dark brown floor-length curtains "
        "at the terrace window."),
}


def post_multipart(url: str, api_key: str, fields: dict, png: bytes) -> dict:
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

    req = urllib.request.Request(
        url,
        data=b"".join(parts),
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
        print("Укажите ключ: python3 render_phone_v3.py <ключ>", file=sys.stderr)
        return 1

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1").rstrip("/")

    for name, prompt in PROMPTS.items():
        short = name.replace("_pad", "")
        print(f"→ {short}: скачиваю план…", flush=True)
        with urllib.request.urlopen(f"{CROPS}/{name}.png", timeout=120) as r:
            png = r.read()

        print(f"→ {short}: генерирую рендер (несколько минут, не прерывайте)…", flush=True)
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
            print(f"✗ {short}: ошибка API {e.code}: {e.read().decode()[:600]}", file=sys.stderr)
            return 1

        try:
            image = base64.b64decode(payload["data"][0]["b64_json"])
        except (KeyError, IndexError, TypeError):
            print(f"✗ {short}: неожиданный ответ: {str(payload)[:600]}", file=sys.stderr)
            return 1

        out = f"{short}_render_v3.png"
        with open(out, "wb") as f:
            f.write(image)
        print(f"✓ {out} готов ({len(image) // 1024} КБ)", flush=True)

    print(f"\nГотово. Файлы здесь: {os.getcwd()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
