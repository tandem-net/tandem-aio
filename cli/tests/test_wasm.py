from __future__ import annotations

import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tandem_cli import wasm


def _sample_task() -> None:
    """Stand-in task function -- build_wasm only needs __module__/__name__ off it."""


class BuildWasmTests(unittest.TestCase):
    """build_wasm used to silently swap in a bundled dummy.wasm whenever py2wasm
    failed, so a broken compile still looked like a successful build. That file
    is gone now, so these pin down that failures are loud instead of silent."""

    def test_missing_py2wasm_binary_raises_a_clear_error(self) -> None:
        with patch.object(wasm.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaises(RuntimeError) as ctx:
                wasm.build_wasm(_sample_task)
        self.assertIn("py2wasm", str(ctx.exception))
        self.assertIn("pip install", str(ctx.exception))

    def test_compile_failure_raises_with_the_underlying_stderr(self) -> None:
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["py2wasm"],
            stderr=b"SomeCompileError: unsupported construct",
        )
        with patch.object(wasm.subprocess, "run", side_effect=error):
            with self.assertRaises(RuntimeError) as ctx:
                wasm.build_wasm(_sample_task)
        message = str(ctx.exception)
        self.assertIn("_sample_task", message)
        self.assertIn("SomeCompileError: unsupported construct", message)

    def test_successful_compile_returns_the_wasm_bytes(self) -> None:
        def fake_run(cmd, **kwargs):
            wasm_path = cmd[cmd.index("-o") + 1]
            with open(wasm_path, "wb") as f:
                f.write(b"\x00asm-fake-bytes")
            return SimpleNamespace(returncode=0)

        with patch.object(wasm.subprocess, "run", side_effect=fake_run):
            result = wasm.build_wasm(_sample_task)
        self.assertEqual(result, b"\x00asm-fake-bytes")


if __name__ == "__main__":
    unittest.main()
