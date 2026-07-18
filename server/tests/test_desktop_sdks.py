from __future__ import annotations

import sys
import unittest
from pathlib import Path

# The server isn't installed as a package (no setup.py/pyproject.toml under
# server/), so "app" is only importable once server/ itself is on sys.path --
# exactly how server/run.py expects to be run.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.blueprints.desktop import _serialize_sdk  # noqa: E402


class SerializeSdkTests(unittest.TestCase):
    def test_includes_the_full_versions_list(self) -> None:
        sdk = {
            "name": "tandem-python-sdk",
            "language": "Python",
            "description": "Official Python SDK",
            "versions": [
                {"version": "0.1.0", "download_url": None},
                {"version": "0.2.0", "download_url": "https://example.com/0.2.0.zip"},
            ],
        }

        result = _serialize_sdk(sdk)

        self.assertEqual(
            result["versions"],
            [
                {"version": "0.1.0", "download_url": None},
                {"version": "0.2.0", "download_url": "https://example.com/0.2.0.zip"},
            ],
        )

    def test_flat_version_fields_mirror_the_latest_version(self) -> None:
        sdk = {
            "name": "tandem-python-sdk",
            "language": "Python",
            "description": "Official Python SDK",
            "versions": [
                {"version": "0.1.0", "download_url": None},
                {"version": "0.2.0", "download_url": "https://example.com/0.2.0.zip"},
            ],
        }

        result = _serialize_sdk(sdk)

        self.assertEqual(result["version"], "0.2.0")
        self.assertEqual(result["download_url"], "https://example.com/0.2.0.zip")

    def test_handles_an_sdk_with_no_versions_yet(self) -> None:
        sdk = {"name": "brand-new-sdk", "language": "Go", "description": "", "versions": []}

        result = _serialize_sdk(sdk)

        self.assertIsNone(result["version"])
        self.assertIsNone(result["download_url"])
        self.assertEqual(result["versions"], [])


if __name__ == "__main__":
    unittest.main()
