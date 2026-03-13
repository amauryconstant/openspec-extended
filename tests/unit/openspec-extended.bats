#!/usr/bin/env bats
# Unit tests for openspec-extended CLI

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# ========== CLI: --version ==========

@test "openspec-extended: --version shows version" {
    run_osx --version
    [ "$status" -eq 0 ]
    [[ "$output" == "openspec-extended "* ]]
}

@test "openspec-extended: --version output is semver format" {
    run_osx --version
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^openspec-extended\ [0-9]+\.[0-9]+\.[0-9]+$ ]]
}

# ========== CLI: --help ==========

@test "openspec-extended: --help shows help" {
    run_osx --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"Commands"* ]]
    [[ "$output" == *"install"* ]]
    [[ "$output" == *"update"* ]]
}

@test "openspec-extended: -h shows help" {
    run_osx -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

@test "openspec-extended: --help shows available tools" {
    run_osx --help
    [[ "$output" == *"opencode"* ]]
    [[ "$output" == *"claude"* ]]
}

@test "openspec-extended: --help shows --with-core option" {
    run_osx --help
    [[ "$output" == *"--with-core"* ]]
}

# ========== CLI: no arguments ==========

@test "openspec-extended: no args shows usage and exits 1" {
    run_osx
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

# ========== CLI: invalid command ==========

@test "openspec-extended: unknown command exits 1" {
    run_osx invalid-command opencode
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command"* ]] || [[ "$output" == *"Available commands"* ]]
}

# ========== CLI: invalid tool ==========

@test "openspec-extended: unknown tool exits 1" {
    run_osx install invalid-tool
    [ "$status" -eq 1 ]
}

# ========== CLI: missing tool argument ==========

@test "openspec-extended: install without tool shows usage" {
    run_osx install
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

@test "openspec-extended: update without tool shows usage" {
    run_osx update
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage"* ]]
}

# ========== CLI: --with-core option ==========

@test "openspec-extended: --with-core option recognized" {
    # Should not error on --with-core (even if it doesn't find core)
    run_osx install opencode --with-core
    # May succeed or fail, but should not show "Unknown option"
    [[ "$output" != *"Unknown option"* ]]
}

# ========== Script validation ==========

@test "openspec-extended: script is valid bash" {
    bash -n "$OPENCODEX_BIN"
}

@test "openspec-extended: script is executable" {
    [ -x "$OPENCODEX_BIN" ]
}

@test "openspec-extended: script contains required constants" {
    grep -q "SCRIPT_NAME=" "$OPENCODEX_BIN"
    grep -q "SCRIPT_VERSION=" "$OPENCODEX_BIN"
}

@test "openspec-extended: script contains required functions" {
    grep -q "resolve_install_dirs" "$OPENCODEX_BIN"
    grep -q "copy_skills" "$OPENCODEX_BIN"
    grep -q "deploy_core" "$OPENCODEX_BIN"
}

# ========== Path resolution ==========

@test "openspec-extended: finds resources in development location" {
    # When running from repo, should find ../resources
    run_osx --version
    [ "$status" -eq 0 ]
}

# ========== Version fallback ==========

@test "openspec-extended: script uses SCRIPT_VERSION fallback" {
    # The script should have a fallback version
    grep -q "SCRIPT_VERSION" "$OPENCODEX_BIN"
    
    # Verify it's a valid semver
    local version
    version=$(grep "SCRIPT_VERSION=" "$OPENCODEX_BIN" | head -1 | cut -d'"' -f2)
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}
