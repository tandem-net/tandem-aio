"""Per-account resource usage: what an account is using, and against what limit.

This is scaffolding. Today only compute time (seconds the server measured) is
really measured; RAM, storage, CPU, and GPU are placeholders with clear limits,
sitting behind the same interface so they can be filled in later without
changing any callers or the `tandem usage` output.

Limits are per user *account*. A user may hold several API keys, so usage is
summed across all of a user's keys.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.extensions import db
from app.models import UserAPI
from app.utils import quota

# Per-account limits. Real enforcement comes later; for now these are just the
# numbers `tandem usage` shows percentages against. They're deliberately simple
# constants so they're easy to move to per-account config or a DB column later.
ACCOUNT_COMPUTE_LIMIT_SECONDS = quota.QUOTA_DEFAULT_LIMIT  # compute seconds, rolling 24h
ACCOUNT_RAM_LIMIT_BYTES = 5 * 2**30                    # 5 GiB
ACCOUNT_STORAGE_LIMIT_BYTES = 5 * 2**30                # 5 GiB
ACCOUNT_CPU_LIMIT_CORES = 4                            # placeholder
ACCOUNT_GPU_LIMIT_COUNT = 1                            # placeholder

# `source` values: whether `used` is a real measurement or a not-yet-wired stub.
MEASURED = "measured"
PLACEHOLDER = "placeholder"


@dataclass(frozen=True)
class ResourceMetric:
    """How much of one resource an account is using, and its ceiling.

    `source` says whether `used` is a real measurement or a placeholder that
    still needs wiring up, so `tandem usage` can be honest about which is which.
    """

    type: str
    used: float
    limit: float
    unit: str
    source: str

    @property
    def percent(self) -> float:
        if self.limit <= 0:
            return 0.0
        return round(min(self.used / self.limit * 100.0, 100.0), 1)

    def as_dict(self) -> dict:
        return {
            "type": self.type,
            "used": self.used,
            "limit": self.limit,
            "unit": self.unit,
            "percent": self.percent,
            "source": self.source,
        }


def _account_api_keys(user_id: int) -> list[str]:
    statement = select(UserAPI.api_key).where(UserAPI.user_id == user_id)
    return list(db.session.scalars(statement).all())


def _collect_compute(user_id: int) -> ResourceMetric:
    """Real: sum the rolling compute-seconds usage across the account's API keys."""
    used = 0
    for api_key in _account_api_keys(user_id):
        _, info = quota.check_quota(api_key)
        used += int(info.get("used", 0))
    return ResourceMetric(
        type="compute",
        used=float(used),
        limit=float(ACCOUNT_COMPUTE_LIMIT_SECONDS),
        unit="seconds",
        source=MEASURED,
    )


def usage_for_user(user_id: int) -> list[ResourceMetric]:
    """Gather every resource metric for one account.

    Only compute time is really measured today. RAM, storage, CPU, and GPU are
    placeholders -- a fixed limit with 0 used -- until each one gets wired up.
    This is also the order `tandem usage` prints them in.
    """

    def placeholder(resource_type: str, limit: float, unit: str) -> ResourceMetric:
        return ResourceMetric(
            type=resource_type,
            used=0.0,
            limit=float(limit),
            unit=unit,
            source=PLACEHOLDER,
        )

    return [
        _collect_compute(user_id),
        placeholder("ram", ACCOUNT_RAM_LIMIT_BYTES, "bytes"),
        placeholder("storage", ACCOUNT_STORAGE_LIMIT_BYTES, "bytes"),
        placeholder("cpu", ACCOUNT_CPU_LIMIT_CORES, "cores"),
        placeholder("gpu", ACCOUNT_GPU_LIMIT_COUNT, "gpus"),
    ]
