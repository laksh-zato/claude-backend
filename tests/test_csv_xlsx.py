from pathlib import Path

import pytest

from files.csv_xlsx import parse_tabular


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_csv_returns_markdown_table():
    md = parse_tabular(FIXTURES / "sample.csv", mime="text/csv")
    assert "| account" in md
    assert "Cash" in md
    assert "1500" in md


def test_parse_xlsx_returns_markdown_table():
    md = parse_tabular(
        FIXTURES / "sample.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert "Cash" in md
    assert "| account" in md


def test_parse_corrupt_csv_raises_value_error():
    bad = FIXTURES / "bad.bin"
    bad.write_bytes(b"\xff" * 1024 + b"\x00binary garbage truncated mid\xc3")
    with pytest.raises(ValueError, match="parse"):
        parse_tabular(bad, mime="text/csv")
    bad.unlink()
