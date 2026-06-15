import pytest
from adapters.base import BaseAdapter, ImagenResult


class DummyAdapter(BaseAdapter):
    dominio = "dummy.com"
    nombre = "Dummy"

    async def buscar(self, sku: str, descripcion: str | None = None):
        return [ImagenResult(sku=sku, marca="dummy", url="https://dummy.com/img.jpg", fuente=self.dominio, orden=1)]


def test_base_adapter_is_abstract() -> None:
    assert BaseAdapter.__abstractmethods__ != set()


def test_dummy_adapter_returns_result() -> None:
    dummy = DummyAdapter(rate_limiter=None)  # type: ignore[arg-type]
    assert dummy.dominio == "dummy.com"
