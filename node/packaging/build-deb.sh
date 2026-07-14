#!/usr/bin/env bash
#
# Build a Debian package (.deb) for the Tandem node.
#
#   node/packaging/build-deb.sh
#
# Produces node/packaging/dist/tandem-node_<version>_<arch>.deb. Installing that
# package puts `tandem-node` on the user's PATH (in /usr/bin), which is exactly
# where the CLI looks for it. Runs anywhere dpkg-deb is available -- no special
# Rust packaging tooling needed.

set -euo pipefail

# Where things are. This script lives in node/packaging, so the node crate is one
# directory up and the repo root is two up.
PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="$(cd "$PACKAGING_DIR/.." && pwd)"
DIST_DIR="$PACKAGING_DIR/dist"

# You normally need dpkg-deb; on macOS you'd get it from `brew install dpkg`.
if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb is required to build a .deb but wasn't found."
  echo "On Debian/Ubuntu it's part of the base system; on macOS: brew install dpkg"
  exit 1
fi

# Pull the version straight out of Cargo.toml so the package version always
# matches the crate version.
VERSION="$(grep -m1 '^version' "$NODE_DIR/Cargo.toml" | cut -d'"' -f2)"
if [ -z "$VERSION" ]; then
  echo "Could not read the version from $NODE_DIR/Cargo.toml"
  exit 1
fi

# Debian's own name for this CPU (amd64, arm64, ...). Falls back to amd64 if
# dpkg can't tell us for some reason.
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"

# Build the release binary unless one is already sitting there.
BINARY="$NODE_DIR/target/release/tandem-node"
if [ ! -f "$BINARY" ]; then
  echo "Building the release binary first..."
  cargo build --release --manifest-path "$NODE_DIR/Cargo.toml"
fi

echo "Packaging tandem-node $VERSION ($ARCH)..."

# Lay out the package tree in a scratch directory, then hand it to dpkg-deb.
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

mkdir -p "$STAGING/DEBIAN"
mkdir -p "$STAGING/usr/bin"

install -m 0755 "$BINARY" "$STAGING/usr/bin/tandem-node"

# Note: the heredoc delimiter is unquoted so $VERSION and $ARCH expand, which
# means we must keep backticks out of the body or the shell would try to run
# them as commands.
cat > "$STAGING/DEBIAN/control" <<CONTROL
Package: tandem-node
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Tandem <tandem@wnusair.org>
Description: Tandem compute node
 The Rust worker that runs Tandem WASM tasks. Install this alongside the
 Tandem CLI, then manage it with tandem node start / tandem node status.
CONTROL

mkdir -p "$DIST_DIR"
OUTPUT="$DIST_DIR/tandem-node_${VERSION}_${ARCH}.deb"

# --root-owner-group makes the files inside the package owned by root, so it
# installs cleanly regardless of who built it.
dpkg-deb --build --root-owner-group "$STAGING" "$OUTPUT" >/dev/null

echo "Built $OUTPUT"
