from __future__ import annotations

import getpass
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import set_key

_REQUEST_TIMEOUT_SECONDS = 30
_DEFAULT_SERVER_URL = "http://127.0.0.1:6767"


@dataclass(frozen=True)
class AuthSession:
    username: str
    api_key: str
    server_url: str
    created_api_key: bool


def resolve_server_url(server_url: str | None) -> str:
    resolved = (
        server_url
        or os.environ.get("TANDEM_SERVER_URL")
        or os.environ.get("SERVER_URL")
        or _DEFAULT_SERVER_URL
    )
    return resolved.rstrip("/")


def prompt_username(username: str | None) -> str:
    resolved = (username or "").strip()
    if resolved:
        return resolved

    try:
        resolved = input("Username: ").strip()
    except EOFError as exc:  # pragma: no cover - depends on terminal state.
        raise ValueError(
            "Could not read a username from stdin. Pass --username or run in an interactive terminal."
        ) from exc

    if not resolved:
        raise ValueError("Username is required.")

    return resolved


def prompt_password(password: str | None, *, confirm: bool = False) -> str:
    if password is not None:
        if not password:
            raise ValueError("Password is required.")
        return password

    try:
        resolved = getpass.getpass("Password: ")
    except EOFError as exc:  # pragma: no cover - depends on terminal state.
        raise ValueError(
            "Could not read a password from stdin. Pass --password or run in an interactive terminal."
        ) from exc

    if not resolved:
        raise ValueError("Password is required.")

    if confirm:
        confirmation = getpass.getpass("Confirm password: ")
        if resolved != confirmation:
            raise ValueError("Passwords did not match.")

    return resolved


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _response_payload(response: requests.Response) -> Any:
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "application/json" in content_type:
        try:
            return response.json()
        except ValueError:
            return response.text.strip()
    return response.text.strip()


def _raise_response_error(response: requests.Response) -> None:
    payload = _response_payload(response)

    if isinstance(payload, dict):
        detail = (
            payload.get("error")
            or payload.get("message")
            or payload.get("detail")
            or str(payload)
        )
    else:
        detail = str(payload) or "request failed"

    raise RuntimeError(
        f"{response.request.method} {response.url} failed with {response.status_code}: {detail}"
    )


def _required_text(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Server response was missing `{field_name}`.")
    return value.strip()


def _required_bool(payload: dict[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise RuntimeError(f"Server response was missing boolean `{field_name}`.")
    return value


def register_user(
    *,
    username: str,
    password: str,
    server_url: str | None = None,
) -> None:
    resolved_server_url = resolve_server_url(server_url)
    response = requests.post(
        f"{resolved_server_url}/api/v1/register",
        json={"username": username, "password": password},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code != 201:
        _raise_response_error(response)


def login_user(
    *,
    username: str,
    password: str,
    server_url: str | None = None,
    rotate_api_key: bool = False,
) -> AuthSession:
    resolved_server_url = resolve_server_url(server_url)
    response = requests.post(
        f"{resolved_server_url}/api/v1/login",
        json={
            "username": username,
            "password": password,
            "rotate_api_key": rotate_api_key,
        },
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        _raise_response_error(response)

    payload = _response_payload(response)
    if not isinstance(payload, dict):
        raise RuntimeError("Login response was not valid JSON.")

    return AuthSession(
        username=_required_text(payload, "username"),
        api_key=_required_text(payload, "api_key"),
        server_url=resolved_server_url,
        created_api_key=_required_bool(payload, "created_api_key"),
    )


def store_auth_session(session: AuthSession, *, env_file: str = ".env") -> Path:
    path = Path(env_file).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()

    if path.exists() and path.is_symlink():
        raise RuntimeError(f"Refusing to write secrets to symlinked env file: {path}")
    if path.exists() and path.is_dir():
        raise RuntimeError(f"Env file path is a directory: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600)

    set_key(str(path), "TANDEM_SERVER_URL", session.server_url, quote_mode="auto")
    set_key(str(path), "TANDEM_API_KEY", session.api_key, quote_mode="auto")

    if os.name == "posix":
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    return path
