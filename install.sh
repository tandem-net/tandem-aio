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
