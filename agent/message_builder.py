from langchain_core.messages import HumanMessage


def build_user_message(text: str, parsed_files: list[dict]) -> HumanMessage:
    if not parsed_files:
        return HumanMessage(content=text)

    blocks: list[dict] = []
    for f in parsed_files:
        if f["kind"] == "text":
            blocks.append({
                "type": "text",
                "text": f"<file: {f['filename']} ({f['mime']})>\n{f['text']}",
            })
        elif f["kind"] == "block":
            blocks.append(f["block"])

    blocks.append({"type": "text", "text": text})
    return HumanMessage(content=blocks)
