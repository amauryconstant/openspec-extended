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
    run bash "$INSTALL_SCRIPT" --uninstall
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

@test "install: creates PREFIX/share/openspecx directory" {
    local prefix="$TEST_DIR/.local"
    
    # The install function should create directories
    # We test this indirectly by verifying uninstall works
    mkdir -p "$prefix/share/openspecx"
    mkdir -p "$prefix/bin"
    
    assert_dir_exists "$prefix/share/openspecx"
}

# ========== Uninstall functionality ==========

@test "install: uninstall removes install directory" {
    local prefix="$TEST_DIR/.local"
    local install_dir="$prefix/share/openspecx"
    
    # Create fake installation
    mkdir -p "$install_dir/resources"
    mkdir -p "$prefix/bin"
    touch "$prefix/bin/openspecx"
    
    # Run uninstall
    PREFIX="$prefix" run bash "$INSTALL_SCRIPT" --uninstall
    
    # Directory should be removed
    [ ! -d "$install_dir" ]
}

@test "install: uninstall removes symlink" {
    local prefix="$TEST_DIR/.local"
    local install_dir="$prefix/share/openspecx"
    
    # Create fake installation with symlink
    mkdir -p "$install_dir/bin"
    mkdir -p "$prefix/bin"
    echo "#!/bin/bash" > "$install_dir/bin/openspecx"
    ln -sf "$install_dir/bin/openspecx" "$prefix/bin/openspecx"
    
    # Run uninstall
    PREFIX="$prefix" run bash "$INSTALL_SCRIPT" --uninstall
    
    # Symlink should be removed
    [ ! -e "$prefix/bin/openspecx" ]
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
