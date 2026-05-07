import base64
from pathlib import Path

import pytest

from files.parse import parse_upload, ALLOWED_MIMES


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_csv_returns_base64_file_block():
    parsed = parse_upload(FIXTURES / "sample.csv", filename="sample.csv")
    assert parsed["kind"] == "block"
    assert parsed["filename"] == "sample.csv"
    assert parsed["mime"] == "text/csv"
    block = parsed["block"]
    assert block["type"] == "file"
    assert block["file"]["filename"] == "sample.csv"
    data_url = block["file"]["file_data"]
    assert data_url.startswith("data:text/csv;base64,")
    decoded = base64.b64decode(data_url.split(",", 1)[1]).decode("utf-8")
    assert "Cash" in decoded
    assert "account" in decoded


def test_parse_xlsx_is_converted_to_csv_base64_block():
    """XLSX is converted to CSV server-side because OpenRouter's XLSX parser
    is unreliable; OpenRouter's CSV parser handles the result reliably."""
    parsed = parse_upload(FIXTURES / "sample.xlsx", filename="sample.xlsx")
    assert parsed["kind"] == "block"
    assert parsed["filename"] == "sample.csv"
    assert parsed["mime"] == "text/csv"
    block = parsed["block"]
    assert block["type"] == "file"
    assert block["file"]["filename"] == "sample.csv"
    data_url = block["file"]["file_data"]
    assert data_url.startswith("data:text/csv;base64,")
    decoded = base64.b64decode(data_url.split(",", 1)[1]).decode("utf-8")
    assert "Cash" in decoded
    assert "account" in decoded.lower()


def test_parse_pdf_returns_block_payload():
    parsed = parse_upload(FIXTURES / "sample.pdf", filename="sample.pdf")
    assert parsed["kind"] == "block"
    assert parsed["block"]["type"] == "file"


def test_parse_corrupt_csv_at_upload_boundary_raises():
    bad = FIXTURES / "corrupt.csv"
    bad.write_bytes(b"\xff" * 1024 + b"\x00binary garbage truncated mid\xc3")
    with pytest.raises(ValueError, match="parse"):
        parse_upload(bad, filename="corrupt.csv")
    bad.unlink()


def test_parse_unknown_extension_raises():
    fake = FIXTURES / "weird.xyz"
    fake.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_upload(fake, filename="weird.xyz")
    fake.unlink()


def test_allowed_mimes_set():
    assert "application/pdf" in ALLOWED_MIMES
    assert "text/csv" in ALLOWED_MIMES
    assert "image/png" in ALLOWED_MIMES
