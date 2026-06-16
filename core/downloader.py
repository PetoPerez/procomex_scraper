from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse
import httpx


class AsyncDownloader:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self, url: str) -> bytes:
        if url.startswith("file://"):
            # imágenes locales (p. ej. extraídas de un PDF en entrada/)
            return Path(unquote(urlparse(url).path)).read_bytes()
        response = await self.client.get(url)
        response.raise_for_status()
        return response.content

    async def save_image(self, target_path: Path, image_bytes: bytes) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(image_bytes)
