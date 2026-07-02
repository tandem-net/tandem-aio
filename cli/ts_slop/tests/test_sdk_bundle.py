from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tandem_cli.app_config import load_project_config
from tandem_cli.discovery import discover_project
from tandem_cli.sdk_registry import get_runtime_sdk


class SdkBundleTests(unittest.TestCase):
    def test_python_runtime_uses_bundled_sdk_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "tasks.py").write_text(
                "import tandem\n\n"
                "@tandem.compute\n"
                "def greet(name: str) -> str:\n"
                "    return f'hello {name}'\n",
                encoding="utf-8",
            )
            config_path = project_root / "tandem.toml"
            config_path.write_text(
                '[project]\nname = "demo"\nruntime = "python"\nentry = "tasks.py"\n',
                encoding="utf-8",
            )

            config = load_project_config(config_path)
            sdk_spec = get_runtime_sdk("python")
            if sdk_spec is None:
                self.fail("python runtime SDK should be registered")

            self.assertEqual(config.sdk_path, sdk_spec.bundled_path)
            self.assertEqual(config.sdk_import_name, "tandem")
            self.assertEqual(config.sdk_package_name, "tandem")

    def test_discovery_loads_tasks_from_bundled_sdk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "tasks.py").write_text(
                "import tandem\n\n"
                "@tandem.compute(batch=2)\n"
                "def greet(name: str) -> str:\n"
                "    return f'hello {name}'\n",
                encoding="utf-8",
            )
            config_path = project_root / "tandem.toml"
            config_path.write_text(
                '[project]\nname = "demo"\nruntime = "python"\nentry = "tasks.py"\n',
                encoding="utf-8",
            )

            config = load_project_config(config_path)
            discovered = discover_project(config)

            self.assertEqual(tuple(discovered.tasks), ("greet",))
            self.assertEqual(discovered.sdk_descriptor.sdk.package, "tandem")
            self.assertEqual(discovered.sdk_descriptor.sdk.language, "python")
            self.assertEqual(discovered.sdk_descriptor.tasks[0].metadata.name, "greet")


if __name__ == "__main__":
    unittest.main()
