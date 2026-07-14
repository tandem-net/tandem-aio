#!/usr/bin/env bash
#
# Installs the `tandem` CLI command without needing to know anything about
# Python packaging. Run this from a checkout of the tandem-aio repo:
#
#   ./install.sh
#
# It sets up its own private Python environment (so it can't clash with
# whatever Python packages you already have), then puts a `tandem` command
# on your PATH. Safe to re-run any time -- it just refreshes things.

# stop immediately if anything fails, so we don't limp along in a broken state
set -euo pipefail

# The repo root is wherever this script lives, so this works whether you run
# it as ./install.sh or bash install.sh from somewhere else.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HOME/.tandem/venv"
BIN_DIR="$HOME/.local/bin"

# 1. This installer only knows how to handle Linux and macOS.
case "$(uname -s)" in
  Linux|Darwin) ;;
  *)
    echo "This installer only supports Linux and macOS."
    echo "On Windows, follow the manual install steps in cli/README.md instead."
    exit 1
    ;;
esac

# 2. Find a Python interpreter new enough for the CLI (3.10+).
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "Could not find Python 3.10 or newer on your PATH."
  echo "Install one, then re-run this script. For example:"
  echo "  macOS:         brew install python@3.12"
  echo "  Ubuntu/Debian: sudo apt install python3.12"
  exit 1
fi

echo "Using $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# 3. Create (or reuse) a private virtual environment just for the CLI, so
# installing it can never conflict with other Python projects on your machine.
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating a private environment at $VENV_DIR..."
  VENV_ERROR_LOG="$(mktemp)"
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR" 2>"$VENV_ERROR_LOG"; then
    if grep -qi "ensurepip is not available" "$VENV_ERROR_LOG"; then
      echo "Your Python is missing the 'venv' module."
      echo "On Ubuntu/Debian, install it with: sudo apt install python3-venv"
    fi
    cat "$VENV_ERROR_LOG"
    rm -f "$VENV_ERROR_LOG"
    exit 1
  fi
  rm -f "$VENV_ERROR_LOG"
else
  echo "Reusing existing environment at $VENV_DIR"
fi

# 4. Install the CLI into that environment. --force-reinstall means re-running
# this script always picks up local changes, even between edits that don't
# bump the version number in cli/pyproject.toml.
"$VENV_DIR/bin/python" -m pip install --upgrade pip --quiet
echo "Installing the tandem CLI..."
"$VENV_DIR/bin/python" -m pip install --force-reinstall "$REPO_ROOT/cli"

# 5. Put the `tandem` command somewhere your shell can find it.
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/tandem" "$BIN_DIR/tandem"

echo ""
echo "Tandem CLI installed."
echo "Linked: $BIN_DIR/tandem -> $VENV_DIR/bin/tandem"
echo ""

# 6. If your server needs a node registration token, save it now so `tandem node
# start` doesn't need it exported by hand every session. We check the
# environment first, then fall back to this repo's own .env file, since that's
# where a local dev server's token normally lives.
REGISTRATION_TOKEN="${TANDEM_NODE_REGISTRATION_TOKEN:-}"
TOKEN_SOURCE="the environment"
if [ -z "$REGISTRATION_TOKEN" ] && [ -f "$REPO_ROOT/.env" ]; then
  REGISTRATION_TOKEN="$(grep -m1 '^TANDEM_NODE_REGISTRATION_TOKEN=' "$REPO_ROOT/.env" | cut -d'=' -f2-)"
  TOKEN_SOURCE="$REPO_ROOT/.env"
fi

if [ -n "$REGISTRATION_TOKEN" ]; then
  "$BIN_DIR/tandem" settings set-registration-token "$REGISTRATION_TOKEN" >/dev/null
  echo "Saved a node registration token from $TOKEN_SOURCE."
  echo "tandem node start will use it automatically -- no export needed."
  echo ""
fi

# 7. Install the compute node. This is the Rust program that actually runs your
# tasks; the CLI starts and stops it for you, but it has to exist on disk first.
# We try hard to make this work no matter what you have installed, and when we
# can't, we point you at exactly what to install rather than failing silently.
# (Set TANDEM_SKIP_NODE=1 to install just the CLI and skip this.)
NODE_SRC_DIR="$REPO_ROOT/node"
NODE_HOME_BIN_DIR="$HOME/.tandem/bin"
NODE_DEST="$NODE_HOME_BIN_DIR/tandem-node"
mkdir -p "$NODE_HOME_BIN_DIR"

install_node_binary() {
  # An explicit prebuilt binary wins. This is what the download-a-release flow
  # feeds in: `TANDEM_NODE_BIN=/path/to/tandem-node ./install.sh`.
  if [ -n "${TANDEM_NODE_BIN:-}" ]; then
    if [ -f "$TANDEM_NODE_BIN" ]; then
      echo "Using the prebuilt node binary at $TANDEM_NODE_BIN"
      install -m 0755 "$TANDEM_NODE_BIN" "$NODE_DEST"
      return 0
    fi
    echo "warning: TANDEM_NODE_BIN is set but '$TANDEM_NODE_BIN' does not exist; ignoring it."
  fi

  # Otherwise build it from the source in this repo, if Rust is available.
  if command -v cargo >/dev/null 2>&1; then
    echo "Building the Tandem node from source (this can take a few minutes the first time)..."
    if cargo build --release --manifest-path "$NODE_SRC_DIR/Cargo.toml"; then
      install -m 0755 "$NODE_SRC_DIR/target/release/tandem-node" "$NODE_DEST"
      return 0
    fi
    echo "warning: building the node failed -- see the cargo output above."
    return 1
  fi

  # No Cargo, but maybe there's already a build lying around from before.
  if [ -f "$NODE_SRC_DIR/target/release/tandem-node" ]; then
    echo "Cargo isn't installed, but found an existing node build -- using it."
    install -m 0755 "$NODE_SRC_DIR/target/release/tandem-node" "$NODE_DEST"
    return 0
  fi

  # Nothing we can do on our own. The caller prints guidance.
  return 2
}

NODE_INSTALLED=0
if [ "${TANDEM_SKIP_NODE:-0}" = "1" ]; then
  echo "Skipping the node install because TANDEM_SKIP_NODE=1."
  echo ""
elif install_node_binary; then
  NODE_INSTALLED=1
  echo "Tandem node installed at $NODE_DEST"
  echo ""
else
  NODE_RC=$?
  echo ""
  if [ "$NODE_RC" = "2" ]; then
    echo "Could not install the Tandem node automatically: Rust (cargo) isn't installed."
  else
    echo "The Tandem node did not build."
  fi
  echo "The CLI itself is installed and works -- you just can't start a node yet."
  echo "Pick whichever is easier for you:"
  echo ""
  echo "  A) Install Rust, then re-run ./install.sh:"
  echo "       curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
  echo "       (see https://rustup.rs -- you may also need a C compiler:"
  echo "        'sudo apt install build-essential' on Debian/Ubuntu, or"
  echo "        'xcode-select --install' on macOS)"
  echo ""
  echo "  B) Download a prebuilt node binary for your platform from the project's"
  echo "     releases, then re-run pointing at it:"
  echo "       TANDEM_NODE_BIN=/path/to/tandem-node ./install.sh"
  echo ""
fi

case ":$PATH:" in
  *":$BIN_DIR:"*)
    echo "Run: tandem --help"
    ;;
  *)
    echo "$BIN_DIR isn't on your PATH yet. Add this line to your shell profile"
    echo "(~/.bashrc, ~/.zshrc, or ~/.profile), then restart your terminal:"
    echo ""
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

# If some other `tandem` is already on PATH ahead of ours, say so -- otherwise
# it'd be confusing why nothing seems to have changed.
if command -v tandem >/dev/null 2>&1; then
  FOUND_AT="$(command -v tandem)"
  if [ "$FOUND_AT" != "$BIN_DIR/tandem" ]; then
    echo ""
    echo "Note: 'tandem' currently resolves to $FOUND_AT, which comes before"
    echo "$BIN_DIR on your PATH. Adjust your PATH order if you want this install to win."
  fi
fi

# A short, friendly "what now?" so people aren't left guessing.
echo ""
echo "Next steps:"
echo "  1. Log in:            tandem auth login"
if [ "$NODE_INSTALLED" = "1" ]; then
  echo "  2. Start your node:   tandem node start        (or run it 24/7: tandem node enable)"
  echo "  3. Check on it:       tandem status"
  echo ""
  echo "Your node needs to be running before you can deploy or start a job."
else
  echo "  2. Install the node (see the note above), then: tandem node start"
fi
