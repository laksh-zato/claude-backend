from pathlib import Path
from typing import Union

import pandas as pd


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def parse_tabular(path_or_buf: Union[Path, bytes], mime: str) -> str:
    """Parse a CSV or XLSX file into a markdown table string."""
    try:
        if mime == "text/csv":
            df = pd.read_csv(path_or_buf)
        elif mime == XLSX_MIME:
            df = pd.read_excel(path_or_buf, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported tabular mime: {mime}")
    except Exception as exc:
        raise ValueError(f"Could not parse tabular file: {exc}") from exc

    return df.to_markdown(index=False)
