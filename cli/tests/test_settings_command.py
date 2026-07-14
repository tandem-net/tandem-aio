from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tandem_cli import commands, remote
from tandem_cli.auth import (
    clear_stored_registration_token,
    clear_stored_server_url,
    get_stored_registration_token,
    get_stored_server_url,
    set_stored_registration_token,
    set_stored_server_url,
)


def _use_isolated_credentials_file(test_case: unittest.TestCase, tmpdir: str) -> None:
    """Point the CLI's keyring fallback at a throwaway file so tests never touch
    the real ~/.tandem/credentials.json on the machine running them."""
    fake_path = Path(tmpdir) / "credentials.json"
    patcher_available = patch("tandem_cli.auth._keyring_available", return_value=False)
    patcher_path = patch("tandem_cli.auth._FALLBACK_CREDS_PATH", fake_path)
    patcher_available.start()
    patcher_path.start()
    test_case.addCleanup(patcher_available.stop)
    test_case.addCleanup(patcher_path.stop)


class StoredServerUrlTests(unittest.TestCase):
    def test_set_then_get_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            normalized = set_stored_server_url("http://example.com:9000/")
            self.assertEqual(normalized, "http://example.com:9000")
            self.assertEqual(get_stored_server_url(), "http://example.com:9000")

    def test_rejects_a_url_without_a_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            with self.assertRaises(ValueError):
                set_stored_server_url("example.com")

    def test_rejects_an_empty_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            with self.assertRaises(ValueError):
                set_stored_server_url("   ")

    def test_clear_removes_the_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            set_stored_server_url("http://example.com")
            clear_stored_server_url()
            self.assertIsNone(get_stored_server_url())


class StoredRegistrationTokenTests(unittest.TestCase):
    def test_set_then_get_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            normalized = set_stored_registration_token("  meow-secret  ")
            self.assertEqual(normalized, "meow-secret")
            self.assertEqual(get_stored_registration_token(), "meow-secret")

    def test_rejects_an_empty_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            with self.assertRaises(ValueError):
                set_stored_registration_token("   ")

    def test_clear_removes_the_saved_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            set_stored_registration_token("meow-secret")
            clear_stored_registration_token()
            self.assertIsNone(get_stored_registration_token())


class SettingsCommandTests(unittest.TestCase):
    def _run_in_empty_project_dir(self, argv: list[str]) -> tuple[int, str, str]:
        """Run commands.main() from a tempdir with no .env file, so
        TANDEM_SERVER_URL/SERVER_URL/TANDEM_NODE_REGISTRATION_TOKEN can't sneak
        in from the repo's own .env.

        Restores the cwd before the tempdir is removed -- a test method may
        call this more than once, and addCleanup alone wouldn't restore the
        cwd until the whole test finishes, leaving it pointed at a deleted
        directory in between calls.
        """
        stdout, stderr = io.StringIO(), io.StringIO()
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                excluded_keys = ("TANDEM_SERVER_URL", "SERVER_URL", "TANDEM_NODE_REGISTRATION_TOKEN")
                env_without_server_url = {
                    k: v for k, v in os.environ.items() if k not in excluded_keys
                }
                with patch.dict(os.environ, env_without_server_url, clear=True):
                    with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                        exit_code = commands.main(argv)
            finally:
                os.chdir(previous_cwd)

        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_show_with_nothing_set_explains_the_split_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)
            exit_code, output, _ = self._run_in_empty_project_dir(["settings", "show"])

        self.assertEqual(exit_code, 0)
        self.assertIn("tandem.wnusair.org", output)
        self.assertIn("127.0.0.1:6767", output)

    def test_set_then_show_reports_the_saved_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            set_exit, set_output, _ = self._run_in_empty_project_dir(
                ["settings", "set-server-url", "http://staging.example.com:9000"]
            )
            show_exit, show_output, _ = self._run_in_empty_project_dir(["settings", "show"])

        self.assertEqual(set_exit, 0)
        self.assertIn("http://staging.example.com:9000", set_output)
        self.assertEqual(show_exit, 0)
        self.assertIn("http://staging.example.com:9000", show_output)
        self.assertIn("saved setting", show_output)

    def test_set_rejects_an_invalid_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)
            exit_code, _, stderr_output = self._run_in_empty_project_dir(
                ["settings", "set-server-url", "not-a-url"]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("must start with", stderr_output)

    def test_reset_reverts_to_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            self._run_in_empty_project_dir(["settings", "set-server-url", "http://example.com"])
            reset_exit, reset_output, _ = self._run_in_empty_project_dir(
                ["settings", "reset-server-url"]
            )
            show_exit, show_output, _ = self._run_in_empty_project_dir(["settings", "show"])

        self.assertEqual(reset_exit, 0)
        self.assertIn("Cleared", reset_output)
        self.assertEqual(show_exit, 0)
        self.assertNotIn("http://example.com", show_output)
        self.assertIn("built-in default", show_output)

    def test_show_with_no_registration_token_explains_how_to_set_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)
            exit_code, output, _ = self._run_in_empty_project_dir(["settings", "show"])

        self.assertEqual(exit_code, 0)
        self.assertIn("No node registration token saved", output)
        self.assertIn("tandem settings set-registration-token", output)

    def test_set_then_show_reports_the_saved_registration_token_masked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            set_exit, set_output, _ = self._run_in_empty_project_dir(
                ["settings", "set-registration-token", "meow-secret-value"]
            )
            show_exit, show_output, _ = self._run_in_empty_project_dir(["settings", "show"])

        self.assertEqual(set_exit, 0)
        self.assertEqual(show_exit, 0)
        # The raw token never gets printed back out, only a masked form.
        self.assertNotIn("meow-secret-value", set_output)
        self.assertNotIn("meow-secret-value", show_output)
        self.assertIn("saved setting", show_output)

    def test_set_registration_token_rejects_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)
            exit_code, _, stderr_output = self._run_in_empty_project_dir(
                ["settings", "set-registration-token", "   "]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("cannot be empty", stderr_output)

    def test_reset_registration_token_reverts_to_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _use_isolated_credentials_file(self, tmpdir)

            self._run_in_empty_project_dir(["settings", "set-registration-token", "meow-secret"])
            reset_exit, reset_output, _ = self._run_in_empty_project_dir(
                ["settings", "reset-registration-token"]
            )
            show_exit, show_output, _ = self._run_in_empty_project_dir(["settings", "show"])

        self.assertEqual(reset_exit, 0)
        self.assertIn("Cleared", reset_output)
        self.assertEqual(show_exit, 0)
        self.assertIn("No node registration token saved", show_output)


class RemoteResolverHonorsStoredUrlTests(unittest.TestCase):
    def test_deploy_and_start_pick_up_the_same_saved_override(self) -> None:
        """The settings command would be broken in half the CLI if deploy/start
        kept using their own resolver without checking the saved override too."""
        with patch("tandem_cli.remote.get_stored_server_url", return_value="http://saved-server:4242"):
            self.assertEqual(remote._resolve_server_url(None), "http://saved-server:4242")

    def test_an_explicit_flag_still_wins_over_the_saved_override(self) -> None:
        with patch("tandem_cli.remote.get_stored_server_url", return_value="http://saved-server:4242"):
            self.assertEqual(
                remote._resolve_server_url("http://explicit-flag:5000"),
                "http://explicit-flag:5000",
            )


if __name__ == "__main__":
    unittest.main()
