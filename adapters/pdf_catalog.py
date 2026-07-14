from __future__ import annotations

import asyncio
import io
import logging
import re
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .base import BaseAdapter, ImagenResult
from core.parser import extract_codes
from core.pdf_extractor import PdfCatalog

PDF_DIR = Path("entrada")
CACHE_DIR = Path("salida/.cache/pdf")
MIN_SIDE = 600  # reescalamos hasta este lado mínimo para superar el validador (>=400px)

logger = logging.getLogger(__name__)


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

    _catalogs: dict[str, Optional[PdfCatalog]] = {}
    _lock = asyncio.Lock()

    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        catalog = await self._get_catalog()
        if catalog is None:
            logger.warning("[%s] no hay PDF de la marca en %s/", self.marca, PDF_DIR)
            return []

        code = self._resolve_code(sku, descripcion, catalog)
        if code is None:
            logger.info("[%s] '%s' no arrojó ningún código presente en el catálogo", self.marca, sku)
            return []

        cache_file = CACHE_DIR / self.marca / f"{code}.jpg"
        if not cache_file.exists():
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

    def _resolve_code(self, sku: str, descripcion: Optional[str], catalog: PdfCatalog) -> Optional[str]:
        """Primer código del SKU (o, si falla, de la descripción) que exista en el
        catálogo. El índice del PDF es quien valida: probamos candidatos contra él.

        Antes se exigía `fullmatch` sobre el SKU, así que un SKU con el código
        embebido en texto ("COLADERA PUSH 2249 FLEXIMATIC") se descartaba en
        silencio. Ahora se extrae el código de donde esté.
        """
        for text in (sku, descripcion):
            if not text:
                continue
            for candidate in extract_codes(text, self.marca):
                if candidate in catalog.index:
                    return candidate
        return None

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
        """El PDF cuyo nombre contiene la marca como palabra completa.

        Ojo: no vale `"flex" in nombre`, porque "Coflex" contiene "flex" y
        Fleximatic terminaba indexando el catálogo de Coflex (encontrando cero).
        Partimos el nombre en palabras y exigimos coincidencia exacta.
        """
        if not PDF_DIR.is_dir():
            return None
        for pdf in sorted(PDF_DIR.glob("*.pdf")):
            words = re.split(r"[^a-z0-9]+", pdf.stem.lower())
            if self.marca in words:
                return pdf
        return None  # exigimos un PDF nombrado por la marca para no mezclar catálogos


class FleximaticAdapter(PdfCatalogAdapter):
    dominio = "fleximatic (pdf)"
    nombre = "Fleximatic"
    marca = "fleximatic"
    code_regex = r"\d{3,6}[A-Z]?"  # ej. 2249, 4445, 2720A


class SolverAdapter(PdfCatalogAdapter):
    dominio = "solver (pdf)"
    nombre = "Solver"
    marca = "solver"
    code_regex = r"\d{3,4}"


class CoflexAdapter(PdfCatalogAdapter):
    dominio = "coflex (pdf)"
    nombre = "Coflex"
    marca = "coflex"
    code_regex = r"[A-Z]{1,4}-[A-Z0-9]{2,7}"  # ej. TF-100, PH-220, P-B3011, DJ-D48A
