"""Tearing Tandem back off a machine.

`tandem uninstall` undoes what the installers did: it stops the node and any 24/7
service, clears your saved login, removes the `tandem` command, and deletes the
~/.tandem folder (the private Python environment, the node binary, and node state).

The tricky part is that the command is running *from* the environment it's trying
to delete -- `tandem` lives in ~/.tandem/venv. So for that one folder we hand the
removal off to a short detached process that runs a moment after we exit. On
Windows this is required (you can't delete files that are in use); everywhere else
it just keeps things clean and predictable.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import node_paths, node_service
from .auth import clear_auth_session


def _tandem_root() -> Path:
    """The ~/.tandem folder that holds the venv, the node binary, and node state."""
    return node_paths.NODE_HOME.parent


def _posix_launcher() -> Path:
    """The `tandem` symlink install.sh drops on PATH (Linux/macOS)."""
    return Path.home() / ".local" / "bin" / "tandem"


def _windows_launcher() -> Path:
    """The tandem.bat wrapper install.bat drops on PATH (Windows)."""
    return node_paths.BIN_DIR / "tandem.bat"


def _running_from(root: Path) -> bool:
    """Are we executing from inside `root`? If so we can't delete it out from under
    ourselves, so the caller defers that removal to a detached process."""
    try:
        return Path(sys.executable).resolve().is_relative_to(root.resolve())
    except (ValueError, OSError):
        return False


def _schedule_root_removal(root: Path) -> None:
    """Delete `root` from a detached process that runs just after this one exits."""
    if os.name == "nt":
        # `ping` is a dependency-free way to wait ~2s for us to exit before the
        # rmdir, so the venv's files are no longer locked.
        command = f'ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{root}"'
        subprocess.Popen(
            ["cmd", "/c", command],
            creationflags=0x00000008 | 0x00000200,  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            close_fds=True,
        )
    else:
        command = f"sleep 1; rm -rf {shlex.quote(str(root))}"
        subprocess.Popen(
            ["/bin/sh", "-c", command],
            start_new_session=True,
            close_fds=True,
        )


def perform_uninstall() -> list[str]:
    """Remove everything Tandem put on this machine. Returns a list of short,
    human-readable notes about what happened, which the CLI prints back."""
    steps: list[str] = []

    # 1. Stop the node and tear down any 24/7 service so nothing is left running.
    try:
        if node_service.active_backend() in ("systemd", "launchd"):
            node_service.disable_service()
            steps.append("turned off the 24/7 service")
    except Exception as exc:
        steps.append(f"warning: could not turn off the service ({exc})")

    try:
        if node_service.stop_node():
            steps.append("stopped the node")
    except Exception as exc:
        steps.append(f"warning: could not stop the node ({exc})")

    # 2. Clear the saved login (OS keyring plus the fallback file).
    try:
        clear_auth_session()
        steps.append("cleared your saved login")
    except Exception as exc:
        steps.append(f"warning: could not clear your saved login ({exc})")

    # 3. Remove the `tandem` launcher on PATH. The POSIX one lives outside
    # ~/.tandem, so it has to go separately.
    for launcher in (_posix_launcher(), _windows_launcher()):
        try:
            if launcher.is_symlink() or launcher.exists():
                launcher.unlink()
                steps.append(f"removed {launcher}")
        except OSError as exc:
            steps.append(f"warning: could not remove {launcher} ({exc})")

    # 4. Remove ~/.tandem itself. If we're running from inside it (the normal
    # case), defer that to a detached process; otherwise just delete it now.
    root = _tandem_root()
    if root.exists():
        if _running_from(root):
            _schedule_root_removal(root)
            steps.append(f"scheduled removal of {root} (finishes a moment after this exits)")
        else:
            shutil.rmtree(root, ignore_errors=True)
            steps.append(f"removed {root}")

    return steps
