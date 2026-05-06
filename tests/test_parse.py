from pathlib import Path
from files.parse import parse_upload, ALLOWED_MIMES


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_csv_returns_text_payload():
    parsed = parse_upload(FIXTURES / "sample.csv", filename="sample.csv")
    assert parsed["kind"] == "text"
    assert "Cash" in parsed["text"]
    assert parsed["filename"] == "sample.csv"
    assert parsed["mime"] == "text/csv"


def test_parse_pdf_returns_block_payload():
    parsed = parse_upload(FIXTURES / "sample.pdf", filename="sample.pdf")
    assert parsed["kind"] == "block"
    assert parsed["block"]["type"] == "file"


def test_parse_unknown_extension_raises():
    import pytest

    fake = FIXTURES / "weird.xyz"
    fake.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_upload(fake, filename="weird.xyz")
    fake.unlink()


def test_allowed_mimes_set():
    assert "application/pdf" in ALLOWED_MIMES
    assert "text/csv" in ALLOWED_MIMES
    assert "image/png" in ALLOWED_MIMES
