#!/usr/bin/env bats
# Unit tests for install.sh (binary install flow).
#
# These tests start a local HTTP server in setup_file that serves a
# fixture tarball and SHA256SUMS file. install.sh is pointed at the
# server via BASE_URL, so tests are hermetic and don't touch GitHub.

load '../helpers/test-helpers'

# ========== File-level fixture: local HTTP server ==========

SERVER_PORT=18181
SERVER_PID=""
TARBALL_NAME="openspec-extended-v0.19.0-linux-x86_64.tar.gz"

setup_file() {
    FIXTURE_DIR="$FIXTURES_DIR/install"
    bash "$FIXTURE_DIR/pack.sh" 0.19.0 linux-x86_64
    TARBALL_PATH="$FIXTURE_DIR/releases/download/v0.19.0/$TARBALL_NAME"
    [[ -f "$TARBALL_PATH" ]]
    [[ -f "$FIXTURE_DIR/releases/download/v0.19.0/SHA256SUMS" ]]

    python3 -m http.server "$SERVER_PORT" --directory "$FIXTURE_DIR" \
        >/dev/null 2>&1 &
    SERVER_PID=$!

    # Wait briefly for the server to start accepting connections.
    local i
    for i in {1..50}; do
        if curl -sf "http://127.0.0.1:${SERVER_PORT}/releases/download/v0.19.0/SHA256SUMS" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.1
    done
    echo "Could not start local HTTP server on port $SERVER_PORT" >&2
    return 1
}

teardown_file() {
    if [[ -n "$SERVER_PID" ]]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# Stripped env passed to install.sh. Forces the script to fetch from
# the local server. The `env` prefix in callers keeps the test
# hermetic: we only pass through what install.sh actually needs.
BASE_URL_LOCAL="http://127.0.0.1:${SERVER_PORT}"
TEST_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
TEST_HOME="${HOME:-/tmp}"

# Run install.sh with a minimal env. Caller passes additional args.
run_install() {
    env -i \
        HOME="$TEST_HOME" \
        PATH="$TEST_PATH" \
        BASE_URL="$BASE_URL_LOCAL" \
        BASE_URL_GITHUB="$BASE_URL_LOCAL" \
        REPO=test/test \
        VERSION=v0.19.0 \
        bash "$INSTALL_SCRIPT" "$@"
}

# ========== Help / version ==========

@test "install: --help shows usage" {
    run bash "$INSTALL_SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"BASE_URL"* ]]
}

@test "install: --version shows installer version" {
    run bash "$INSTALL_SCRIPT" --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"OpenSpec-extended installer"* ]]
}

@test "install: --uninstall is recognized and exits cleanly" {
    run bash "$INSTALL_SCRIPT" --uninstall <<< "n"
    [ "$status" -eq 0 ]
    [[ "$output" != *"Unknown option"* ]]
}

@test "install: unknown option shows --help hint" {
    run bash "$INSTALL_SCRIPT" --bogus-flag
    [ "$status" -ne 0 ]
    [[ "$output" == *"Unknown option"* ]]
    [[ "$output" == *"--help"* ]]
}

# ========== PREFIX handling ==========

@test "install: rejects PREFIX with path traversal" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" PREFIX='../../../tmp' \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid PREFIX"* ]]
}

@test "install: rejects system directory /etc" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" PREFIX=/etc \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid PREFIX"* ]]
}

@test "install: rejects system directory /bin" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" PREFIX=/bin \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid PREFIX"* ]]
}

@test "install: accepts home directory PREFIX" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" PREFIX="$HOME/.local" \
        bash "$INSTALL_SCRIPT" --help
    [ "$status" -eq 0 ]
}

# ========== VERSION handling ==========

@test "install: rejects VERSION without patch" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" VERSION='1.2' \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid VERSION"* ]]
}

@test "install: rejects VERSION with non-numeric parts" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" VERSION='1.2.x' \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid VERSION"* ]]
}

@test "install: accepts VERSION with prerelease" {
    # Will fail to download (no v1.2.3-alpha fixture), but must pass
    # validation. The error must NOT be about VERSION format.
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" PREFIX="$TEST_DIR/.local" \
        REPO=test/test VERSION='v1.2.3-alpha.1' BASE_URL="$BASE_URL_LOCAL" \
        bash "$INSTALL_SCRIPT" 2>&1
    [[ "$output" != *"Invalid VERSION"* ]]
}

@test "install: accepts VERSION with build metadata" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" PREFIX="$TEST_DIR/.local" \
        REPO=test/test VERSION='v1.2.3+build.42' BASE_URL="$BASE_URL_LOCAL" \
        bash "$INSTALL_SCRIPT" 2>&1
    [[ "$output" != *"Invalid VERSION"* ]]
}

@test "install: accepts latest and main keywords" {
    for keyword in latest main; do
        run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" VERSION="$keyword" \
            bash "$INSTALL_SCRIPT" 2>&1
        [[ "$output" != *"Invalid VERSION"* ]]
    done
}

# ========== REPO handling ==========

@test "install: rejects REPO with path traversal" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" REPO='../../etc/passwd' \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid REPO format"* ]]
}

@test "install: rejects REPO with command injection" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" REPO='repo; rm -rf /tmp' \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid REPO format"* ]]
}

@test "install: rejects REPO with too many parts" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" REPO='repo/extra/parts' \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid REPO format"* ]]
}

@test "install: accepts valid REPO format" {
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" REPO='test/test' \
        bash "$INSTALL_SCRIPT" --help
    [ "$status" -eq 0 ]
}

# ========== Dependencies ==========

@test "install: requires curl or wget" {
    grep -q "curl.*wget" "$INSTALL_SCRIPT"
}

@test "install: requires tar" {
    grep -q "command -v tar" "$INSTALL_SCRIPT"
}

# ========== Platform detection ==========

@test "install: detect_platform returns supported platform on this OS" {
    run bash -c "
        $(sed -n '/^detect_platform()/,/^}/p' "$INSTALL_SCRIPT")
        detect_platform
    "
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^(linux|darwin)-(x86_64|arm64)$ ]]
}

@test "install: detect_platform rejects unknown OS strings" {
    # Verify the case statement in detect_platform covers only
    # linux/darwin. We grep the source rather than stubbing uname,
    # which is fragile under bash function scoping.
    grep -A3 "case \"\\\$os\" in" "$INSTALL_SCRIPT" | grep -q "linux)"
    grep -A3 "case \"\\\$os\" in" "$INSTALL_SCRIPT" | grep -q "darwin)"
    ! grep -A6 "case \"\\\$os\" in" "$INSTALL_SCRIPT" | grep -q "beos)"
}

# ========== Script structure ==========

@test "install: script is valid bash" {
    bash -n "$INSTALL_SCRIPT"
}

@test "install: script is executable" {
    [ -x "$INSTALL_SCRIPT" ]
}

@test "install: script contains required functions" {
    for fn in detect_platform download_tarball verify_checksum run_install uninstall; do
        grep -q "^${fn}()" "$INSTALL_SCRIPT"
    done
}

# ========== Code quality ==========

@test "install: uses portable shebang" {
    head -1 "$INSTALL_SCRIPT" | grep -q "^#!/usr/bin/env bash"
}

@test "install: shellcheck passes (no errors or warnings)" {
    if ! command -v shellcheck &>/dev/null; then
        skip "shellcheck not available"
    fi
    local out
    out=$(shellcheck "$INSTALL_SCRIPT" 2>&1 || true)
    if echo "$out" | grep -v "SC2310" | grep -qE 'SC[0-9]{4} \(error|warning\)'; then
        echo "$out"
        return 1
    fi
}

# ========== End-to-end install (the only network-free real install) ==========

@test "install: end-to-end install via BASE_URL produces runnable binary" {
    local prefix="$TEST_DIR/.local"
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" \
        PREFIX="$prefix" REPO=test/test VERSION=v0.19.0 \
        BASE_URL="$BASE_URL_LOCAL" \
        bash "$INSTALL_SCRIPT" 2>&1
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -x "$prefix/bin/openspec-extended" ]

    run "$prefix/bin/openspec-extended" --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.19.0"* ]]
}

@test "install: rejects tarball with bad SHA256SUMS" {
    # Overwrite SHA256SUMS with a checksum that doesn't match the tarball.
    echo "0000000000000000000000000000000000000000000000000000000000000000  $TARBALL_NAME" \
        > "$FIXTURES_DIR/install/releases/download/v0.19.0/SHA256SUMS"

    local prefix="$TEST_DIR/.local"
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" \
        PREFIX="$prefix" REPO=test/test VERSION=v0.19.0 \
        BASE_URL="$BASE_URL_LOCAL" \
        bash "$INSTALL_SCRIPT" 2>&1
    [ "$status" -ne 0 ]
    [[ "$output" == *"Checksum verification failed"* ]]

    # Restore the correct checksums so other tests can use the fixture.
    bash "$FIXTURES_DIR/install/pack.sh" 0.19.0 linux-x86_64 >/dev/null
}

@test "install: --uninstall removes the installed binary" {
    local prefix="$TEST_DIR/.local"

    # First install
    env -i HOME="$TEST_HOME" PATH="$TEST_PATH" \
        PREFIX="$prefix" REPO=test/test VERSION=v0.19.0 \
        BASE_URL="$BASE_URL_LOCAL" \
        bash "$INSTALL_SCRIPT" >/dev/null 2>&1
    [ -x "$prefix/bin/openspec-extended" ]

    # Then uninstall, with confirmation
    run env -i HOME="$TEST_HOME" PATH="$TEST_PATH" \
        PREFIX="$prefix" REPO=test/test VERSION=v0.19.0 \
        BASE_URL="$BASE_URL_LOCAL" \
        bash "$INSTALL_SCRIPT" --uninstall <<< "y" 2>&1
    [ "$status" -eq 0 ]
    [ ! -e "$prefix/bin/openspec-extended" ]
}
