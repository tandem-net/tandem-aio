#!/usr/bin/env bash
#
# Build the release binaries the node and driver images copy in, then build the
# stack images. Run this before bringing the stack up.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo ">>> building tandem-node (release)"
cargo build --release --manifest-path node/Cargo.toml

echo ">>> building tandem-compile (release)"
cargo build --release --manifest-path sdk/core/Cargo.toml --bin tandem-compile

echo ">>> building docker images"
docker compose -f docker/docker-compose.yml build

echo ""
echo "Done. Run the end-to-end test with:"
echo "  docker compose -f docker/docker-compose.yml up --abort-on-container-exit --exit-code-from driver"
