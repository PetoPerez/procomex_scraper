from __future__ import annotations

import re
import unicodedata
from typing import Optional

# El Excel real de Procomex trae una sola columna de texto libre, con la marca y
# el código del producto embebidos en el nombre. Ejemplos:
#
#   "COLADERA UNIVERSAL PUSH 2249 FLEXIMATIC"   -> marca=fleximatic, codigo=2249
#   "CESPOL PARA FREGADERO PVC FLEXIMATIC 2307" -> marca=fleximatic, codigo=2307
#   "ANGULAR FLEXIMATIC ACETAL"                 -> marca=fleximatic, codigo=None
#   "CODO CPVC FLOWGARD 1/2\""                  -> marca=None (sin fuente propia)
#
# Este módulo convierte esa línea suelta en (marca, codigo, descripcion).

# Alias por marca: cualquiera de estas palabras en el texto identifica la marca.
BRAND_ALIASES: dict[str, tuple[str, ...]] = {
    "truper": ("truper",),
    "foy": ("foy",),
    "foset": ("foset",),
    "urrea": ("urrea",),
    "surtek": ("surtek",),
    "futura": ("futura",),
    "tubin": ("tubin",),
    "fleximatic": ("fleximatic", "flexi"),
    "solver": ("solver",),
    "coflex": ("coflex",),
    "valmex": ("valmex",),
    "rugo": ("rugo",),
    "polimex": ("polimex",),
}

# Patrones de código por marca. Se buscan DENTRO del texto (no se exige que el
# campo entero sea el código): el catálogo es quien valida al final si existe.
# Deben ir en sintonía con `code_regex` de cada adaptador en adapters/pdf_catalog.py.
CODE_PATTERNS: dict[str, tuple[str, ...]] = {
    "fleximatic": (r"\b\d{3,6}[A-Z]?\b",),
    "solver": (r"\b\d{3,4}\b",),
    "coflex": (r"\b[A-Z]{1,4}-[A-Z0-9]{2,7}\b",),
}

# Fallback cuando la marca no declara patrón propio: códigos alfanuméricos con
# dígito (evita capturar palabras normales como "CODO" o "PVC").
GENERIC_CODE_PATTERNS = (
    r"\b[A-Z]{1,4}-?\d{2,6}[A-Z]?\b",
    r"\b\d{4,6}\b",
)

# Ruido frecuente que parece código pero no lo es (medidas, años, presiones).
CODE_STOPWORDS = {"2024", "2025", "2026", "1420", "1000"}


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Minúsculas, sin acentos, sin signos: para comparar por palabras."""
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(text).lower()).strip()


def detect_brand(text: str) -> Optional[str]:
    """Devuelve la marca soportada que aparece en el texto, o None."""
    words = set(normalize(text).split())
    for brand, aliases in BRAND_ALIASES.items():
        if any(alias in words for alias in aliases):
            return brand
    return None


def extract_codes(text: str, brand: Optional[str] = None) -> list[str]:
    """Códigos candidatos dentro del texto, en orden de aparición.

    No decide cuál es el bueno: el catálogo valida cuál existe realmente.
    """
    upper = strip_accents(text or "").upper()
    patterns = CODE_PATTERNS.get(brand or "", GENERIC_CODE_PATTERNS)

    codes: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, upper):
            if match in CODE_STOPWORDS or match in codes:
                continue
            codes.append(match)
    return codes


def clean_description(text: str, brand: Optional[str], codes: list[str]) -> str:
    """El nombre del producto sin la marca ni los códigos: lo que queda es la
    descripción útil para emparejar por texto."""
    words = normalize(text).split()
    aliases = set(BRAND_ALIASES.get(brand or "", ()))
    lowered_codes = {c.lower() for c in codes}
    kept = [w for w in words if w not in aliases and w not in lowered_codes]
    return " ".join(kept)


def slugify(text: str, max_length: int = 40) -> str:
    """Identificador seguro para nombre de archivo a partir del texto libre."""
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")
    return slug[:max_length] or "producto"


def parse_product(text: str) -> dict:
    """Convierte una línea de texto libre en sus partes.

    Devuelve: {producto, marca, codigo, codigos, descripcion, id}
    - `marca` es None si ninguna marca soportada aparece en el texto.
    - `codigo` es el primer candidato (o None); `codigos` trae todos.
    - `id` es estable y seguro para usar como nombre de archivo.
    """
    text = (text or "").strip()
    brand = detect_brand(text)
    codes = extract_codes(text, brand)
    description = clean_description(text, brand, codes)

    identifier = codes[0] if codes else slugify(text)
    if brand and codes:
        identifier = f"{brand}-{codes[0]}"

    return {
        "producto": text,
        "marca": brand,
        "codigo": codes[0] if codes else None,
        "codigos": codes,
        "descripcion": description,
        "id": re.sub(r"[^A-Za-z0-9_.-]", "-", identifier),
    }
