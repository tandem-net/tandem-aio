from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tandem_cli import commands


class InitCommandTests(unittest.TestCase):
    def test_init_without_arguments_prompts_and_uses_defaults(self) -> None:
        stdout = io.StringIO()

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = Path.cwd()
            os.chdir(tmpdir)
            self.addCleanup(os.chdir, previous_cwd)

            expected_name = Path(tmpdir).name
            config_path = Path(tmpdir) / "tandem.toml"

            with patch("builtins.input", side_effect=["", "", "", "", ""]):
                with patch("sys.stdout", stdout):
                    exit_code = commands.main(["init"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(config_path.exists())

            content = config_path.read_text(encoding="utf-8")
            self.assertIn(f'name = "{expected_name}"', content)
            self.assertIn('entry = "tasks.py"', content)
            self.assertIn('version = "0.1.0"', content)
            self.assertIn(
                f'output_dir = ".tandem_build/{expected_name}"',
                content,
            )

            output = stdout.getvalue()
            self.assertIn("Create a new Tandem project config.", output)
            self.assertIn("Press Enter to accept the default", output)

    def test_init_with_explicit_arguments_stays_non_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "custom.toml"

            with patch("builtins.input") as mock_input:
                exit_code = commands.main(
                    [
                        "init",
                        str(config_path),
                        "--name",
                        "demo-app",
                        "--entry",
                        "src/tasks.py",
                    ]
                )

            self.assertEqual(exit_code, 0)
            mock_input.assert_not_called()

            content = config_path.read_text(encoding="utf-8")
            self.assertIn('name = "demo-app"', content)
            self.assertIn('entry = "src/tasks.py"', content)
            self.assertIn('version = "0.1.0"', content)
            self.assertIn('output_dir = ".tandem_build/demo-app"', content)


if __name__ == "__main__":
    unittest.main()
