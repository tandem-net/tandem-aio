"""
Desktop and CLI API routes for the Tandem desktop application.

All routes in this blueprint require a valid JWT access token issued by
the /api/v1/auth/login endpoint. The existing UserAPI key system and
Node ZKP verification are completely separate and unaffected.

Routes:
  GET  /api/v1/desktop/ping         — Server health + version (authenticated)
  GET  /api/v1/desktop/sdks         — List available SDKs
  GET  /api/v1/desktop/updates      — Check for desktop app updates
"""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Blueprint, jsonify, request

from app.blueprints.auth import require_jwt

logger = logging.getLogger(__name__)

desktop_bp = Blueprint("desktop", __name__)

# Current server-side app version — bump this when releasing a new desktop build
_DESKTOP_APP_VERSION = os.environ.get("TANDEM_DESKTOP_VERSION", "1.0.0")
_DESKTOP_DOWNLOAD_URL = os.environ.get(
    "TANDEM_DESKTOP_DOWNLOAD_URL",
    "https://tandem.wnusair.org/releases/latest/Tandem_amd64.deb",
)

# ---------------------------------------------------------------------------
# SDK registry — source of truth for what SDKs (and which versions of each)
# the CLI and desktop app can discover and install.
#
# Each entry can list more than one version under "versions". We also keep
# the older flat "version"/"download_url" fields around (see _serialize_sdk),
# mirroring the latest version, so any existing client that only understands
# one version per SDK keeps working.
# ---------------------------------------------------------------------------
_SDK_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "tandem-python-sdk",
        "language": "Python",
        "description": "Official Python SDK — task decorators, RPC dispatch, and WASM building for Tandem jobs",
        "versions": [
            {"version": "0.1.0", "download_url": None},  # bundled with the CLI, no server download yet
        ],
    },
]


def _serialize_sdk(sdk: dict[str, Any]) -> dict[str, Any]:
    """Shape one registry entry for the JSON response.

    Includes the full "versions" list plus a flat version/download_url that
    mirrors the latest version, so older clients that expect one version per
    SDK still get something sensible.
    """
    versions = sdk.get("versions") or []
    latest = versions[-1] if versions else {}
    return {
        "name": sdk["name"],
        "language": sdk.get("language"),
        "description": sdk.get("description"),
        "version": latest.get("version"),
        "download_url": latest.get("download_url"),
        "versions": versions,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@desktop_bp.route("/ping", methods=["GET"])
@require_jwt
def ping():
    """
    Authenticated health check. Returns server version and the authenticated
    user's username so the desktop can confirm the session is live.
    """
    from flask import g
    return jsonify({
        "status": "ok",
        "server": "tandem",
        "version": _DESKTOP_APP_VERSION,
        "username": g.current_user.username,
    }), 200


@desktop_bp.route("/sdks", methods=["GET"])
@require_jwt
def list_sdks():
    """
    Return the list of SDKs available for installation.
    Accepts an optional ?q= query parameter for filtering.
    """
    query = (request.args.get("q") or "").strip().lower()
    sdks = _SDK_REGISTRY
    if query:
        sdks = [
            s for s in sdks
            if query in s["name"].lower()
            or query in (s.get("language") or "").lower()
            or query in (s.get("description") or "").lower()
        ]
    return jsonify({"sdks": [_serialize_sdk(s) for s in sdks]}), 200


@desktop_bp.route("/updates", methods=["GET"])
@require_jwt
def check_updates():
    """
    Compare the client's current version against the server's known latest version.
    Returns update availability, latest version, and download URL.
    """
    current_version = (request.args.get("current_version") or "").strip()
    update_available = (
        bool(current_version) and current_version != _DESKTOP_APP_VERSION
    )
    return jsonify({
        "update_available": update_available,
        "current_version": current_version or "unknown",
        "latest_version": _DESKTOP_APP_VERSION,
        "download_url": _DESKTOP_DOWNLOAD_URL if update_available else None,
        "release_notes": None,
    }), 200
