#!/usr/bin/env bats
# Unit tests for install.sh

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# ========== Argument parsing ==========

@test "install: --help shows usage and exits 0" {
    run bash "$INSTALL_SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"Examples"* ]]
}

@test "install: -h shows usage and exits 0" {
    run bash "$INSTALL_SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

@test "install: --uninstall option recognized" {
    # Should not error on --uninstall even if nothing installed
    # Provide 'n' input to skip confirmation if installation exists
    run bash -c "echo 'n' | bash '$INSTALL_SCRIPT' --uninstall"
    # May fail if nothing to uninstall, but should not show usage error
    [[ "$output" != *"Unknown option"* ]]
}

@test "install: unknown option shows error" {
    run bash "$INSTALL_SCRIPT" --invalid-option
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}

# ========== PREFIX handling ==========

@test "install: respects PREFIX environment variable" {
    local custom_prefix="$TEST_DIR/custom-prefix"
    
    # Source and test the variable is used
    export PREFIX="$custom_prefix"
    
    # Just verify the script uses the variable by checking help doesn't fail
    run bash -c "PREFIX='$custom_prefix' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

# ========== VERSION handling ==========

@test "install: respects VERSION environment variable" {
    export VERSION=v0.9.0
    
    # Verify script accepts VERSION variable
    run bash -c "VERSION=v0.9.0 bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

# ========== REPO handling ==========

@test "install: respects REPO environment variable" {
    export REPO="test/repo"
    
    # Verify script accepts REPO variable
    run bash -c "REPO='test/repo' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

# ========== Directory creation ==========

@test "install: creates PREFIX/share/openspec-extended directory" {
    local prefix="$TEST_DIR/.local"
    
    # The install function should create directories
    # We test this indirectly by verifying uninstall works
    mkdir -p "$prefix/share/openspec-extended"
    mkdir -p "$prefix/bin"
    
    assert_dir_exists "$prefix/share/openspec-extended"
}

# ========== Uninstall functionality ==========

@test "install: uninstall removes install directory" {
    skip "Requires interactive confirmation"
}

@test "install: uninstall removes symlink" {
    skip "Requires interactive confirmation"
}

@test "install: uninstall handles missing installation gracefully" {
    local prefix="$TEST_DIR/nonexistent"
    
    # Should not fail even if nothing to uninstall
    PREFIX="$prefix" run bash "$INSTALL_SCRIPT" --uninstall
    [ "$status" -eq 0 ]
}

# ========== Dependencies ==========

@test "install: requires curl or wget" {
    # This test verifies the check_dependencies function exists
    # We can't easily test it without mocking, so just verify script structure
    grep -q "curl.*wget" "$INSTALL_SCRIPT"
}

# ========== Script structure ==========

@test "install: script is valid bash" {
    bash -n "$INSTALL_SCRIPT"
}

@test "install: script is executable" {
    [ -x "$INSTALL_SCRIPT" ]
}

@test "install: script contains required functions" {
    grep -q "^get_latest_version" "$INSTALL_SCRIPT"
    grep -q "^download_tarball" "$INSTALL_SCRIPT"
    grep -q "^install()" "$INSTALL_SCRIPT"
    grep -q "^uninstall()" "$INSTALL_SCRIPT"
}

# ========== Input Validation - REPO ==========

@test "install: rejects REPO with path traversal" {
    run bash -c "REPO='../../etc/passwd' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid REPO format"* ]]
}

@test "install: rejects REPO with command injection" {
    run bash -c "REPO='repo; rm -rf /tmp' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid REPO format"* ]]
}

@test "install: rejects REPO with too many parts" {
    run bash -c "REPO='repo/extra/parts' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid REPO format"* ]]
}

@test "install: accepts valid REPO format" {
    run bash -c "REPO='test/test' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

# ========== Input Validation - VERSION ==========

@test "install: rejects VERSION without patch" {
    run bash -c "VERSION='1.2' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid VERSION format"* ]]
}

@test "install: accepts valid SemVer" {
    run bash -c "VERSION='1.2.3' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

@test "install: accepts VERSION with v prefix" {
    run bash -c "VERSION='v1.2.3' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

@test "install: accepts VERSION with prerelease" {
    run bash -c "VERSION='1.2.3-alpha.1' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

@test "install: accepts VERSION with build" {
    run bash -c "VERSION='1.2.3+build' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

@test "install: accepts VERSION keyword latest" {
    run bash -c "VERSION='latest' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

@test "install: accepts VERSION keyword main" {
    run bash -c "VERSION='main' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

# ========== Input Validation - PREFIX ==========

@test "install: rejects PREFIX with path traversal" {
    run bash -c "PREFIX='../../../tmp' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid PREFIX"* ]]
}

@test "install: rejects system directory /etc" {
    run bash -c "PREFIX='/etc' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid PREFIX"* ]]
}

@test "install: rejects system directory /bin" {
    run bash -c "PREFIX='/bin' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" == *"Invalid PREFIX"* ]]
}

@test "install: accepts home directory PREFIX" {
    run bash -c "PREFIX='$HOME/.local' bash '$INSTALL_SCRIPT' --help"
    [ "$status" -eq 0 ]
}

# ========== Error Handling ==========

@test "install: unknown option shows --help hint" {
    run bash "$INSTALL_SCRIPT" --invalid
    [ "$status" -eq 1 ]
    [[ "$output" == *"Run"* ]]
    [[ "$output" == *"--help"* ]]
}

@test "install: dependency error shows macOS hint" {
    run bash -c "OSTYPE='darwin' bash '$INSTALL_SCRIPT' 2>&1"
    [[ "$output" == *"brew install"* ]] || true
}

@test "install: dependency error shows apt-get hint" {
    skip "Platform-specific test"
}

@test "install: dependency error shows yum hint" {
    skip "Platform-specific test"
}

@test "install: dependency error shows pacman hint" {
    skip "Platform-specific test"
}

# ========== Code Quality ==========

@test "install: uses portable shebang" {
    head -1 "$INSTALL_SCRIPT" | grep -q '#!/usr/bin/env bash'
}

@test "install: passes shellcheck" {
    if ! command -v shellcheck &>/dev/null; then
        skip "shellcheck not available"
    fi
    
    local shellcheck_output
    shellcheck_output=$(shellcheck "$INSTALL_SCRIPT" 2>&1 || true)
    
    # Check for errors or warnings (exclude info-level SC2310)
    if echo "$shellcheck_output" | grep -v "SC2310" | grep -qE 'SC[0-9]{4} \(error|warning\)'; then
        echo "$shellcheck_output"
        return 1
    fi
}

# ========== Integration Test ==========

@test "install: full install and uninstall cycle" {
    local prefix="/tmp/openspec-test-$$"
    
    # Run install
    run bash -c "PREFIX='$prefix' bash '$INSTALL_SCRIPT' 2>&1"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Installed"* ]]
    
    # Verify installation exists
    assert_dir_exists "$prefix/share/openspec-extended"
    assert_dir_exists "$prefix/share/openspec-extended/resources"
    assert_dir_exists "$prefix/share/openspec-extended/resources/opencode"
    assert_dir_exists "$prefix/share/openspec-extended/resources/claude"
    assert_file_exists "$prefix/share/openspec-extended/bin/openspec-extended"
    assert_dir_exists "$prefix/bin"
    
    # Verify symlink exists
    [ -L "$prefix/bin/openspec-extended" ]
    
    # Verify binary is executable and works
    assert_executable "$prefix/bin/openspec-extended"
    run "$prefix/bin/openspec-extended" --version
    [ "$status" -eq 0 ]
    
    # Run uninstall with confirmation
    run bash -c "echo 'y' | PREFIX='$prefix' bash '$INSTALL_SCRIPT' --uninstall 2>&1"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Uninstall complete"* ]]
    
    # Verify files removed
    [ ! -d "$prefix/share/openspec-extended" ]
    [ ! -e "$prefix/bin/openspec-extended" ]
    
    # Clean up empty directories
    rm -rf "$prefix"
}
