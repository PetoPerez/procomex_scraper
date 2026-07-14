from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.csv_io import read_csv_any_encoding


class ResumableResults:
    COLUMNS = ["sku", "marca", "estatus", "fuente", "imagen_1", "imagen_2", "error"]

    def __init__(self, path: Path) -> None:
        self.path = path
        self._rows: list[dict] = []
        self._loaded = False
        self._skus_done: set[str] = set()

    def load(self) -> None:
        if self.path.exists():
            df = read_csv_any_encoding(self.path)
            for _, row in df.iterrows():
                sku = str(row.get("sku", "")).strip()
                if sku:
                    self._skus_done.add(sku)
            self._loaded = True

    def is_done(self, sku: str) -> bool:
        if not self._loaded:
            self.load()
        return sku in self._skus_done

    def reset(self, skus: set[str]) -> None:
        """Olvida los SKUs indicados para que vuelvan a procesarse.

        Elimina sus filas previas del CSV (si existe) y los saca del
        conjunto de "ya procesados", evitando filas duplicadas al reescribir.
        """
        skus = {str(s).strip() for s in skus}
        self._skus_done -= skus
        if self.path.exists():
            df = read_csv_any_encoding(self.path)
            df = df[~df["sku"].astype(str).str.strip().isin(skus)]
            df.to_csv(self.path, index=False, encoding="utf-8")

    def append(self, row: dict) -> None:
        if not self.path.exists():
            header = True
        else:
            header = False
        df = pd.DataFrame([row])
        df.to_csv(self.path, mode="a", index=False, header=header, encoding="utf-8")
        self._skus_done.add(row.get("sku", ""))
