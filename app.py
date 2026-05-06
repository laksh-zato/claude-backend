import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, abort
from flask_cors import CORS

from files.cache import FileCache
from files.parse import parse_upload, ALLOWED_MIMES, detect_mime


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # public demo, no auth


# Process-wide singletons.
file_cache = FileCache(
    ttl_seconds=int(os.environ.get("FILE_CACHE_TTL_SECONDS", "3600")),
    maxsize=int(os.environ.get("FILE_CACHE_MAXSIZE", "200")),
)
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", "20000000"))


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


@app.errorhandler(400)
def _400(e):
    return jsonify({"error": e.description}), 400


@app.errorhandler(413)
def _413(e):
    return jsonify({"error": e.description}), 413


@app.errorhandler(415)
def _415(e):
    return jsonify({"error": e.description}), 415
