"""Where the Tandem node lives on disk, and how the CLI finds its binary.

Everything the node needs at rest -- its saved identity, its private key, the
pid of the running process, and its log -- lives under ~/.tandem/node, right
next to the CLI's own ~/.tandem/venv and ~/.tandem/credentials.json. Keeping it
all in one predictable place is what lets the CLI manage "the node on this
machine" without the user having to track files themselves.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# The home for everything node-related. The CLI installer (install.sh) drops the
# compiled binary under ~/.tandem/bin, so both live under the same ~/.tandem root.
_TANDEM_ROOT = Path.home() / ".tandem"
NODE_HOME = _TANDEM_ROOT / "node"
BIN_DIR = _TANDEM_ROOT / "bin"


def binary_name() -> str:
    """The node executable's filename, including the .exe suffix on Windows."""
    return "tandem-node.exe" if os.name == "nt" else "tandem-node"


def ensure_home() -> Path:
    """Create ~/.tandem/node if it isn't there yet and return it."""
    NODE_HOME.mkdir(parents=True, exist_ok=True)
    return NODE_HOME


def state_file() -> Path:
    """The saved node identity (node_id, node_token, server_url)."""
    return NODE_HOME / "node.json"


def private_key_file() -> Path:
    """The node's RSA private key, used to sign execution receipts."""
    return NODE_HOME / "node_key.pem"


def pid_file() -> Path:
    """Holds the pid of the running background node process."""
    return NODE_HOME / "node.pid"


def log_file() -> Path:
    """Where the background node's stdout and stderr are captured."""
    return NODE_HOME / "node.log"


def installed_binary() -> Path:
    """Where install.sh puts the binary. May not exist yet."""
    return BIN_DIR / binary_name()


def _repo_dev_binary() -> Path | None:
    """When you're running the CLI straight from a source checkout, use the
    binary that `cargo build --release` produced under node/target/release. This
    is purely a developer convenience -- an installed CLI won't find anything
    here and falls through to the other lookups."""
    here = Path(__file__).resolve()
    # cli/node_paths.py -> parents[1] is the repo root in a source checkout.
    candidates = []
    if len(here.parents) >= 2:
        candidates.append(here.parents[1] / "node" / "target" / "release" / binary_name())
    candidates.append(Path.cwd() / "node" / "target" / "release" / binary_name())
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_node_binary() -> Path | None:
    """Locate the node executable, or None if it isn't installed anywhere yet.

    Order of preference:
      1. TANDEM_NODE_BIN, an explicit override (used by the release/download flow)
      2. the installed copy under ~/.tandem/bin
      3. a release build in the local repo (developer convenience)
      4. anything named tandem-node already on PATH
    """
    override = os.environ.get("TANDEM_NODE_BIN")
    if override:
        candidate = Path(override).expanduser()
        return candidate if candidate.exists() else None

    installed = installed_binary()
    if installed.exists():
        return installed

    dev = _repo_dev_binary()
    if dev is not None:
        return dev

    on_path = shutil.which(binary_name())
    return Path(on_path) if on_path else None
