from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _resolve_tool(env_var: str, default_name: str) -> str:
    """Find a helper binary: an explicit env override wins, else look on PATH.

    We fall back to the bare name so the actual `subprocess` call is what raises
    a clear "not found" error, rather than failing here in a confusing way.
    """
    override = os.environ.get(env_var)
    if override:
        return override
    found = shutil.which(default_name)
    return found or default_name


def _resolve_wit_dir() -> str:
    """Find the directory that holds Tandem's `task.wit` contract."""
    override = os.environ.get("TANDEM_WIT_DIR")
    if override:
        return override

    # Once packaged, the WIT ships next to this module under _bundled/wit.
    bundled = Path(__file__).resolve().parent / "_bundled" / "wit"
    if (bundled / "task.wit").exists():
        return str(bundled)

    raise RuntimeError(
        "Could not find Tandem's WIT directory. Set TANDEM_WIT_DIR to the folder "
        "that contains task.wit."
    )


def _resolve_cache_dir() -> str:
    """Where compiled components get cached between builds."""
    override = os.environ.get("TANDEM_COMPILE_CACHE")
    if override:
        return override
    cache = Path.home() / ".tandem" / "compile-cache"
    cache.mkdir(parents=True, exist_ok=True)
    return str(cache)


def build_wasm(
    *,
    source_dir: Path | str,
    entry_module: str,
    entry_function: str,
    options: dict[str, Any] | None = None,
) -> bytes:
    """Compile a marked Python function into a WASM component.

    The real work happens in the Rust compile engine (the `tandem-compile`
    binary, which drives componentize-py). This function just resolves the tools,
    shells out, and hands back the component bytes.
    """
    compile_bin = _resolve_tool("TANDEM_COMPILE_BIN", "tandem-compile")
    componentize_py = _resolve_tool("TANDEM_COMPONENTIZE_PY", "componentize-py")
    wit_dir = _resolve_wit_dir()
    cache_dir = _resolve_cache_dir()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "task.wasm")
        command = [
            compile_bin,
            "--source", str(source_dir),
            "--entry-module", entry_module,
            "--entry-function", entry_function,
            "--language", "python",
            "--wit-dir", wit_dir,
            "--componentize-py", componentize_py,
            "--cache", cache_dir,
            "--out", out_path,
        ]
        for key, value in (options or {}).items():
            command.extend(["--option", f"{key}={value}"])

        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Could not find the Tandem compiler `{compile_bin}`. It's built "
                "and installed alongside the CLI; set TANDEM_COMPILE_BIN to point "
                "at it if it lives somewhere custom."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr_text = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise RuntimeError(
                f"Failed to compile `{entry_module}.{entry_function}` to a WASM "
                f"component:\n{stderr_text}"
            ) from exc

        with open(out_path, "rb") as handle:
            return handle.read()
