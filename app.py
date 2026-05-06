import asyncio
import logging
import os
import queue
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

from flask import Flask, Response, jsonify, request, abort, stream_with_context
from flask_cors import CORS
from openai import APIError, AuthenticationError, RateLimitError

from agent.graph import build_agent
from agent.message_builder import build_user_message
from files.cache import FileCache
from files.parse import parse_upload, ALLOWED_MIMES, detect_mime
from sse import format_sse, EventTranslator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # public demo, no auth


# Process-wide singletons.
file_cache = FileCache(
    ttl_seconds=int(os.environ.get("FILE_CACHE_TTL_SECONDS", "3600")),
    maxsize=int(os.environ.get("FILE_CACHE_MAXSIZE", "200")),
)
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", "20000000"))


@lru_cache(maxsize=8)
def _get_agent_for_model(model_slug: str):
    """Build (and cache) one deepagent per model slug. ~50ms first call per slug."""
    return build_agent(default_model=model_slug)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/files", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        abort(400, description="missing 'file' field")

    f = request.files["file"]
    filename = f.filename or "upload.bin"

    # Size check — read first MAX_FILE_BYTES+1, fail if more
    f.stream.seek(0, 2)  # to end
    size = f.stream.tell()
    f.stream.seek(0)
    if size > MAX_FILE_BYTES:
        abort(413, description=f"File exceeds {MAX_FILE_BYTES} bytes")

    # Extension whitelist
    try:
        mime = detect_mime(filename)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 415

    if mime not in ALLOWED_MIMES:
        return jsonify({"error": f"Unsupported mime: {mime}"}), 415

    # Persist to a temp file for pandas/pypdf/etc., parse, then drop the temp.
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
        tmp.write(f.stream.read())
        tmp_path = Path(tmp.name)

    try:
        parsed = parse_upload(tmp_path, filename=filename)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    finally:
        tmp_path.unlink(missing_ok=True)

    file_id = file_cache.put(parsed)
    return jsonify({"file_id": file_id, "filename": filename, "mime": mime})


@app.route("/files/<file_id>", methods=["DELETE"])
def delete_file(file_id: str):
    file_cache.delete(file_id)
    return "", 204


def _resolve_files(file_ids: list[str]) -> tuple[list[dict], list[str]]:
    parsed = []
    missing = []
    for fid in file_ids:
        payload = file_cache.get(fid)
        if payload is None:
            missing.append(fid)
        else:
            parsed.append(payload)
    return parsed, missing


def _stream_events(text: str, file_ids: list[str], thread_id: str, model: str):
    """Generator yielding SSE-formatted strings.

    Bridges LangGraph's async `astream_events` into Flask's sync streaming
    response by running the async iterator in a worker thread that pushes
    translated payloads onto a queue consumed by this generator.
    """
    yield format_sse({"type": "model", "model": model})

    parsed, missing = _resolve_files(file_ids)
    if missing:
        yield format_sse({
            "type": "error",
            "message": f"File expired, please re-attach (ids: {', '.join(missing)})",
        })
        yield format_sse({"type": "done"})
        return

    user_msg = build_user_message(text=text, parsed_files=parsed)
    config = {"configurable": {"thread_id": thread_id, "model": model}}
    translator = EventTranslator(current_model=model)

    q: "queue.Queue[dict | None]" = queue.Queue()

    async def runner():
        try:
            agent = _get_agent_for_model(model)
            async for raw in agent.astream_events(
                {"messages": [user_msg]}, config=config, version="v2"
            ):
                payload = translator.translate(raw)
                if payload is not None:
                    q.put(payload)
        except AuthenticationError as exc:
            logger.exception("OpenRouter authentication error: %s", exc)
            q.put({"type": "error", "message": "Backend misconfigured: invalid OpenRouter key"})
        except RateLimitError as exc:
            logger.exception("OpenRouter rate limit hit: %s", exc)
            q.put({"type": "error", "message": "Rate limited; please retry shortly"})
        except APIError as exc:
            logger.exception("OpenRouter API error: %s", exc)
            q.put({"type": "error", "message": "Upstream model error; please retry"})
        except Exception as exc:
            logger.exception("Unexpected agent error: %s", exc)
            q.put({"type": "error", "message": "Agent error; please retry"})
        finally:
            q.put(None)

    t = threading.Thread(target=lambda: asyncio.run(runner()), daemon=True)
    t.start()

    while True:
        evt = q.get()
        if evt is None:
            break
        yield format_sse(evt)

    yield format_sse({"type": "done"})


@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    text = body.get("text", "")
    file_ids = body.get("file_ids", [])
    thread_id = body.get("thread_id") or "default"
    model = body.get("model") or "anthropic/claude-sonnet-4.6"

    return Response(
        stream_with_context(_stream_events(text, file_ids, thread_id, model)),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.errorhandler(400)
def _400(e):
    return jsonify({"error": e.description}), 400


@app.errorhandler(413)
def _413(e):
    return jsonify({"error": e.description}), 413


@app.errorhandler(415)
def _415(e):
    return jsonify({"error": e.description}), 415
