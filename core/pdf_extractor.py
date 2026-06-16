from __future__ import annotations

import math
import re
from pathlib import Path

import pymupdf  # PyMuPDF

MIN_IMG_SIDE = 60  # ignora iconos/viñetas; queremos fotos de producto
TARGET_MIN_PX = 600  # lado mínimo deseado al renderizar


def _large_images(page: "pymupdf.Page") -> list[tuple[int, "pymupdf.Rect"]]:
    out: list[tuple[int, "pymupdf.Rect"]] = []
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            for rect in page.get_image_rects(xref):
                r = pymupdf.Rect(rect)
                if r.width >= MIN_IMG_SIDE and r.height >= MIN_IMG_SIDE:
                    out.append((xref, r))
        except Exception:
            continue
    return out


class PdfCatalog:
    """Indexa un catálogo PDF: código → imagen de producto más cercana.

    Los catálogos traen UNA foto representativa por familia/sección, no por SKU,
    así que varios códigos de la misma sección comparten imagen. Se asocia cada
    código con la imagen grande más cercana (misma franja vertical) de su página.
    """

    def __init__(self, pdf_path: Path, code_regex: str) -> None:
        self.path = Path(pdf_path)
        self.doc = pymupdf.open(self.path)
        self._rx = re.compile(code_regex)
        # código -> (página, bbox) de la imagen de producto más cercana
        self.index: dict[str, tuple[int, tuple[float, float, float, float]]] = {}
        self._build()

    def _build(self) -> None:
        for page in self.doc:
            codes = set(self._rx.findall(page.get_text()))
            if not codes:
                continue
            images = _large_images(page)
            if not images:
                continue
            for code in codes:
                if code in self.index:
                    continue  # primera aparición gana
                rects = page.search_for(code)
                if not rects:
                    continue
                cy, cx = rects[0].y0, rects[0].x0
                # imagen en la misma franja vertical; penaliza las que están a la derecha del código
                best = min(
                    images,
                    key=lambda ix: abs(ix[1].y0 - cy) + (0 if ix[1].x1 < cx + 60 else 40),
                )
                r = best[1]
                self.index[code] = (page.number, (r.x0, r.y0, r.x1, r.y1))

    def image_bytes(self, code: str) -> bytes | None:
        """Renderiza la región de la imagen sobre el fondo (blanco) de la página.

        Renderizar en vez de extraer el xref aplica correctamente la máscara de
        transparencia del PDF, evitando el fondo negro que deja la imagen cruda.
        """
        entry = self.index.get(code)
        if entry is None:
            return None
        pageno, bbox = entry
        rect = pymupdf.Rect(bbox)
        short_pt = min(rect.width, rect.height)
        if short_pt <= 0:
            return None
        dpi = max(150, math.ceil(TARGET_MIN_PX * 72 / short_pt))
        try:
            pix = self.doc[pageno].get_pixmap(clip=rect, dpi=dpi, alpha=False)
            return pix.tobytes("jpeg")
        except Exception:
            return None

    def close(self) -> None:
        try:
            self.doc.close()
        except Exception:
            pass
