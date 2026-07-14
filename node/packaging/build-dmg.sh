#!/usr/bin/env bash
#
# Build a macOS disk image (.dmg) for the Tandem node.
#
#   node/packaging/build-dmg.sh
#
# Produces node/packaging/dist/tandem-node-macos-<arch>.dmg. The image holds the
# `tandem-node` binary plus a double-clickable Install.command that copies it to
# /usr/local/bin, which is where the CLI looks for it on PATH.
#
# This one only runs on macOS -- a .dmg is made with hdiutil, which doesn't exist
# on Linux or Windows. On those, use build-deb.sh or the Windows .exe instead.

set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "build-dmg.sh only runs on macOS (it needs hdiutil)."
  echo "On Linux build a .deb with build-deb.sh; on Windows ship the .exe directly."
  exit 1
fi

PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="$(cd "$PACKAGING_DIR/.." && pwd)"
DIST_DIR="$PACKAGING_DIR/dist"

VERSION="$(grep -m1 '^version' "$NODE_DIR/Cargo.toml" | cut -d'"' -f2)"
ARCH="$(uname -m)"  # arm64 on Apple Silicon, x86_64 on Intel

BINARY="$NODE_DIR/target/release/tandem-node"
if [ ! -f "$BINARY" ]; then
  echo "Building the release binary first..."
  cargo build --release --manifest-path "$NODE_DIR/Cargo.toml"
fi

echo "Packaging tandem-node $VERSION ($ARCH) into a .dmg..."

# Everything that should show up when the user opens the disk image.
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

cp "$BINARY" "$STAGING/tandem-node"
chmod 0755 "$STAGING/tandem-node"

# A friendly installer the user can double-click from the mounted image.
cat > "$STAGING/Install.command" <<'INSTALL'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing tandem-node to /usr/local/bin (you may be asked for your password)..."
sudo mkdir -p /usr/local/bin
sudo install -m 0755 "$HERE/tandem-node" /usr/local/bin/tandem-node
echo "Done. Now manage it from the Tandem CLI: tandem node start"
INSTALL
chmod 0755 "$STAGING/Install.command"

cat > "$STAGING/README.txt" <<'README'
Tandem compute node
===================

This disk image contains the tandem-node binary.

To install:
  * Double-click Install.command, OR
  * copy tandem-node onto your PATH yourself, e.g.
      sudo install -m 0755 tandem-node /usr/local/bin/tandem-node

Once it's on your PATH, the Tandem CLI manages it for you:
  tandem node start      # start it in the background
  tandem node enable     # run it 24/7 (starts on login, restarts on crash)
  tandem status          # check whether it's running
README

mkdir -p "$DIST_DIR"
OUTPUT="$DIST_DIR/tandem-node-macos-${ARCH}.dmg"
rm -f "$OUTPUT"

hdiutil create \
  -volname "Tandem Node" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$OUTPUT" >/dev/null

echo "Built $OUTPUT"
