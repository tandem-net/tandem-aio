"""
/api blueprint — Desktop app integration routes.

Provides:
  GET /api/ping          — Health check + version for the desktop app
  GET /api/sdks          — List / search available SDKs
  GET /api/sdks/<name>/download — Download an SDK archive
  GET /api/updates       — Check for a newer desktop app version
"""

import os
from flask import Blueprint, jsonify, request, send_file, abort

api_bp = Blueprint("api", __name__)

# ─── App version (bump this when you ship a new .deb) ────────────────────────
APP_VERSION = os.environ.get("TANDEM_APP_VERSION", "1.0.0")

# ─── SDK registry ─────────────────────────────────────────────────────────────
_SDK_REGISTRY = [
    {
        "name": "tandem-python-sdk",
        "version": "1.0.0",
        "language": "python",
        "description": "Official Python SDK for submitting Tandem jobs",
        "download_url": None,
    },
    {
        "name": "tandem-rust-sdk",
        "version": "1.0.0",
        "language": "rust",
        "description": "Rust crate for building Tandem compute tasks",
        "download_url": None,
    },
    {
        "name": "tandem-node-sdk",
        "version": "1.0.0",
        "language": "javascript",
        "description": "Node.js / TypeScript SDK for Tandem distributed jobs",
        "download_url": None,
    },
    {
        "name": "tandem-cli-sdk",
        "version": "1.0.0",
        "language": "python",
        "description": "Command-line interface for managing Tandem deployments",
        "download_url": None,
    },
]

# ─── Routes ───────────────────────────────────────────────────────────────────

@api_bp.route("/ping", methods=["GET"])
def ping():
    """
    Health check for the desktop app.

    Returns JSON: { status, version }
    """
    return jsonify({"status": "ok", "version": APP_VERSION}), 200


@api_bp.route("/sdks", methods=["GET"])
def list_sdks():
    """
    Return the SDK registry, optionally filtered by a search query.

    Query params:
      q  — optional free-text filter applied to name, language, and description
    """
    query = (request.args.get("q") or "").strip().lower()

    if query:
        results = [
            sdk
            for sdk in _SDK_REGISTRY
            if query in sdk["name"].lower()
            or query in (sdk.get("language") or "").lower()
            or query in (sdk.get("description") or "").lower()
        ]
    else:
        results = list(_SDK_REGISTRY)

    return jsonify({"sdks": results, "total": len(results)}), 200


@api_bp.route("/sdks/<string:sdk_name>/download", methods=["GET"])
def download_sdk(sdk_name: str):
    """
    Download an SDK archive.

    In production, serve the real .tar.gz from object storage.
    Currently returns 404 if no download_url is configured for the SDK.
    """
    if ".." in sdk_name or "/" in sdk_name or "\\" in sdk_name:
        abort(400, description="Invalid SDK name")

    sdk = next((s for s in _SDK_REGISTRY if s["name"] == sdk_name), None)
    if sdk is None:
        abort(404, description=f"SDK '{sdk_name}' not found")

    download_url = sdk.get("download_url")

    sdk_file_path = os.environ.get(f"TANDEM_SDK_PATH_{sdk_name.upper().replace('-', '_')}")
    if sdk_file_path and os.path.isfile(sdk_file_path):
        return send_file(
            sdk_file_path,
            mimetype="application/gzip",
            as_attachment=True,
            download_name=f"{sdk_name}.tar.gz",
        )

    if download_url:
        from flask import redirect
        return redirect(download_url, code=302)

    abort(404, description=f"SDK '{sdk_name}' archive is not yet available for download")


@api_bp.route("/updates", methods=["GET"])
def check_updates():
    """
    Check whether a newer version of the desktop app is available.

    Query params:
      current_version — the version string reported by the running app

    Returns JSON: { latest_version, update_available, download_url, release_notes }
    """
    current = (request.args.get("current_version") or "0.0.0").strip()

    download_url = os.environ.get("TANDEM_APP_DOWNLOAD_URL")
    release_notes = os.environ.get("TANDEM_APP_RELEASE_NOTES", "")

    update_available = current != APP_VERSION

    return jsonify(
        {
            "current_version": current,
            "latest_version": APP_VERSION,
            "update_available": update_available,
            "download_url": download_url if update_available else None,
            "release_notes": release_notes if update_available else None,
        }
    ), 200
