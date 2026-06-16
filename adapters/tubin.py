from __future__ import annotations

import asyncio
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base import BaseAdapter, ImagenResult
from core.session_manager import build_httpx_client


# Bajo salida/ para que persista entre corridas de Docker (ese volumen va montado).
CACHE_PATH = Path("salida/.cache/tubin_index.json")
CACHE_TTL_SECONDS = 7 * 24 * 3600  # refrescar el índice una vez por semana
LISTING_URL = "https://www.tubin.com.mx/productos"
MAX_PAGES = 80
MATCH_THRESHOLD = 0.55  # fracción mínima de palabras de la consulta presentes en el nombre


def _normalize(text: str) -> str:
    """Minúsculas, sin acentos y sin signos: para comparar por palabras."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) > 1}


def _matches(qt: str, name_tokens: set[str]) -> bool:
    """Una palabra de la consulta cuenta si coincide exacta o por prefijo (>=4
    caracteres) con alguna del nombre. Tolera variantes como galvanizado/-a."""
    if qt in name_tokens:
        return True
    pref = qt[:4]
    return len(qt) >= 4 and any(nt.startswith(pref) for nt in name_tokens)


def _overlap(query: set[str], name_tokens: set[str]) -> int:
    return sum(1 for qt in query if _matches(qt, name_tokens))


class TubinAdapter(BaseAdapter):
    """Adaptador para tubin.com.mx.

    El sitio usa Livewire (sin búsqueda por URL ni sitemap), pero el listado
    `/productos?page=N` sí pagina por GET. Recorremos el catálogo una sola vez,
    lo cacheamos en disco y emparejamos cada SKU por su descripción contra el
    nombre del producto. La imagen del producto es `storage/products/{id}.jpg`.
    """

    dominio = "tubin.com.mx"
    nombre = "Tubin"

    # Índice compartido entre instancias durante la corrida: [{"name", "img", "url"}]
    _index: Optional[list[dict]] = None
    _lock = asyncio.Lock()

    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        index = await self._get_index()
        if not index:
            return []

        query = _tokens(descripcion) or _tokens(sku)
        if not query:
            return []

        best, best_score = None, 0.0
        for prod in index:
            name_tokens = prod["_tokens"]
            if not name_tokens:
                continue
            score = _overlap(query, name_tokens) / len(query)
            if score > best_score:
                best, best_score = prod, score

        if best is None or best_score < MATCH_THRESHOLD:
            return []

        return [
            ImagenResult(
                sku=sku,
                marca="tubin",
                url=best["img"],
                fuente=self.dominio,
                orden=1,
            )
        ]

    async def _get_index(self) -> list[dict]:
        if TubinAdapter._index is not None:
            return TubinAdapter._index
        async with TubinAdapter._lock:
            if TubinAdapter._index is not None:  # otra tarea lo construyó mientras esperábamos
                return TubinAdapter._index
            index = self._load_cache()
            if index is None:
                index = await self._crawl()
                self._save_cache(index)
            for prod in index:
                prod["_tokens"] = _tokens(prod["name"])
            TubinAdapter._index = index
        return TubinAdapter._index

    @staticmethod
    def _load_cache() -> Optional[list[dict]]:
        if not CACHE_PATH.exists():
            return None
        if time.time() - CACHE_PATH.stat().st_mtime > CACHE_TTL_SECONDS:
            return None
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _save_cache(index: list[dict]) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            slim = [{"name": p["name"], "img": p["img"], "url": p["url"]} for p in index]
            CACHE_PATH.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # el caché es opcional; si falla, la próxima corrida recrawlea

    async def _crawl(self) -> list[dict]:
        products: dict[str, dict] = {}
        empty_streak = 0
        async with build_httpx_client() as client:
            for page in range(1, MAX_PAGES + 1):
                async with self.rate_limiter:
                    try:
                        resp = await client.get(LISTING_URL, params={"page": page})
                        resp.raise_for_status()
                    except httpx.HTTPError:
                        break
                cards = self._parse_listing(resp.text)
                if not cards:
                    empty_streak += 1
                    if empty_streak >= 2:
                        break
                    continue
                empty_streak = 0
                for prod in cards:
                    products[prod["url"]] = prod
        return list(products.values())

    @staticmethod
    def _parse_listing(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[dict] = []
        for anchor in soup.select("a.single-prod"):
            href = anchor.get("href", "")
            img = anchor.find("img")
            if not href or img is None:
                continue
            src = img.get("src") or ""
            if "storage/products/" not in src:
                continue
            out.append(
                {
                    "url": href,
                    "name": (img.get("alt") or "").strip(),
                    "img": src,
                }
            )
        return out
