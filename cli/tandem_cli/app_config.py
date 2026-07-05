from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .sdk_registry import get_runtime_sdk, resolve_sdk_path, supported_runtimes

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback.
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class ProjectConfig:
    """Resolved CLI project configuration."""

    config_path: Path
    project_root: Path
    name: str
    runtime: str
    version: str
    entry_path: Path
    output_dir: Path
    sdk_path: Path | None
    sdk_package_name: str
    sdk_import_name: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "config_path": str(self.config_path),
            "project_root": str(self.project_root),
            "name": self.name,
            "runtime": self.runtime,
            "version": str(self.version),
            "entry_path": str(self.entry_path),
            "output_dir": str(self.output_dir),
            "sdk_path": str(self.sdk_path) if self.sdk_path is not None else None,
            "sdk_package_name": self.sdk_package_name,
            "sdk_import_name": self.sdk_import_name,
        }


def _require_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Missing required TOML table [{key}].")
    return value


def _coerce_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected `{field_name}` to be a non-empty string.")
    return value.strip()


def _resolve_entry_value(
    project: dict[str, Any], python_section: dict[str, Any]
) -> str:
    for key in ("entry", "source"):
        if key in project:
            return _coerce_string(project[key], f"project.{key}")
        if key in python_section:
            return _coerce_string(python_section[key], f"python.{key}")

    raise ValueError(
        "Project config must define `project.entry` (or `project.source`) pointing to a Python module file."
    )


def load_project_config(path: str | Path) -> ProjectConfig:
    """Load and validate a Tandem project TOML file."""

    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Project config not found: {config_path}")

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    project = _require_table(data, "project")
    python_section = data.get("python") or {}
    if not isinstance(python_section, dict):
        raise ValueError("If present, [python] must be a TOML table.")

    name = _coerce_string(project.get("name"), "project.name")
    runtime = _coerce_string(project.get("runtime", "python"), "project.runtime")
    sdk_spec = get_runtime_sdk(runtime)
    if sdk_spec is None:
        raise ValueError(
            f"Unsupported runtime {runtime!r}. Supported runtimes: "
            f"{', '.join(supported_runtimes())}."
        )

    version = _coerce_string(project.get("version", "0.1.0"), "project.version")
    entry_value = _resolve_entry_value(project, python_section)
    output_value = _coerce_string(
        project.get("output_dir", f".tandem_build/{name}"),
        "project.output_dir",
    )

    project_root = config_path.parent
    entry_path = (project_root / entry_value).resolve()
    if not entry_path.exists():
        raise FileNotFoundError(
            f"Configured Python entry file does not exist: {entry_path}"
        )
    if not entry_path.is_file():
        raise ValueError(f"Configured Python entry path is not a file: {entry_path}")

    output_dir = (project_root / output_value).resolve()
    sdk_path = resolve_sdk_path(
        runtime=runtime,
        project_root=project_root,
        project_table=project,
    )

    return ProjectConfig(
        config_path=config_path,
        project_root=project_root,
        name=name,
        runtime=runtime,
        version=version,
        entry_path=entry_path,
        output_dir=output_dir,
        sdk_path=sdk_path,
        sdk_package_name=sdk_spec.package_name,
        sdk_import_name=sdk_spec.import_name,
    )


def write_project_config(
    path: str | Path,
    *,
    name: str,
    entry: str,
    output_dir: str | None = None,
    version: str = "0.1.0",
) -> Path:
    """Create a minimal Tandem project TOML file."""

    config_path = Path(path).expanduser().resolve()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_output_dir = output_dir or f".tandem_build/{name}"
    content = (
        "[project]\n"
        f'name = "{name}"\n'
        'runtime = "python"\n'
        f'version = "{version}"\n'
        f'entry = "{entry}"\n'
        f'output_dir = "{resolved_output_dir}"\n'
        "\n[build]\n"
        'install = "pip install -r requirements.txt"\n'
        'start = "python app.py"\n'
    )

    config_path.write_text(content, encoding="utf-8")
    return config_path
