from pathlib import Path
import pandas as pd
from core.csv_io import read_input_csv


def test_read_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("sku,marca,descripcion,prioridad\nABC123,truper,Test,1\n")

    df = read_input_csv(csv_path)

    assert len(df) == 1
    assert df.iloc[0]["sku"] == "ABC123"
    assert df.iloc[0]["marca"] == "truper"
    assert df.iloc[0]["prioridad"] == 1
