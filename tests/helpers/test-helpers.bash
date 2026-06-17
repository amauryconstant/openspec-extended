#!/usr/bin/env bash
# Minimal test helpers for install.bats
# Sourced once per test

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"
INSTALL_SCRIPT="$PROJECT_ROOT/install.sh"

setup_test_env() {
    TEST_DIR=$(mktemp -d)
    pushd "$TEST_DIR" > /dev/null || exit 1

    export FIXTURES_DIR
    export INSTALL_SCRIPT
    export TEST_DIR
}

teardown_test_env() {
    popd > /dev/null 2>&1 || true
    if [[ -n "${TEST_DIR:-}" ]] && [[ -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR"
    fi
}
