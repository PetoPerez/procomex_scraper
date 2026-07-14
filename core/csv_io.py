from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {"sku", "marca"}
SUPPORTED_BRANDS = {"truper", "foy", "foset", "urrea", "surtek", "futura", "tubin", "fleximatic", "solver", "coflex", "valmex", "rugo", "polimex"}

# Excel en Windows suele exportar CSV en cp1252, no en UTF-8.
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def read_csv_any_encoding(path: Path) -> pd.DataFrame:
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
        except UnicodeDecodeError:
            continue
    raise ValueError(
        f"No se pudo leer '{path}': codificación no reconocida. "
        "Guarda el archivo como CSV UTF-8 desde Excel."
    )


def read_input_csv(path: Path) -> pd.DataFrame:
    df = read_csv_any_encoding(path)
    missing = REQUIRED_COLUMNS - set(df.columns.str.lower())
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {sorted(missing)}")

    df.columns = [col.lower().strip() for col in df.columns]
    df = df.rename(columns={col: col.lower().strip() for col in df.columns})
    df["sku"] = df["sku"].str.strip()
    df["marca"] = df["marca"].str.lower().str.strip()
    df["descripcion"] = df.get("descripcion", "").astype(str).str.strip()
    df["prioridad"] = pd.to_numeric(df.get("prioridad", ""), errors="coerce").fillna(999).astype(int)

    # Una fila mala no debe tumbar la corrida entera: se marca y se sigue. Antes
    # un solo SKU vacío o una marca fuera de la lista abortaba las miles de filas
    # restantes con un ValueError.
    df = df[df["sku"] != ""].copy()
    if df.empty:
        raise ValueError(f"'{path}' no tiene ninguna fila con SKU.")

    unsupported = sorted(set(df.loc[~df["marca"].isin(SUPPORTED_BRANDS), "marca"]))
    if unsupported:
        logging.warning(
            "Marcas sin adaptador (se procesarán y quedarán como 'sin_fuente'): %s",
            ", ".join(unsupported),
        )

    return df.sort_values(["prioridad", "sku"]).reset_index(drop=True)


def load_or_create_results(path: Path) -> pd.DataFrame:
    if path.exists():
        return read_csv_any_encoding(path)
    columns = ["sku", "marca", "estatus", "fuente", "imagen_1", "imagen_2", "error"]
    return pd.DataFrame(columns=columns)


def write_result_row(path: Path, row: dict) -> None:
    header = not path.exists()
    df = pd.DataFrame([row])
    df.to_csv(path, mode="a", index=False, header=header, encoding="utf-8")
