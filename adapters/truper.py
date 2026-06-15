from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base import BaseAdapter, ImagenResult
from core.session_manager import build_httpx_client


class TruperAdapter(BaseAdapter):
    dominio = "truper.com"
    nombre = "Truper"

    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        """Buscar imágenes para un SKU en truper.com usando el catálogo de búsqueda."""
        async with self.rate_limiter:
            async with build_httpx_client() as client:
                response = await client.get(
                    "https://www.truper.com/catalogsearch/result/",
                    params={"q": sku},
                )
                response.raise_for_status()
                html = response.text

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("ul.products-grid li.item")
        if not items:
            return []

        selected = self._choose_best_item(items, sku)
        if selected is None:
            return []

        image = selected.select_one("a.product-image img")
        if not image:
            return []

        image_url = self._extract_image_url(image)
        if not image_url:
            return []

        return [
            ImagenResult(
                sku=sku,
                marca="truper",
                url=image_url,
                fuente=self.dominio,
                orden=1,
            )
        ]

    @staticmethod
    def _choose_best_item(items: list["bs4.element.Tag"], sku: str) -> Optional["bs4.element.Tag"]:
        normalized_sku = re.sub(r"\W+", "", sku).lower()
        best_item = None
        for item in items:
            text = " ".join(
                [item.get_text(separator=" ", strip=True) or "",]
            ).lower()
            if normalized_sku and normalized_sku in re.sub(r"\W+", "", text):
                return item
            if best_item is None:
                best_item = item
        return best_item

    @staticmethod
    def _extract_image_url(image_tag: "bs4.element.Tag") -> str:
        srcset = image_tag.get("srcset", "")
        if srcset:
            candidates = [part.strip().split(" ")[0] for part in srcset.split(",") if part.strip()]
            if candidates:
                url = candidates[-1]
            else:
                url = image_tag.get("src", "")
        else:
            url = image_tag.get("src", "") or ""

        if url.startswith("//"):
            url = f"https:{url}"
        return urljoin("https://www.truper.com", url)
