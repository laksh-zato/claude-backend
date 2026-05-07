import base64
from pathlib import Path
from typing import Optional, Union


FILE_BLOCK_MIMES = {
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/plain",
}


def to_content_block(
    path_or_bytes: Union[Path, bytes], mime: str, filename: Optional[str] = None
) -> dict:
    """Convert a binary upload to an OpenRouter-compatible content block.

    PDFs, CSVs, XLSX/XLS, and plain text use the `file` content block
    (file_data is a base64 data URL). OpenRouter parses these server-side
    and forwards to the model — Claude reads PDFs natively; for CSV/XLSX
    OpenRouter parses and injects the parsed content. Images use the
    `image_url` content block.

    See: https://openrouter.ai/docs/features/multimodal/pdfs
    """
    if isinstance(path_or_bytes, Path):
        data = path_or_bytes.read_bytes()
        if filename is None:
            filename = path_or_bytes.name
    else:
        data = path_or_bytes
        if filename is None:
            filename = "upload.bin"

    b64 = base64.b64encode(data).decode("ascii")

    if mime in FILE_BLOCK_MIMES:
        return {
            "type": "file",
            "file": {
                "filename": filename,
                "file_data": f"data:{mime};base64,{b64}",
            },
        }

    if mime.startswith("image/"):
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        }

    raise ValueError(f"Unsupported binary mime: {mime}")
