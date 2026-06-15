from __future__ import annotations

import json
import re
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base import BaseAdapter, ImagenResult
from core.session_manager import build_httpx_client


class UrreaAdapter(BaseAdapter):
    dominio = "urrea.com"
    nombre = "Urrea"

    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        """Buscar imágenes para un SKU en urrea.com a través del catálogo de búsqueda y la página de producto."""
        async with self.rate_limiter:
            async with build_httpx_client() as client:
                response = await client.get(
                    "https://urrea.com/catalogsearch/result/",
                    params={"q": sku},
                )
                response.raise_for_status()
                html = response.text

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("li.item.product.product-item")
        if not items:
            return []

        selected = self._choose_best_item(items, sku, descripcion)
        if selected is None:
            return []

        product_url = selected.select_one("a.product-item-link")
        if not product_url:
            return []

        product_url = urljoin("https://urrea.com", product_url.get("href", ""))
        fallback_image = self._extract_search_image(selected)

        async with self.rate_limiter:
            async with build_httpx_client() as client:
                product_response = await client.get(product_url)
                product_response.raise_for_status()
                product_html = product_response.text

        gallery_urls = self._extract_gallery_urls(product_html)
        if gallery_urls:
            return [
                ImagenResult(
                    sku=sku,
                    marca="urrea",
                    url=url,
                    fuente=self.dominio,
                    orden=index,
                )
                for index, url in enumerate(gallery_urls, start=1)
            ]

        if fallback_image:
            return [
                ImagenResult(
                    sku=sku,
                    marca="urrea",
                    url=fallback_image,
                    fuente=self.dominio,
                    orden=1,
                )
            ]

        return []

    @staticmethod
    def _choose_best_item(items: list["bs4.element.Tag"], sku: str, descripcion: Optional[str]) -> Optional["bs4.element.Tag"]:
        normalized_sku = re.sub(r"\W+", "", sku).lower()
        normalized_desc = re.sub(r"\W+", "", (descripcion or "")).lower()
        for item in items:
            text = item.get_text(separator=" ", strip=True).lower()
            normalized_text = re.sub(r"\W+", "", text)
            if normalized_sku and normalized_sku in normalized_text:
                return item
            if normalized_desc and normalized_desc in normalized_text:
                return item
        return items[0]

    @staticmethod
    def _extract_search_image(item: "bs4.element.Tag") -> Optional[str]:
        image_tag = item.select_one("img.product-image-photo")
        if not image_tag:
            return None
        url = image_tag.get("src") or image_tag.get("data-src") or ""
        if not url:
            return None
        if url.startswith("//"):
            url = f"https:{url}"
        return urljoin("https://urrea.com", url)

    @staticmethod
    def _extract_gallery_urls(html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.select("script[type='text/x-magento-init']")
        urls: list[str] = []
        for script in scripts:
            text = script.string or ""
            if "mage/gallery/gallery" not in text and "mage/gallery" not in text:
                continue
            array_text = UrreaAdapter._extract_json_array(text, "\"data\"")
            if not array_text:
                continue
            try:
                data = json.loads(array_text)
            except json.JSONDecodeError:
                continue
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                raw_url = entry.get("img") or entry.get("full") or entry.get("thumb")
                if not raw_url:
                    continue
                if raw_url.startswith("//"):
                    raw_url = f"https:{raw_url}"
                urls.append(urljoin("https://urrea.com", raw_url))
            if urls:
                return list(dict.fromkeys(urls))[:5]
        return []

    @staticmethod
    def _extract_json_array(text: str, key: str) -> Optional[str]:
        idx = text.find(key)
        if idx == -1:
            return None
        idx = text.find("[", idx)
        if idx == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for pos in range(idx, len(text)):
            char = text[pos]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == "\"":
                    in_string = False
            else:
                if char == "\"":
                    in_string = True
                elif char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                    if depth == 0:
                        return text[idx : pos + 1]
        return None
