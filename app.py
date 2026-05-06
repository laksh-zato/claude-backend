import os

from flask import Flask, jsonify
from flask_cors import CORS

from files.cache import FileCache


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
