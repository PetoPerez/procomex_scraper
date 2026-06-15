from __future__ import annotations

import io
from typing import Optional
from PIL import Image

MIN_WIDTH = 400
MIN_HEIGHT = 400
VALID_FORMATS = {"JPEG", "PNG", "WEBP"}
PLACEHOLDER_KEYWORDS = {"placeholder", "no-image", "noimage", "missing", "default"}


def validate_image_bytes(image_bytes: bytes, source_url: str = "") -> tuple[bool, Optional[str], Optional[int], Optional[int], Optional[str]]:
    if not image_bytes:
        return False, None, None, None, "imagen vacía"

    lower_url = source_url.lower()
    if any(keyword in lower_url for keyword in PLACEHOLDER_KEYWORDS):
        return False, None, None, None, "URL de placeholder"

    if len(image_bytes) < 10_000:
        return False, None, None, None, "archivo demasiado pequeño"

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
    except Exception as exc:
        return False, None, None, None, f"formato inválido: {exc}"

    try:
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        image_format = image.format
    except Exception as exc:
        return False, None, None, None, f"error al leer imagen: {exc}"

    if image_format is None or image_format.upper() not in VALID_FORMATS:
        return False, None, None, None, f"formato no soportado: {image_format}"

    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return False, image_format, width, height, "resolución menor al mínimo"

    return True, image_format, width, height, None
