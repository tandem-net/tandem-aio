#!/usr/bin/env bash
#
# Build the macOS disk image (.dmg) for Tandem.
#
#   packaging/build-dmg.sh
#
# Produces packaging/dist/tandem-macos-<arch>.dmg, then immediately mounts it
# and runs its Install.command for you, so one run of this script leaves you
# with a working `tandem` command on PATH -- the same end result install.sh
# gives someone running from a checkout. (Install.command uses sudo to copy
# into /usr/local/bin, so you'll be asked for your password.)
#
# The image itself holds all three Tandem binaries -- tandem, tandem-node, and
# tandem-compile -- plus that double-clickable Install.command, in case you
# just want to hand the .dmg to someone else without installing it here.
#
# This one only runs on macOS -- a .dmg is made with hdiutil, which doesn't exist
# on Linux or Windows. On those, use build-deb.sh or the Windows steps instead.

set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "build-dmg.sh only runs on macOS (it needs hdiutil)."
  echo "On Linux build a .deb with build-deb.sh; on Windows use install.bat."
  exit 1
fi

# Where things are. This script lives in packaging/, so the repo root is one up.
PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$PACKAGING_DIR/.." && pwd)"
DIST_DIR="$PACKAGING_DIR/dist"

NODE_DIR="$REPO_ROOT/node"
CLI_DIR="$REPO_ROOT/cli"

# The version is the CLI's version -- same source of truth as build-deb.sh.
VERSION="$(grep -m1 '^version' "$CLI_DIR/pyproject.toml" | cut -d'"' -f2)"
ARCH="$(uname -m)"  # arm64 on Apple Silicon, x86_64 on Intel

# 1. Make sure all three binaries exist, building each if needed (same as build-deb.sh).
NODE_BINARY="$NODE_DIR/target/release/tandem-node"
if [ ! -f "$NODE_BINARY" ]; then
  echo "Building the node release binary first..."
  cargo build --release --manifest-path "$NODE_DIR/Cargo.toml"
fi

# The compile engine `tandem build` shells out to. It's a Rust workspace binary,
# so the build output lands under sdk/target (not sdk/core).
COMPILE_BINARY="$REPO_ROOT/sdk/target/release/tandem-compile"
if [ ! -f "$COMPILE_BINARY" ]; then
  echo "Building the compile engine (tandem-compile) first..."
  cargo build --release --manifest-path "$REPO_ROOT/sdk/core/Cargo.toml" --bin tandem-compile
fi

CLI_BINARY="$CLI_DIR/packaging/dist/tandem"
if [ ! -f "$CLI_BINARY" ]; then
  echo "Building the CLI binary first..."
  bash "$CLI_DIR/packaging/build-binary.sh"
fi

echo "Packaging tandem $VERSION ($ARCH) into a .dmg..."

# 2. Everything that should show up when the user opens the disk image.
STAGING="$(mktemp -d)"
MOUNT_POINT=""
cleanup() {
  rm -rf "$STAGING"
  if [ -n "$MOUNT_POINT" ] && [ -d "$MOUNT_POINT" ]; then
    # -force in case something (e.g. Install.command failing partway through
    # sudo) left a child process holding the volume busy for a moment.
    if hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || hdiutil detach "$MOUNT_POINT" -force -quiet 2>/dev/null; then
      rmdir "$MOUNT_POINT" 2>/dev/null || true
    else
      echo "warning: could not unmount $MOUNT_POINT -- eject it manually (Finder, or 'hdiutil detach \"$MOUNT_POINT\"')" >&2
    fi
  fi
}
trap cleanup EXIT

install -m 0755 "$CLI_BINARY" "$STAGING/tandem"
install -m 0755 "$NODE_BINARY" "$STAGING/tandem-node"
install -m 0755 "$COMPILE_BINARY" "$STAGING/tandem-compile"

# A friendly installer the user can double-click from the mounted image. It puts
# all three commands on the PATH.
cat > "$STAGING/Install.command" <<'INSTALL'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing tandem, tandem-node, and tandem-compile to /usr/local/bin (you may be asked for your password)..."
sudo mkdir -p /usr/local/bin
sudo install -m 0755 "$HERE/tandem" /usr/local/bin/tandem
sudo install -m 0755 "$HERE/tandem-node" /usr/local/bin/tandem-node
sudo install -m 0755 "$HERE/tandem-compile" /usr/local/bin/tandem-compile
echo "Done. Log in with 'tandem auth login', then start the worker with 'tandem node start'."
INSTALL
chmod 0755 "$STAGING/Install.command"

cat > "$STAGING/README.txt" <<'README'
Tandem
======

This disk image contains all three Tandem commands:
  * tandem          the command-line tool
  * tandem-node     the compute node it drives
  * tandem-compile  the compile engine `tandem build` shells out to

To install:
  * Double-click Install.command, OR
  * copy all three onto your PATH yourself, e.g.
      sudo install -m 0755 tandem tandem-node tandem-compile /usr/local/bin/

Once they're on your PATH:
  tandem auth login      # log in
  tandem node start      # start the worker in the background
  tandem status          # check login + node
README

mkdir -p "$DIST_DIR"
OUTPUT="$DIST_DIR/tandem-macos-${ARCH}.dmg"
rm -f "$OUTPUT"

hdiutil create \
  -volname "Tandem" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$OUTPUT" >/dev/null

echo "Built $OUTPUT"

# 3. Mount the image we just built and run its own installer, so this script
# leaves you with a working `tandem` command instead of just a file to hand off.
echo "Installing from the image (you may be asked for your password)..."
MOUNT_POINT="$(mktemp -d)"
hdiutil attach "$OUTPUT" -mountpoint "$MOUNT_POINT" -nobrowse -quiet
"$MOUNT_POINT/Install.command"
hdiutil detach "$MOUNT_POINT" -quiet
MOUNT_POINT=""
