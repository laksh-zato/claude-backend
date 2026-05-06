import base64
from pathlib import Path
from typing import Union


def to_content_block(path_or_bytes: Union[Path, bytes], mime: str, filename: str = None) -> dict:
    """Convert a PDF or image to an OpenRouter-compatible content block.

    PDF format follows OpenRouter's PDF support (file content block).
    Image format follows OpenAI's vision API (image_url content block).
    Both Anthropic-on-OpenRouter accept these.

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

    if mime == "application/pdf":
        return {
            "type": "file",
            "file": {
                "filename": filename,
                "file_data": f"data:application/pdf;base64,{b64}",
            },
        }

    if mime.startswith("image/"):
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        }

    raise ValueError(f"Unsupported binary mime: {mime}")
