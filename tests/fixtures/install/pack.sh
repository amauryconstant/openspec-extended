#!/usr/bin/env bash
# Generate the install-test fixture tarball + SHA256SUMS from the real
# built binary. Layout mirrors the GitHub Actions release job
# (.github/workflows/release.yml:46-52).
#
# Usage: pack.sh [VERSION] [PLATFORM]
#   VERSION   defaults to the contents of tests/fixtures/install/VERSION
#   PLATFORM  defaults to linux-x86_64

set -euo pipefail

FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$FIXTURE_DIR/../../.." && pwd)"
VERSION="${1:-$(cat "$FIXTURE_DIR/VERSION")}"
PLATFORM="${2:-linux-x86_64}"
BIN_SRC="${BIN_SRC:-$PROJECT_ROOT/dist/openspec-extended}"

if [[ ! -x "$BIN_SRC" ]]; then
    echo "pack.sh: binary not found at $BIN_SRC — run 'mise run build' first" >&2
    exit 1
fi

OUT_DIR="$FIXTURE_DIR/releases/download/v$VERSION"
ASSET="openspec-extended-v${VERSION}-${PLATFORM}.tar.gz"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/openspec-extended/bin"
cp "$BIN_SRC" "$STAGE/openspec-extended/bin/openspec-extended"
chmod 0755 "$STAGE/openspec-extended/bin/openspec-extended"

mkdir -p "$OUT_DIR"
tar -C "$STAGE" -czf "$OUT_DIR/$ASSET" openspec-extended
(
    cd "$OUT_DIR"
    sha256sum "$ASSET" > SHA256SUMS
)