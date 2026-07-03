from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeSdkSpec:
    """CLI metadata for a language SDK bundle."""

    runtime: str
    package_name: str
    import_name: str
    bundled_relative_path: tuple[str, ...]
    config_override_keys: tuple[str, ...] = ()

    @property
    def bundled_path(self) -> Path:
        return (
            Path(__file__).resolve().parent.joinpath(*self.bundled_relative_path)
        ).resolve()


_RUNTIME_SDKS: dict[str, RuntimeSdkSpec] = {
    "python": RuntimeSdkSpec(
        runtime="python",
        package_name="tandem",
        import_name="tandem",
        bundled_relative_path=("_bundled", "sdk", "python"),
        config_override_keys=("sdk_path", "sdk_python_path"),
    )
}


def supported_runtimes() -> tuple[str, ...]:
    return tuple(sorted(_RUNTIME_SDKS))


def get_runtime_sdk(runtime: str) -> RuntimeSdkSpec | None:
    return _RUNTIME_SDKS.get(runtime)


def resolve_sdk_path(
    *,
    runtime: str,
    project_root: Path,
    project_table: dict[str, Any],
) -> Path | None:
    spec = get_runtime_sdk(runtime)
    if spec is None:
        raise ValueError(
            f"Unsupported runtime {runtime!r}. Supported runtimes: "
            f"{', '.join(supported_runtimes())}."
        )

    for key in spec.config_override_keys:
        value = project_table.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Expected `project.{key}` to be a non-empty string.")
        sdk_path = (project_root / value.strip()).resolve()
        if not sdk_path.exists():
            raise FileNotFoundError(
                f"Could not locate the Tandem {runtime} SDK package at {sdk_path}"
            )
        return sdk_path

    bundled_path = spec.bundled_path
    return bundled_path if bundled_path.exists() else None
