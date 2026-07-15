from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tandem_cli import wasm


class BuildWasmTests(unittest.TestCase):
    """build_wasm now shells out to the `tandem-compile` engine binary. These
    pin down that it wires the arguments through and that failures are loud."""

    def setUp(self) -> None:
        # Point the tool resolvers at harmless values so nothing is looked up on
        # PATH and no real cache directory is created during the tests.
        self._env = patch.dict(
            os.environ,
            {
                "TANDEM_COMPILE_BIN": "tandem-compile-test",
                "TANDEM_COMPONENTIZE_PY": "componentize-py-test",
                "TANDEM_WIT_DIR": "/tmp/tandem-wit-test",
                "TANDEM_COMPILE_CACHE": "/tmp/tandem-cache-test",
            },
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()

    def _call(self) -> bytes:
        return wasm.build_wasm(
            source_dir=Path("/tmp/proj"),
            entry_module="app",
            entry_function="crunch",
        )

    def test_missing_compiler_binary_raises_a_clear_error(self) -> None:
        with patch.object(wasm.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaises(RuntimeError) as ctx:
                self._call()
        self.assertIn("tandem-compile", str(ctx.exception))

    def test_compile_failure_raises_with_the_underlying_stderr(self) -> None:
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["tandem-compile"],
            stderr=b"compile backend failed: unsupported construct",
        )
        with patch.object(wasm.subprocess, "run", side_effect=error):
            with self.assertRaises(RuntimeError) as ctx:
                self._call()
        message = str(ctx.exception)
        self.assertIn("app.crunch", message)
        self.assertIn("unsupported construct", message)

    def test_successful_compile_returns_the_component_bytes(self) -> None:
        component_bytes = b"\x00asm\x0d\x00\x01\x00component-bytes"

        def fake_run(cmd, **kwargs):
            # The engine writes the component to whatever --out points at.
            out_path = cmd[cmd.index("--out") + 1]
            with open(out_path, "wb") as handle:
                handle.write(component_bytes)
            # Sanity-check that the important arguments are wired through.
            self.assertEqual(cmd[cmd.index("--entry-module") + 1], "app")
            self.assertEqual(cmd[cmd.index("--entry-function") + 1], "crunch")
            self.assertEqual(cmd[cmd.index("--language") + 1], "python")
            return SimpleNamespace(returncode=0)

        with patch.object(wasm.subprocess, "run", side_effect=fake_run):
            result = self._call()
        self.assertEqual(result, component_bytes)


if __name__ == "__main__":
    unittest.main()
