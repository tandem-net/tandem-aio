from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tandem_cli import commands


class _FakeRequest:
    def __init__(self, method: str) -> None:
        self.method = method


class _FakeResponse:
    def __init__(
        self, *, status_code: int, payload: dict[str, object], url: str
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.url = url
        self.headers = {"Content-Type": "application/json"}
        self.text = json.dumps(payload)
        self.request = _FakeRequest("POST")

    def json(self) -> dict[str, object]:
        return self._payload


class AuthCommandTests(unittest.TestCase):
    def test_auth_register_stores_credentials_in_env_file(self) -> None:
        stdout = io.StringIO()

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = Path.cwd()
            os.chdir(tmpdir)
            self.addCleanup(os.chdir, previous_cwd)

            responses = [
                _FakeResponse(
                    status_code=201,
                    payload={"status": "success"},
                    url="http://127.0.0.1:6767/api/v1/register",
                ),
                _FakeResponse(
                    status_code=200,
                    payload={
                        "status": "success",
                        "message": "authenticated successfully",
                        "username": "demo",
                        "api_key": "abcd1234efgh5678",
                        "created_api_key": True,
                    },
                    url="http://127.0.0.1:6767/api/v1/login",
                ),
            ]

            def fake_post(url: str, json: dict[str, object], timeout: int):
                self.assertEqual(timeout, 30)
                response = responses.pop(0)
                self.assertEqual(url, response.url)
                return response

            with patch("tandem_cli.auth.requests.post", side_effect=fake_post):
                with patch(
                    "tandem_cli.auth.getpass.getpass",
                    side_effect=["demo-pass", "demo-pass"],
                ):
                    with patch("sys.stdout", stdout):
                        exit_code = commands.main(
                            [
                                "auth",
                                "register",
                                "--username",
                                "demo",
                                "--server-url",
                                "http://127.0.0.1:6767",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            env_path = Path(tmpdir) / ".env"
            self.assertTrue(env_path.exists())
            content = env_path.read_text(encoding="utf-8")
            self.assertIn("TANDEM_SERVER_URL='http://127.0.0.1:6767'", content)
            self.assertIn("TANDEM_API_KEY=abcd1234efgh5678", content)

            output = stdout.getvalue()
            self.assertIn("Registered user: demo", output)
            self.assertIn("Stored TANDEM_SERVER_URL and TANDEM_API_KEY", output)
            self.assertIn("abcd...5678", output)

    def test_auth_login_no_store_prints_full_api_key(self) -> None:
        stdout = io.StringIO()

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_cwd = Path.cwd()
            os.chdir(tmpdir)
            self.addCleanup(os.chdir, previous_cwd)

            captured_payloads: list[dict[str, object]] = []

            def fake_post(url: str, json: dict[str, object], timeout: int):
                self.assertEqual(url, "http://127.0.0.1:6767/api/v1/login")
                self.assertEqual(timeout, 30)
                captured_payloads.append(json)
                return _FakeResponse(
                    status_code=200,
                    payload={
                        "status": "success",
                        "message": "authenticated successfully",
                        "username": "demo",
                        "api_key": "full-visible-key",
                        "created_api_key": True,
                    },
                    url=url,
                )

            with patch("tandem_cli.auth.requests.post", side_effect=fake_post):
                with patch("tandem_cli.auth.getpass.getpass", return_value="demo-pass"):
                    with patch("sys.stdout", stdout):
                        exit_code = commands.main(
                            [
                                "auth",
                                "login",
                                "--username",
                                "demo",
                                "--server-url",
                                "http://127.0.0.1:6767",
                                "--rotate-api-key",
                                "--no-store",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            self.assertFalse((Path(tmpdir) / ".env").exists())
            self.assertEqual(
                captured_payloads,
                [
                    {
                        "username": "demo",
                        "password": "demo-pass",
                        "rotate_api_key": True,
                    }
                ],
            )

            output = stdout.getvalue()
            self.assertIn("Authenticated user: demo", output)
            self.assertIn("Credentials were not written to disk.", output)
            self.assertIn("API key: full-visible-key", output)


if __name__ == "__main__":
    unittest.main()
