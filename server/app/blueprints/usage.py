from flask import Blueprint, jsonify

from app.utils.auth import require_user_api_key
from app.utils.usage import usage_for_user

usage_bp = Blueprint("usage", __name__)


@usage_bp.route("/usage", methods=["GET"])
def get_usage():
    """Report the calling account's resource usage and limits.

    Auth is the same API key the CLI already uses everywhere else, and usage is
    aggregated across all of the account's keys.
    """
    api_client, error = require_user_api_key()
    if error:
        return error
    assert api_client is not None

    metrics = usage_for_user(api_client.user_id)
    return jsonify(
        {
            "account": {"user_id": api_client.user_id},
            "resources": [metric.as_dict() for metric in metrics],
        }
    )
