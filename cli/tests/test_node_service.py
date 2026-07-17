from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tandem_cli import commands, node_paths, node_service


def _isolate_node_home(test_case: unittest.TestCase, tmpdir: str) -> Path:
    """Point the node home + bin dir at a throwaway temp dir so tests never touch
    the real ~/.tandem/node on the machine running them. Mirrors the credentials
    isolation the auth tests use."""
    node_home = Path(tmpdir) / "node"
    bin_dir = Path(tmpdir) / "bin"
    node_home.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)

    patchers = [
        patch.object(node_paths, "NODE_HOME", node_home),
        patch.object(node_paths, "BIN_DIR", bin_dir),
        patch.object(node_service, "NODE_HOME", node_home),
    ]
    for patcher in patchers:
        patcher.start()
        test_case.addCleanup(patcher.stop)
    return node_home


class NodePathsTests(unittest.TestCase):
    def test_binary_name_mentions_tandem_node(self) -> None:
        self.assertIn("tandem-node", node_paths.binary_name())

    def test_explicit_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "custom-node"
            fake.write_text("#!/bin/sh\n")
            with patch.dict(os.environ, {"TANDEM_NODE_BIN": str(fake)}):
                self.assertEqual(node_paths.find_node_binary(), fake)

    def test_override_pointing_nowhere_is_not_used(self) -> None:
        with patch.dict(os.environ, {"TANDEM_NODE_BIN": "/definitely/not/here"}):
            self.assertIsNone(node_paths.find_node_binary())


class NodeIdentityTests(unittest.TestCase):
    def test_not_registered_without_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            self.assertFalse(node_service.is_registered())

    def test_load_identity_reads_the_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = _isolate_node_home(self, tmp)
            (home / "node.json").write_text(
                json.dumps({"node_id": "node_abc", "server_url": "http://x"})
            )
            self.assertTrue(node_service.is_registered())
            self.assertEqual(node_service.load_identity()["node_id"], "node_abc")

    def test_clean_node_error_pulls_out_the_fatal_line(self) -> None:
        stderr = "[node] server_url = x\n[node] FATAL: registration failed — boom\n"
        message = node_service._clean_node_error(stderr)
        self.assertIn("boom", message)
        self.assertNotIn("FATAL", message)

    def test_register_now_success_reports_the_node_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = _isolate_node_home(self, tmp)

            def fake_run(_cmd, **_kwargs):
                # Simulate the node registering and saving its identity.
                (home / "node.json").write_text(json.dumps({"node_id": "node_new"}))
                result = MagicMock()
                result.returncode = 0
                result.stdout = "TANDEM_NODE_ID=node_new\n"
                result.stderr = ""
                return result

            with patch.object(node_service, "find_node_binary", return_value=Path("/fake/tandem-node")):
                with patch.object(node_service.subprocess, "run", side_effect=fake_run):
                    result = node_service.register_node_now("http://server")

            self.assertTrue(result.ok)
            self.assertEqual(result.node_id, "node_new")

    def test_register_now_failure_returns_a_clean_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            failed = MagicMock()
            failed.returncode = 1
            failed.stdout = ""
            failed.stderr = "[node] FATAL: registration failed — nope\n"

            with patch.object(node_service, "find_node_binary", return_value=Path("/fake/tandem-node")):
                with patch.object(node_service.subprocess, "run", return_value=failed):
                    result = node_service.register_node_now("http://server")

            self.assertFalse(result.ok)
            self.assertIn("nope", result.message)

    def test_register_now_without_a_binary_explains_how_to_get_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            with patch.object(node_service, "find_node_binary", return_value=None):
                result = node_service.register_node_now("http://server")
            self.assertFalse(result.ok)
            self.assertIn("tandem-node", result.message)


class RegistrationTokenResolutionTests(unittest.TestCase):
    """A saved `tandem settings set-registration-token` setting should mean you
    never have to export TANDEM_NODE_REGISTRATION_TOKEN by hand again -- these
    pin down the fallback order and that it actually reaches the node process."""

    def test_no_token_anywhere_resolves_to_empty(self) -> None:
        with patch.object(node_service, "get_stored_registration_token", return_value=None):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TANDEM_NODE_REGISTRATION_TOKEN", None)
                self.assertEqual(node_service.resolve_registration_token(), "")

    def test_env_var_is_used_when_nothing_is_saved(self) -> None:
        with patch.object(node_service, "get_stored_registration_token", return_value=None):
            with patch.dict(os.environ, {"TANDEM_NODE_REGISTRATION_TOKEN": "from-env"}):
                self.assertEqual(node_service.resolve_registration_token(), "from-env")

    def test_saved_setting_wins_over_the_env_var(self) -> None:
        with patch.object(node_service, "get_stored_registration_token", return_value="from-settings"):
            with patch.dict(os.environ, {"TANDEM_NODE_REGISTRATION_TOKEN": "from-env"}):
                self.assertEqual(node_service.resolve_registration_token(), "from-settings")

    def test_build_node_env_carries_the_resolved_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            with patch.object(node_service, "get_stored_registration_token", return_value="from-settings"):
                env = node_service.build_node_env("http://server")
            self.assertEqual(env["TANDEM_NODE_REGISTRATION_TOKEN"], "from-settings")

    def test_build_node_env_omits_the_key_when_no_token_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            with patch.object(node_service, "get_stored_registration_token", return_value=None):
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("TANDEM_NODE_REGISTRATION_TOKEN", None)
                    env = node_service.build_node_env("http://server")
            self.assertNotIn("TANDEM_NODE_REGISTRATION_TOKEN", env)


class RegistrationAuthTokenTests(unittest.TestCase):
    """register_node_now passes the saved API key as TANDEM_NODE_AUTH_TOKEN."""

    def _capture_register_env(self, *, api_key, registration_token) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            home = _isolate_node_home(self, tmp)
            captured: dict = {}

            def fake_run(_cmd, **kwargs):
                captured.update(kwargs.get("env") or {})
                (home / "node.json").write_text(json.dumps({"node_id": "node_new"}))
                result = MagicMock()
                result.returncode = 0
                result.stdout = ""
                result.stderr = ""
                return result

            with patch.object(node_service, "get_api_key", return_value=api_key), \
                    patch.object(node_service, "get_stored_registration_token", return_value=registration_token), \
                    patch.dict(os.environ, {}, clear=False), \
                    patch.object(node_service, "find_node_binary", return_value=Path("/fake/tandem-node")), \
                    patch.object(node_service.subprocess, "run", side_effect=fake_run):
                os.environ.pop("TANDEM_NODE_REGISTRATION_TOKEN", None)
                result = node_service.register_node_now("http://server")

            self.assertTrue(result.ok)
            return captured

    def test_logged_in_sends_the_api_key_as_the_auth_token(self) -> None:
        env = self._capture_register_env(api_key="user-api-key", registration_token=None)
        self.assertEqual(env.get("TANDEM_NODE_AUTH_TOKEN"), "user-api-key")

    def test_not_logged_in_sends_no_auth_token(self) -> None:
        env = self._capture_register_env(api_key=None, registration_token=None)
        self.assertNotIn("TANDEM_NODE_AUTH_TOKEN", env)

    def test_shared_token_still_flows_for_headless_nodes(self) -> None:
        env = self._capture_register_env(api_key=None, registration_token="shared-token")
        self.assertEqual(env.get("TANDEM_NODE_REGISTRATION_TOKEN"), "shared-token")
        self.assertNotIn("TANDEM_NODE_AUTH_TOKEN", env)


class NodeProcessTests(unittest.TestCase):
    def test_pid_file_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            node_service._write_pid(4242)
            self.assertEqual(node_service._read_pid(), 4242)
            node_service._clear_pid()
            self.assertIsNone(node_service._read_pid())

    def test_pid_alive_true_for_this_process(self) -> None:
        self.assertTrue(node_service._pid_alive(os.getpid()))

    def test_pid_alive_false_for_a_bogus_pid(self) -> None:
        self.assertFalse(node_service._pid_alive(2_000_000_000))

    def test_daemon_not_running_without_a_pid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            self.assertFalse(node_service._daemon_running())

    def test_daemon_running_guards_against_pid_reuse(self) -> None:
        # Our own pid is alive but it isn't the node binary. On Linux the /proc
        # check should catch that and report the daemon as not running.
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            node_service._write_pid(os.getpid())
            if Path("/proc").exists():
                self.assertFalse(node_service._daemon_running())


class NodeStatusTests(unittest.TestCase):
    def test_status_is_stopped_and_none_when_nothing_set_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _isolate_node_home(self, tmp)
            with patch.object(node_service, "_service_kind", return_value=None):
                status = node_service.get_status()
            self.assertFalse(status.running)
            self.assertEqual(status.backend, "none")

    def test_status_surfaces_saved_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = _isolate_node_home(self, tmp)
            (home / "node.json").write_text(
                json.dumps({"node_id": "node_x", "server_url": "http://s", "registered_at": 123})
            )
            with patch.object(node_service, "_service_kind", return_value=None):
                status = node_service.get_status()
            self.assertEqual(status.node_id, "node_x")
            self.assertEqual(status.server_url, "http://s")

    def test_tail_log_returns_the_last_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = _isolate_node_home(self, tmp)
            (home / "node.log").write_text("\n".join(f"line{i}" for i in range(100)))
            out = node_service.tail_log(5)
            self.assertIn("line95", out)
            self.assertNotIn("line94", out)


class DeployStartLockTests(unittest.TestCase):
    def _run(self, argv: list[str], env: dict[str, str] | None = None) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with patch.dict(os.environ, env or {}):
                    with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                        exit_code = commands.main(argv)
            finally:
                os.chdir(previous_cwd)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_deploy_is_blocked_when_the_node_is_stopped(self) -> None:
        with patch.object(commands, "node_is_running", return_value=False):
            exit_code, _out, err = self._run(["deploy"])
        self.assertEqual(exit_code, 1)
        self.assertIn("node isn't running", err)

    def test_start_is_blocked_when_the_node_is_stopped(self) -> None:
        with patch.object(commands, "node_is_running", return_value=False):
            exit_code, _out, err = self._run(["start"])
        self.assertEqual(exit_code, 1)
        self.assertIn("node isn't running", err)

    def test_skip_env_var_bypasses_the_lock(self) -> None:
        # With the escape hatch set, we should get past the lock and fail later on
        # the missing project config instead.
        with patch.object(commands, "node_is_running", return_value=False):
            _exit_code, _out, err = self._run(["deploy"], env={"TANDEM_SKIP_NODE_CHECK": "1"})
        self.assertNotIn("node isn't running", err)
        self.assertIn("config", err.lower())


if __name__ == "__main__":
    unittest.main()
