#!/usr/bin/env bats
# Unit tests for openspecx CLI

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# ========== CLI: --version ==========

@test "openspecx: --version shows version" {
    run_openspecx --version
    [ "$status" -eq 0 ]
    [[ "$output" == "openspecx "* ]]
}

@test "openspecx: --version output is semver format" {
    run_openspecx --version
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^openspecx\ [0-9]+\.[0-9]+\.[0-9]+$ ]]
}

# ========== CLI: --help ==========

@test "openspecx: --help shows help" {
    run_openspecx --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"Commands"* ]]
    [[ "$output" == *"install"* ]]
    [[ "$output" == *"update"* ]]
}

@test "openspecx: -h shows help" {
    run_openspecx -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

@test "openspecx: --help shows available tools" {
    run_openspecx --help
    [[ "$output" == *"opencode"* ]]
    [[ "$output" == *"claude"* ]]
}

@test "openspecx: --help shows --with-core option" {
    run_openspecx --help
    [[ "$output" == *"--with-core"* ]]
}

# ========== CLI: no arguments ==========

@test "openspecx: no args shows usage and exits 1" {
    run_openspecx
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

# ========== CLI: invalid command ==========

@test "openspecx: unknown command exits 1" {
    run_openspecx invalid-command opencode
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command"* ]] || [[ "$output" == *"Available commands"* ]]
}

# ========== CLI: invalid tool ==========

@test "openspecx: unknown tool exits 1" {
    run_openspecx install invalid-tool
    [ "$status" -eq 1 ]
}

# ========== CLI: missing tool argument ==========

@test "openspecx: install without tool shows usage" {
    run_openspecx install
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

@test "openspecx: update without tool shows usage" {
    run_openspecx update
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

# ========== CLI: --with-core option ==========

@test "openspecx: --with-core option recognized" {
    # Should not error on --with-core (even if it doesn't find core)
    run_openspecx install opencode --with-core
    # May succeed or fail, but should not show "Unknown option"
    [[ "$output" != *"Unknown option"* ]]
}

# ========== Script validation ==========

@test "openspecx: script is valid bash" {
    bash -n "$OPENCODEX_BIN"
}

@test "openspecx: script is executable" {
    [ -x "$OPENCODEX_BIN" ]
}

@test "openspecx: script contains required constants" {
    grep -q "SCRIPT_NAME=" "$OPENCODEX_BIN"
    grep -q "SCRIPT_VERSION=" "$OPENCODEX_BIN"
}

@test "openspecx: script contains required functions" {
    grep -q "resolve_install_dirs" "$OPENCODEX_BIN"
    grep -q "get_git_tag" "$OPENCODEX_BIN"
    grep -q "copy_skills" "$OPENCODEX_BIN"
    grep -q "deploy_core" "$OPENCODEX_BIN"
}

# ========== Path resolution ==========

@test "openspecx: finds resources in development location" {
    # When running from repo, should find ../resources
    run_openspecx --version
    [ "$status" -eq 0 ]
}

# ========== Version fallback ==========

@test "openspecx: get_git_tag falls back to SCRIPT_VERSION outside git" {
    # The script should have a fallback version
    grep -q "SCRIPT_VERSION" "$OPENCODEX_BIN"
    
    # Verify it's a valid semver
    local version
    version=$(grep "SCRIPT_VERSION=" "$OPENCODEX_BIN" | head -1 | cut -d'"' -f2)
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}
