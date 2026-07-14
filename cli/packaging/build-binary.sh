#!/usr/bin/env bash
#
# Turn the Tandem Python CLI into a single self-contained executable.
#
#   cli/packaging/build-binary.sh
#
# Produces cli/packaging/dist/tandem -- one file that runs `tandem` with no
# Python, no virtualenv, and no pip install needed on the target machine. That's
# the whole point: the node is already a single Rust binary, and this makes the
# CLI a single binary too, so both can be dropped straight into /usr/bin by the
# installers (see ../../packaging/build-deb.sh).
#
# We do this with PyInstaller, which walks the CLI's imports, bundles them plus a
# Python interpreter, and glues it all into one executable for whatever OS you
# run this on (Linux here, macOS on a Mac, Windows on Windows).

set -euo pipefail

# Where things live. This script sits in cli/packaging, so the cli/ package is
# one directory up and the repo root is two up.
PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd "$PACKAGING_DIR/.." && pwd)"
DIST_DIR="$PACKAGING_DIR/dist"

# 1. Find a Python new enough to build with (3.10+), the same way install.sh does.
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
  echo "Could not find Python 3.10 or newer to build the CLI binary."
  echo "Install one and re-run, e.g. 'sudo apt install python3.12' on Debian/Ubuntu."
  exit 1
fi

echo "Building the tandem CLI binary with $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# 2. Do the whole build inside a throwaway virtualenv so we never touch the
# system Python or leave anything behind. Everything below lives under here and
# gets deleted on exit, no matter how the script ends.
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
VENV_DIR="$WORK_DIR/venv"

"$PYTHON_BIN" -m venv "$VENV_DIR"
VENV_PY="$VENV_DIR/bin/python"
"$VENV_PY" -m pip install --upgrade pip --quiet

# 3. Install PyInstaller plus the libraries the CLI actually imports at runtime.
#
# These mirror the dependencies in cli/pyproject.toml, with one deliberate
# exception: py2wasm. The CLI never imports py2wasm -- it runs it as a separate
# `py2wasm` command (see cli/wasm.py), so it's a build tool the user installs
# alongside the CLI, not something that belongs baked inside this binary. Leaving
# it out keeps the binary small. If this list ever falls out of sync with
# pyproject.toml, the smoke test in step 6 will fail the build and tell us.
echo "Installing PyInstaller and the CLI's runtime dependencies..."
"$VENV_PY" -m pip install --quiet \
  pyinstaller \
  requests \
  python-dotenv \
  keyring \
  "tomli>=2.0"

# Install the CLI package itself, but without its dependencies (--no-deps) so pip
# doesn't drag py2wasm back in. We just handled the deps we want above.
"$VENV_PY" -m pip install --quiet --no-deps "$CLI_DIR"

# 4. Give PyInstaller a tiny entry script to start from. It does exactly what the
# installed `tandem` command does: call the CLI's main().
ENTRY="$WORK_DIR/entry_tandem.py"
cat > "$ENTRY" <<'ENTRY_PY'
from tandem_cli.commands import main
import sys

if __name__ == "__main__":
    sys.exit(main())
ENTRY_PY

# 5. Bundle it all into one file.
#   --collect-all tandem_cli  pulls in every CLI submodule plus data files like
#                             dummy.wasm and the bundled SDK.
#   --collect-all keyring     pulls in keyring and its OS backends, which it
#                             loads dynamically (so PyInstaller can't see them
#                             just by following imports).
echo "Bundling the binary with PyInstaller (this takes a minute)..."
"$VENV_PY" -m PyInstaller \
  --onefile \
  --name tandem \
  --collect-all tandem_cli \
  --collect-all keyring \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR/build" \
  --specpath "$WORK_DIR" \
  --clean --noconfirm \
  "$ENTRY"

# 6. Prove the binary actually runs before we call it done. This catches a whole
# class of packaging mistakes (a missing dependency, a backend that didn't get
# bundled) right here instead of on the user's machine.
BINARY="$DIST_DIR/tandem"
echo ""
echo "Smoke-testing the binary..."
if ! "$BINARY" -h >/dev/null 2>&1; then
  echo "The built binary failed to run 'tandem -h'. Something didn't bundle correctly."
  exit 1
fi

echo "Built $BINARY"
