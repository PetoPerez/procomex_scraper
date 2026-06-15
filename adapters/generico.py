from __future__ import annotations

from typing import List, Optional

from .base import BaseAdapter, ImagenResult


class GenericoAdapter(BaseAdapter):
    dominio = "generico"
    nombre = "Generico"

    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        """Adaptador genérico para catálogos pequeños sin integración directa definida."""
        # En v1 este adaptador no implementa búsquedas activas,
        # pero sirve como plantilla para sitios adicionales.
        return []
