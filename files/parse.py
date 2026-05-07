from pathlib import Path
from typing import TypedDict, Literal

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


def parse_upload(path: Path, filename: str) -> ParsedFile:
    mime = detect_mime(filename)
    # CSV/XLSX: validate by attempting to parse with pandas (catches corrupt
    # uploads at the /files boundary), then send the original bytes to the LLM
    # as a base64 file block. OpenRouter parses the file server-side.
    if mime in ("text/csv", XLSX_MIME):
        parse_tabular(path, mime=mime)  # raises on corrupt; result discarded
    block = to_content_block(path, mime=mime, filename=filename)
    return {"kind": "block", "filename": filename, "mime": mime, "block": block}
