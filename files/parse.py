from pathlib import Path
from typing import TypedDict, Literal

import pandas as pd

from .csv_xlsx import parse_tabular, XLSX_MIME
from .pdf_image import to_content_block


ALLOWED_MIMES = {
    "application/pdf",
    "text/csv",
    XLSX_MIME,
    "image/png",
    "image/jpeg",
}

EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xlsx": XLSX_MIME,
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class ParsedFile(TypedDict, total=False):
    kind: Literal["text", "block"]
    filename: str
    mime: str
    text: str
    block: dict


def detect_mime(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mime = EXTENSION_TO_MIME.get(ext)
    if mime is None:
        raise ValueError(f"Unsupported file extension: {ext}")
    return mime


def _xlsx_to_csv_bytes(path: Path) -> bytes:
    """Read an XLSX (first sheet) and return CSV bytes.

    OpenRouter's XLSX parser is unreliable on real-world workbooks (multi-sheet,
    formulas, merged cells), so we convert to CSV server-side and let
    OpenRouter's reliable CSV parser handle the result.
    """
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Could not parse XLSX file: {exc}") from exc
    return df.to_csv(index=False).encode("utf-8")


def parse_upload(path: Path, filename: str) -> ParsedFile:
    mime = detect_mime(filename)

    # XLSX: convert to CSV server-side (pandas), send as CSV file block.
    if mime == XLSX_MIME:
        csv_bytes = _xlsx_to_csv_bytes(path)
        csv_filename = Path(filename).with_suffix(".csv").name
        block = to_content_block(csv_bytes, mime="text/csv", filename=csv_filename)
        return {
            "kind": "block",
            "filename": csv_filename,
            "mime": "text/csv",
            "block": block,
        }

    # CSV: validate via pandas (catches corrupt at upload boundary), send raw bytes.
    if mime == "text/csv":
        parse_tabular(path, mime=mime)  # raises on corrupt; result discarded

    block = to_content_block(path, mime=mime, filename=filename)
    return {"kind": "block", "filename": filename, "mime": mime, "block": block}
