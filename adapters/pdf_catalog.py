from __future__ import annotations

import asyncio
import io
import re
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .base import BaseAdapter, ImagenResult
from core.pdf_extractor import PdfCatalog

PDF_DIR = Path("entrada")
CACHE_DIR = Path("salida/.cache/pdf")
MIN_SIDE = 600  # reescalamos hasta este lado mínimo para superar el validador (>=400px)


def _to_jpeg(raw: bytes, min_side: int = MIN_SIDE) -> bytes:
    """Reescala (si es chica) y re-codifica a JPEG. Las fotos de catálogo rondan
    los 200 px; el validador exige >=400 px y >=10 KB, así que las agrandamos."""
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    if min(w, h) < min_side:
        scale = min_side / min(w, h)
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


class PdfCatalogAdapter(BaseAdapter):
    """Base para marcas cuya fuente es un PDF colocado en `entrada/`.

    Busca el SKU como *código* dentro del catálogo. Una imagen genérica por
    familia puede quedar compartida entre varios códigos (limitación del PDF).
    """

    marca: str = ""
    code_regex: str = r"\d{4}"        # qué SKUs intentamos buscar en el PDF
    pdf_keyword: str = ""              # filtra el archivo PDF por nombre

    _catalogs: dict[str, Optional[PdfCatalog]] = {}
    _lock = asyncio.Lock()

    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        code = (sku or "").strip()
        if not re.fullmatch(self.code_regex, code):
            return []

        cache_file = CACHE_DIR / self.marca / f"{code}.jpg"
        if not cache_file.exists():
            catalog = await self._get_catalog()
            if catalog is None:
                return []
            raw = catalog.image_bytes(code)
            if not raw:
                return []
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(_to_jpeg(raw))

        return [
            ImagenResult(
                sku=sku,
                marca=self.marca,
                url=cache_file.resolve().as_uri(),  # file://… lo lee el downloader
                fuente=self.dominio,
                orden=1,
            )
        ]

    async def _get_catalog(self) -> Optional[PdfCatalog]:
        if self.marca in self._catalogs:
            return self._catalogs[self.marca]
        async with PdfCatalogAdapter._lock:
            if self.marca in self._catalogs:
                return self._catalogs[self.marca]
            pdf = self._find_pdf()
            catalog = PdfCatalog(pdf, self.code_regex) if pdf else None
            self._catalogs[self.marca] = catalog
            return catalog

    def _find_pdf(self) -> Optional[Path]:
        if not PDF_DIR.is_dir():
            return None
        pdfs = sorted(PDF_DIR.glob("*.pdf"))
        if self.pdf_keyword:
            matched = [p for p in pdfs if self.pdf_keyword.lower() in p.name.lower()]
            if matched:
                return matched[0]
        return None  # exigimos un PDF nombrado por la marca para no mezclar catálogos


class FleximaticAdapter(PdfCatalogAdapter):
    dominio = "fleximatic (pdf)"
    nombre = "Fleximatic"
    marca = "fleximatic"
    code_regex = r"\d{4}"
    pdf_keyword = "flex"


class SolverAdapter(PdfCatalogAdapter):
    dominio = "solver (pdf)"
    nombre = "Solver"
    marca = "solver"
    code_regex = r"\d{3,4}"
    pdf_keyword = "solver"


class CoflexAdapter(PdfCatalogAdapter):
    dominio = "coflex (pdf)"
    nombre = "Coflex"
    marca = "coflex"
    code_regex = r"[A-Z]{1,4}-[A-Z0-9]{2,7}"  # ej. TF-100, PH-220, P-B3011, DJ-D48A
    pdf_keyword = "coflex"
