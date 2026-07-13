"""Per-API-key instruction quota enforcement using Redis.

Each API key gets a rolling 24-hour instruction budget tracked as a Redis
counter with a TTL.  The limit itself can be overridden per-key.
"""

from __future__ import annotations

from app.extensions import redis_client

QUOTA_DEFAULT_LIMIT = 1_000_000_000  # 1 billion fuel units
QUOTA_RESET_SECONDS = 86400  # 24 hours


def get_quota_key(api_key: str) -> str:
    """Redis key for instructions-used counter."""
    return f"quota:{api_key}:instructions_used"


def get_quota_limit_key(api_key: str) -> str:
    """Redis key for the per-key instruction limit."""
    return f"quota:{api_key}:instructions_limit"


def check_quota(api_key: str) -> tuple[bool, dict]:
    """Check whether *api_key* is still under its instruction quota.

    Returns ``(True, info_dict)`` when under quota and
    ``(False, info_dict)`` when over.  *info_dict* always has keys
    ``used``, ``limit``, and ``remaining``.
    """
    used_raw = redis_client.get(get_quota_key(api_key))
    limit_raw = redis_client.get(get_quota_limit_key(api_key))

    used = int(used_raw) if used_raw is not None else 0
    limit = int(limit_raw) if limit_raw is not None else QUOTA_DEFAULT_LIMIT
    remaining = max(limit - used, 0)

    info = {"used": used, "limit": limit, "remaining": remaining}
    return (used < limit, info)


def record_usage(api_key: str, instruction_count: int) -> None:
    """Add *instruction_count* to the rolling quota counter.

    If the counter doesn't yet have a TTL, one is set so the window
    automatically resets after ``QUOTA_RESET_SECONDS``.
    """
    key = get_quota_key(api_key)
    redis_client.incrby(key, instruction_count)

    # Only set TTL if the key has no expiry yet (ttl returns -1 for no expiry)
    if redis_client.ttl(key) < 0:
        redis_client.expire(key, QUOTA_RESET_SECONDS)
