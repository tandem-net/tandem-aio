from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from tandem_cli import app_config, commands, remote


class ResolveApiKeyTests(unittest.TestCase):
    """`tandem auth login` stores the API key in the keyring, but deploy/start
    never read it back -- login looked like it worked and then every deploy
    still demanded --api-key. These pin down the fallback chain."""

    def test_explicit_argument_wins_over_everything(self) -> None:
        with patch.object(remote, "get_api_key", return_value="from-keyring"):
            with patch.dict("os.environ", {"TANDEM_API_KEY": "from-env"}):
                self.assertEqual(remote._resolve_api_key("from-flag"), "from-flag")

    def test_env_var_wins_over_the_stored_session(self) -> None:
        with patch.object(remote, "get_api_key", return_value="from-keyring"):
            with patch.dict("os.environ", {"TANDEM_API_KEY": "from-env"}):
                self.assertEqual(remote._resolve_api_key(None), "from-env")

    def test_falls_back_to_the_logged_in_session(self) -> None:
        with patch.object(remote, "get_api_key", return_value="from-keyring"):
            with patch.dict("os.environ", {}, clear=False):
                os.environ.pop("TANDEM_API_KEY", None)
                self.assertEqual(remote._resolve_api_key(None), "from-keyring")

    def test_nothing_available_raises_with_the_login_command(self) -> None:
        with patch.object(remote, "get_api_key", return_value=None):
            with patch.dict("os.environ", {}, clear=False):
                os.environ.pop("TANDEM_API_KEY", None)
                with self.assertRaises(RuntimeError) as ctx:
                    remote._resolve_api_key(None)
        self.assertIn("tandem auth login", str(ctx.exception))


class ConnectionErrorTranslationTests(unittest.TestCase):
    """A closed/unreachable server used to surface as a raw urllib3 traceback
    through main()'s catch-all. These confirm the friendly translation fires
    for whichever command hits it, without needing a real server."""

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = commands.main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_connection_error_becomes_a_friendly_message(self) -> None:
        request = requests.PreparedRequest()
        request.url = "http://127.0.0.1:6767/deploy/"
        boom = requests.exceptions.ConnectionError("refused", request=request)

        with patch.object(commands, "_cmd_deploy", side_effect=boom):
            exit_code, _, stderr = self._run(["deploy", "tandem.toml"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Couldn't reach the Tandem server", stderr)
        self.assertIn("http://127.0.0.1:6767/deploy/", stderr)
        self.assertIn("tandem settings show", stderr)

    def test_timeout_becomes_a_friendly_message(self) -> None:
        with patch.object(commands, "_cmd_deploy", side_effect=requests.exceptions.Timeout("slow")):
            exit_code, _, stderr = self._run(["deploy", "tandem.toml"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Timed out waiting for the Tandem server", stderr)


class RegistrationFailureHintTests(unittest.TestCase):
    def test_missing_token_message_leads_with_login(self) -> None:
        hint = commands._registration_failure_hint(
            'registration failed (401 Unauthorized): {"error":"Missing node registration bearer token"}'
        )
        self.assertIsNotNone(hint)
        # Login comes first, the token fallback second.
        self.assertIn("tandem auth login", hint)
        self.assertLess(hint.index("tandem auth login"), hint.index("set-registration-token"))
        self.assertIn("tandem settings set-registration-token", hint)

    def test_invalid_token_message_gets_a_hint(self) -> None:
        hint = commands._registration_failure_hint(
            'registration failed (403 Forbidden): {"error":"Invalid node registration token"}'
        )
        self.assertIsNotNone(hint)
        self.assertIn("tandem auth login", hint)

    def test_unrelated_failure_gets_no_hint(self) -> None:
        hint = commands._registration_failure_hint("Registration timed out talking to the server.")
        self.assertIsNone(hint)


class ProjectConfigErrorMessageTests(unittest.TestCase):
    def test_missing_file_suggests_tandem_init(self) -> None:
        with self.assertRaises(FileNotFoundError) as ctx:
            app_config.load_project_config("/definitely/not/a/real/path/tandem.toml")
        self.assertIn("tandem init", str(ctx.exception))

    def test_invalid_toml_names_the_file_and_the_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_config = Path(tmpdir) / "tandem.toml"
            bad_config.write_text("[project\nname = broken\n", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                app_config.load_project_config(bad_config)

        self.assertIn(str(bad_config), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
