from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ImagenResult:
    sku: str
    marca: str
    url: str
    fuente: str
    orden: int
    formato: Optional[str] = None
    ancho: Optional[int] = None
    alto: Optional[int] = None


class BaseAdapter(ABC):
    dominio: str
    nombre: str

    def __init__(self, rate_limiter: "RateLimiter") -> None:
        self.rate_limiter = rate_limiter

    @abstractmethod
    async def buscar(self, sku: str, descripcion: Optional[str] = None) -> List[ImagenResult]:
        """
        Buscar imágenes para un SKU en el sitio del fabricante.
        Debe devolver una lista ordenada por preferencia.
        """
        raise NotImplementedError
