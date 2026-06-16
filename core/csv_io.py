from __future__ import annotations

from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {"sku", "marca"}
SUPPORTED_BRANDS = {"truper", "foy", "foset", "urrea", "surtek", "futura", "tubin", "fleximatic", "solver", "coflex", "valmex", "rugo", "polimex"}


def read_input_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = REQUIRED_COLUMNS - set(df.columns.str.lower())
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {sorted(missing)}")

    df.columns = [col.lower().strip() for col in df.columns]
    df = df.rename(columns={col: col.lower().strip() for col in df.columns})
    df["sku"] = df["sku"].str.strip()
    df["marca"] = df["marca"].str.lower().str.strip()
    df["descripcion"] = df.get("descripcion", "").astype(str).str.strip()
    df["prioridad"] = pd.to_numeric(df.get("prioridad", ""), errors="coerce").fillna(999).astype(int)

    invalid_skus = df["sku"] == ""
    invalid_brands = ~df["marca"].isin(SUPPORTED_BRANDS)
    if invalid_skus.any() or invalid_brands.any():
        rows = []
        for index, row in df.loc[invalid_skus | invalid_brands].iterrows():
            errors = []
            if row["sku"] == "":
                errors.append("sku vacío")
            if row["marca"] not in SUPPORTED_BRANDS:
                errors.append(f"marca desconocida '{row['marca']}'")
            rows.append(f"fila {index + 2}: {'; '.join(errors)}")
        raise ValueError("CSV inválido:\n" + "\n".join(rows))

    return df.sort_values(["prioridad", "sku"]).reset_index(drop=True)


def load_or_create_results(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str).fillna("")
    columns = ["sku", "marca", "estatus", "fuente", "imagen_1", "imagen_2", "error"]
    return pd.DataFrame(columns=columns)


def write_result_row(path: Path, row: dict) -> None:
    header = not path.exists()
    df = pd.DataFrame([row])
    df.to_csv(path, mode="a", index=False, header=header, encoding="utf-8")
