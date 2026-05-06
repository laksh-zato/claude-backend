import base64
from pathlib import Path
from files.pdf_image import to_content_block


FIXTURES = Path(__file__).parent / "fixtures"


def test_pdf_returns_document_block():
    block = to_content_block(FIXTURES / "sample.pdf", mime="application/pdf")
    assert block["type"] == "file"
    assert block["file"]["filename"].endswith(".pdf")
    data_url = block["file"]["file_data"]
    assert data_url.startswith("data:application/pdf;base64,")
    payload = data_url.split(",", 1)[1]
    decoded = base64.b64decode(payload)
    assert decoded[:4] == b"%PDF"


def test_image_returns_image_url_block():
    img = FIXTURES / "tiny.png"
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xfa\xff\xff?\x00\x05\xfe\x02\xfe\xa3\x9eo\x9d"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    block = to_content_block(img, mime="image/png")
    assert block["type"] == "image_url"
    assert block["image_url"]["url"].startswith("data:image/png;base64,")
    img.unlink()
