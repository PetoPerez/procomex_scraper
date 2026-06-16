from __future__ import annotations

import argparse
import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import httpx

from adapters.truper import TruperAdapter
from adapters.urrea import UrreaAdapter
from adapters.tubin import TubinAdapter
from adapters.pdf_catalog import FleximaticAdapter, SolverAdapter
from adapters.generico import GenericoAdapter
from core.csv_io import read_input_csv
from core.downloader import AsyncDownloader
from core.image_validator import validate_image_bytes
from core.rate_limiter import RateLimiter
from core.resumable import ResumableResults


BRAND_ADAPTERS = {
    "truper": TruperAdapter,
    "foy": TruperAdapter,
    "foset": TruperAdapter,
    "urrea": UrreaAdapter,
    "surtek": UrreaAdapter,
    "futura": UrreaAdapter,
    "tubin": TubinAdapter,
    "fleximatic": FleximaticAdapter,
    "solver": SolverAdapter,
    "coflex": GenericoAdapter,
    "valmex": GenericoAdapter,
    "rugo": GenericoAdapter,
    "polimex": GenericoAdapter,
}


def get_adapter(brand: str, rate_limiters: dict[str, RateLimiter]) -> Any:
    adapter_cls = BRAND_ADAPTERS.get(brand)
    if not adapter_cls:
        raise ValueError(f"Marca no soportada: {brand}")
    domain = adapter_cls.dominio
    if domain not in rate_limiters:
        rate_limiters[domain] = RateLimiter(domain=domain)
    return adapter_cls(rate_limiters[domain])


async def download_valid_images(
    sku: str,
    output_dir: Path,
    downloader: AsyncDownloader,
    results: list,
) -> tuple[list[str], str | None]:
    downloaded = []
    first_error = None

    for index, image_result in enumerate(results, start=1):
        try:
            image_bytes = await downloader.fetch(image_result.url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {429, 503}:
                raise
            first_error = first_error or f"http {exc.response.status_code}: {exc.request.url}"
            continue
        except Exception as exc:
            first_error = first_error or str(exc)
            continue

        valid, fmt, width, height, validation_error = validate_image_bytes(image_bytes, image_result.url)
        if not valid:
            first_error = first_error or validation_error
            continue

        target_path = output_dir / f"{sku}_{len(downloaded) + 1}.jpg"
        await downloader.save_image(target_path, image_bytes)
        downloaded.append(str(target_path.name))
        if len(downloaded) >= 2:
            break

    return downloaded, first_error


async def process_item(
    item: dict[str, Any],
    output_dir: Path,
    downloader: AsyncDownloader,
    resumable: ResumableResults,
    rate_limiters: dict[str, RateLimiter],
    semaphore: asyncio.Semaphore,
) -> None:
    sku = item["sku"]
    marca = item["marca"]
    descripcion = item.get("descripcion", "")
    adapter = get_adapter(marca, rate_limiters)
    result_row = {
        "sku": sku,
        "marca": marca,
        "estatus": "no_encontrado",
        "fuente": adapter.dominio,
        "imagen_1": "",
        "imagen_2": "",
        "error": "",
    }

    async with semaphore:
        try:
            images = await adapter.buscar(sku, descripcion)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {429, 503}:
                rate_limiters[adapter.dominio].backoff()
            result_row["error"] = f"HTTP {exc.response.status_code}"
            resumable.append(result_row)
            return
        except Exception as exc:
            result_row["error"] = str(exc)
            resumable.append(result_row)
            return

    if not images:
        result_row["error"] = "sin resultados"
        resumable.append(result_row)
        return

    try:
        async with asyncio.Semaphore(1):
            downloaded, download_error = await download_valid_images(sku, output_dir, downloader, images)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {429, 503}:
            rate_limiters[adapter.dominio].backoff()
        result_row["error"] = f"HTTP {exc.response.status_code}"
        resumable.append(result_row)
        return

    if downloaded:
        result_row["imagen_1"] = downloaded[0] if len(downloaded) > 0 else ""
        result_row["imagen_2"] = downloaded[1] if len(downloaded) > 1 else ""
        result_row["estatus"] = "ok" if len(downloaded) >= 2 else "parcial"
        result_row["error"] = download_error or ""
    else:
        result_row["error"] = download_error or "no se pudieron validar imágenes"

    resumable.append(result_row)


async def run(input_path: Path, output_path: Path, output_dir: Path, concurrency: int = 6, force: bool = False) -> None:
    df = read_input_csv(input_path)
    resumable = ResumableResults(output_path)
    resumable.load()
    if force:
        resumable.reset({str(row["sku"]) for row in df.to_dict(orient="records")})
    pending = [row for row in df.to_dict(orient="records") if not resumable.is_done(str(row["sku"]))]

    if not pending:
        logging.info("No hay SKUs pendientes. Terminando.")
        return

    rate_limiters: dict[str, RateLimiter] = {}
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        downloader = AsyncDownloader(client)
        tasks = [process_item(item, output_dir, downloader, resumable, rate_limiters, semaphore) for item in pending]
        await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de imágenes de ferretería para Shopify")
    parser.add_argument("--input", default="entrada/input.csv", help="CSV de entrada")
    parser.add_argument("--output", default="salida/resultados.csv", help="CSV de resultados")
    parser.add_argument("--images", default="salida", help="Carpeta de salida para imágenes")
    parser.add_argument("--concurrency", type=int, default=6, help="Número máximo de tareas concurrentes")
    parser.add_argument("--force", action="store_true", help="Reprocesa los SKUs del input aunque ya estén en el CSV de resultados")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_dir = Path(args.images)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(run(input_path, output_path, output_dir, concurrency=args.concurrency, force=args.force))
    except Exception as exc:
        logging.error("Error al ejecutar el scraper: %s", exc)
        raise


if __name__ == "__main__":
    main()
