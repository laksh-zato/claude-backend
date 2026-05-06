from langchain_core.messages import HumanMessage
from agent.message_builder import build_user_message


def test_build_with_text_only():
    msg = build_user_message(text="hello", parsed_files=[])
    assert isinstance(msg, HumanMessage)
    assert msg.content == "hello"


def test_build_with_csv_file_inlines_as_text_block():
    parsed = [{"kind": "text", "filename": "tb.csv", "mime": "text/csv", "text": "| account |\n| Cash |"}]
    msg = build_user_message(text="audit this", parsed_files=parsed)
    assert isinstance(msg.content, list)
    text_blocks = [b for b in msg.content if b["type"] == "text"]
    # First block describes file, last block is the user prompt
    assert any("tb.csv" in b["text"] for b in text_blocks)
    assert any(b["text"] == "audit this" for b in text_blocks)


def test_build_with_pdf_file_includes_file_block():
    parsed = [{
        "kind": "block",
        "filename": "x.pdf",
        "mime": "application/pdf",
        "block": {"type": "file", "file": {"filename": "x.pdf", "file_data": "data:application/pdf;base64,xxx"}},
    }]
    msg = build_user_message(text="review", parsed_files=parsed)
    file_blocks = [b for b in msg.content if b["type"] == "file"]
    assert len(file_blocks) == 1
