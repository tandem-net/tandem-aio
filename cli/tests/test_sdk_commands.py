from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tandem_cli import commands, sdk_commands
from tandem_cli.auth import AuthSession


def _fake_session() -> AuthSession:
    return AuthSession(
        username="demo",
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        api_key="fake-api-key",
        server_url="http://127.0.0.1:6767",
    )


class _FakeResponse:
    def __init__(self, *, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}
        self.text = json.dumps(payload)

    def json(self) -> dict[str, object]:
        return self._payload


_ONE_SDK_REGISTRY = {
    "sdks": [
        {
            "name": "tandem-python-sdk",
            "language": "Python",
            "description": "Official Python SDK",
            "version": "0.1.0",
            "download_url": None,
            "versions": [{"version": "0.1.0", "download_url": None}],
        }
    ]
}

_TWO_SDK_REGISTRY = {
    "sdks": [
        _ONE_SDK_REGISTRY["sdks"][0],
        {
            "name": "tandem-rust-sdk",
            "language": "Rust",
            "description": "Not actually bundled anywhere",
            "version": "0.1.0",
            "download_url": None,
            "versions": [{"version": "0.1.0", "download_url": None}],
        },
    ]
}


class SdkListTests(unittest.TestCase):
    def test_sdk_list_requires_login(self) -> None:
        stderr = io.StringIO()
        with patch(
            "tandem_cli.sdk_commands.require_auth",
            side_effect=RuntimeError("Not logged in. Run `tandem auth login` first."),
        ):
            with patch("sys.stderr", stderr):
                exit_code = commands.main(["sdk", "list"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Not logged in", stderr.getvalue())

    def test_sdk_list_prints_name_language_and_versions(self) -> None:
        stdout = io.StringIO()
        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
            ):
                with patch("sys.stdout", stdout):
                    exit_code = commands.main(["sdk", "list"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("tandem-python-sdk", output)
        self.assertIn("Python", output)
        self.assertIn("0.1.0", output)


class ResolveSdkTests(unittest.TestCase):
    def test_auto_selects_the_only_sdk_when_name_omitted(self) -> None:
        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
            ):
                resolved = sdk_commands.resolve_sdk(None)

        self.assertEqual(resolved.name, "tandem-python-sdk")
        self.assertEqual(resolved.version, "0.1.0")
        self.assertTrue(resolved.bundle_path.exists())

    def test_raises_with_available_names_when_ambiguous(self) -> None:
        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=_TWO_SDK_REGISTRY),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    sdk_commands.resolve_sdk(None)

        message = str(ctx.exception)
        self.assertIn("tandem-python-sdk", message)
        self.assertIn("tandem-rust-sdk", message)

    def test_unknown_explicit_name_lists_available(self) -> None:
        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    sdk_commands.resolve_sdk("does-not-exist")

        self.assertIn("does-not-exist", str(ctx.exception))
        self.assertIn("tandem-python-sdk", str(ctx.exception))

    def test_sdk_the_server_lists_but_the_cli_has_no_bundle_for_raises(self) -> None:
        registry = {
            "sdks": [
                {
                    "name": "some-future-sdk",
                    "language": "Go",
                    "description": "not shipped with this CLI build",
                    "versions": [{"version": "1.0.0", "download_url": None}],
                }
            ]
        }
        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=registry),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    sdk_commands.resolve_sdk(None)

        self.assertIn("doesn't carry a local copy", str(ctx.exception))


class SdkDownloadTests(unittest.TestCase):
    def test_download_copies_the_renamed_sdk_into_the_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "out"
            with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
                with patch(
                    "tandem_cli.sdk_commands.requests.get",
                    return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
                ):
                    resolved = sdk_commands.resolve_sdk(None)
                    destination = sdk_commands.download_sdk(resolved, output_dir)

            self.assertEqual(destination, output_dir)
            self.assertTrue((output_dir / "tandem" / "__init__.py").exists())
            pyproject_text = (output_dir / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn('name = "tandem-python"', pyproject_text)

    def test_download_refuses_to_overwrite_an_existing_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "out"
            output_dir.mkdir()
            with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
                with patch(
                    "tandem_cli.sdk_commands.requests.get",
                    return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
                ):
                    resolved = sdk_commands.resolve_sdk(None)
                    with self.assertRaises(RuntimeError) as ctx:
                        sdk_commands.download_sdk(resolved, output_dir)

            self.assertIn("already exists", str(ctx.exception))

    def test_sdk_download_command_defaults_output_to_cwd_slash_name(self) -> None:
        stdout = io.StringIO()

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = Path.cwd()
            os.chdir(tmpdir)
            self.addCleanup(os.chdir, previous_cwd)

            with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
                with patch(
                    "tandem_cli.sdk_commands.requests.get",
                    return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
                ):
                    with patch("sys.stdout", stdout):
                        exit_code = commands.main(["sdk", "download"])

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(tmpdir) / "tandem-python-sdk" / "tandem" / "__init__.py").exists())
            self.assertIn("Downloaded tandem-python-sdk", stdout.getvalue())


class SdkInstallTests(unittest.TestCase):
    def test_install_stages_a_copy_and_invokes_pip_against_it(self) -> None:
        captured_argv: list[list[str]] = []
        staged_path_had_files_when_pip_ran = {"value": False}

        def fake_run(argv, **_kwargs):
            captured_argv.append(argv)
            staged_path = Path(argv[-1])
            staged_path_had_files_when_pip_ran["value"] = (
                staged_path / "tandem" / "__init__.py"
            ).exists()

            class _Result:
                returncode = 0

            return _Result()

        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
            ):
                with patch("tandem_cli.sdk_commands.subprocess.run", side_effect=fake_run):
                    resolved = sdk_commands.resolve_sdk(None)
                    version = sdk_commands.install_sdk(resolved, target_python="/fake/python")

        self.assertEqual(version, "0.1.0")
        self.assertEqual(len(captured_argv), 1)
        self.assertEqual(captured_argv[0][:3], ["/fake/python", "-m", "pip"])
        self.assertEqual(captured_argv[0][3], "install")
        self.assertTrue(staged_path_had_files_when_pip_ran["value"])

    def test_install_raises_when_pip_fails(self) -> None:
        def fake_run(_argv, **_kwargs):
            class _Result:
                returncode = 1

            return _Result()

        with patch("tandem_cli.sdk_commands.require_auth", return_value=_fake_session()):
            with patch(
                "tandem_cli.sdk_commands.requests.get",
                return_value=_FakeResponse(status_code=200, payload=_ONE_SDK_REGISTRY),
            ):
                with patch("tandem_cli.sdk_commands.subprocess.run", side_effect=fake_run):
                    resolved = sdk_commands.resolve_sdk(None)
                    with self.assertRaises(RuntimeError) as ctx:
                        sdk_commands.install_sdk(resolved, target_python="/fake/python")

        self.assertIn("pip install failed", str(ctx.exception))


class ResolveTargetPythonTests(unittest.TestCase):
    def test_prefers_an_explicit_override(self) -> None:
        result = sdk_commands.resolve_target_python("/explicit/python")
        self.assertEqual(result, "/explicit/python")

    def test_prefers_the_active_virtualenv_over_anything_else(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "myvenv"
            bin_dir = venv_dir / "bin"
            bin_dir.mkdir(parents=True)
            fake_python = bin_dir / "python"
            fake_python.touch()

            with patch.dict(os.environ, {"VIRTUAL_ENV": str(venv_dir)}):
                result = sdk_commands.resolve_target_python(None)

            self.assertEqual(result, str(fake_python))

    def test_falls_back_to_path_when_no_venv_is_active(self) -> None:
        env_without_virtualenv = dict(os.environ)
        env_without_virtualenv.pop("VIRTUAL_ENV", None)
        with patch.dict(os.environ, env_without_virtualenv, clear=True):
            result = sdk_commands.resolve_target_python(None)

        self.assertTrue(result)  # some interpreter was found, one way or another


if __name__ == "__main__":
    unittest.main()
