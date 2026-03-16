#!/usr/bin/env bats
# Integration tests for install flow

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# ========== install opencode ==========

@test "install-flow: install opencode creates .opencode structure" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_dir_exists ".opencode/skills"
    assert_dir_exists ".opencode/commands"
    assert_dir_exists ".opencode/scripts"
    assert_dir_exists ".opencode/agents"
}

@test "install-flow: install opencode copies extension skills" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_dir_exists ".opencode/skills/osx-concepts"
    assert_dir_exists ".opencode/skills/osx-modify-artifacts"
    assert_dir_exists ".opencode/skills/osx-review-artifacts"
}

@test "install-flow: install opencode copies agents" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_file_exists ".opencode/agents/osx-analyzer.md"
    assert_file_exists ".opencode/agents/osx-builder.md"
    assert_file_exists ".opencode/agents/osx-maintainer.md"
}

@test "install-flow: install opencode copies commands" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_file_exists ".opencode/commands/osx-phase0.md"
    assert_file_exists ".opencode/commands/osx-phase1.md"
    assert_file_exists ".opencode/commands/osx-phase2.md"
}

@test "install-flow: install opencode copies scripts and makes executable" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_file_exists ".opencode/scripts/osx-orchestrate"
    assert_executable ".opencode/scripts/osx-orchestrate"
}

@test "install-flow: install opencode copies lib scripts" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_dir_exists ".opencode/scripts/lib"
    assert_file_exists ".opencode/scripts/lib/osx"
}

@test "install-flow: install opencode copies manifest with version" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    assert_file_exists ".opencode/manifest.json"
    
    local version
    version=$(jq -r '.version' .opencode/manifest.json)
    [ -n "$version" ]
    [ "$version" != "" ]
    [ "$version" != "null" ]
}

@test "install-flow: install opencode shows success message" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    [[ "$output" == *"Deployed"* ]]
}

# ========== install claude ==========

@test "install-flow: install claude creates .claude structure" {
    run_osx install claude
    [ "$status" -eq 0 ]
    
    assert_dir_exists ".claude/skills"
    assert_dir_exists ".claude/commands"
}

@test "install-flow: install claude copies extension skills" {
    run_osx install claude
    [ "$status" -eq 0 ]
    
    assert_dir_exists ".claude/skills/osx-concepts"
}

# ========== install --with-core ==========

@test "install-flow: install --with-core includes core skills" {
    run_osx install opencode --with-core
    [ "$status" -eq 0 ]
    
    # Core skills should be present
    assert_dir_exists ".opencode/skills/osc-propose" || \
    assert_dir_exists ".opencode/skills/osc-new-change" || \
    [[ "$(ls .opencode/skills/ 2>/dev/null | wc -l)" -gt 6 ]]
}

@test "install-flow: install --with-core includes core commands" {
    run_osx install opencode --with-core
    [ "$status" -eq 0 ]
    
    # Core commands should be present (either flat or in osx/ subdir)
    local has_core=false
    
    if [[ -f ".opencode/commands/osx-propose.md" ]]; then
        has_core=true
    elif [[ -d ".opencode/commands/osx" ]]; then
        has_core=true
    fi
    
    [[ "$has_core" == "true" ]] || \
    [[ "$(ls .opencode/commands/*.md 2>/dev/null | wc -l)" -gt 7 ]]
}

# ========== update command ==========

@test "install-flow: update overwrites existing skills" {
    # First install
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Modify a skill's SKILL.md
    echo "modified" >> ".opencode/skills/osx-concepts/SKILL.md"
    
    # Get original content length
    local orig_len
    orig_len=$(wc -c < "$PROJECT_ROOT/resources/opencode/skills/osx-concepts/SKILL.md")
    
    # Update
    run_osx update opencode
    [ "$status" -eq 0 ]
    
    # File should be overwritten (back to original size)
    local new_len
    new_len=$(wc -c < ".opencode/skills/osx-concepts/SKILL.md")
    [ "$new_len" -eq "$orig_len" ]
}

@test "install-flow: update shows deployed message" {
    # First install
    run_osx install opencode
    
    run_osx update opencode
    [ "$status" -eq 0 ]
    
    [[ "$output" == *"Deployed"* ]]
}

# ========== install vs update ==========

@test "install-flow: install skips existing skills" {
    # First install
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Second install should skip
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    [[ "$output" == *"Skipped"* ]] || [[ "$output" == *"0 skill"* ]]
}

# ========== .gitignore ==========

@test "install-flow: updates .gitignore when osx-orchestrate present" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    [ -f ".gitignore" ]
    grep -q "openspec/changes/.*/state.json" .gitignore
}

@test "install-flow: .gitignore has markers" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    grep -q "BEGIN OpenSpec autonomous" .gitignore
    grep -q "END OpenSpec autonomous" .gitignore
}

@test "install-flow: .gitignore preserves existing content" {
    echo "# Existing content" > .gitignore
    
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    grep -q "# Existing content" .gitignore
    grep -q "openspec/changes" .gitignore
}

# ========== Skills have SKILL.md ==========

@test "install-flow: skills have SKILL.md file" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    for skill_dir in .opencode/skills/*/; do
        assert_file_exists "$skill_dir/SKILL.md"
    done
}

# ========== Commands have .md files ==========

@test "install-flow: commands have .md files" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    local count
    count=$(find .opencode/commands -name "*.md" | wc -l)
    [ "$count" -gt 0 ]
}

# ========== Error handling ==========

@test "install-flow: install to invalid tool fails gracefully" {
    run_osx install nonexistent-tool
    [ "$status" -eq 1 ]
}

# ========== Version-aware upgrade behavior ==========

@test "install-flow: install upgrades skill when source version > installed version" {
    # First install
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Manually downgrade a skill in manifest to simulate older installed version
    local manifest=".opencode/manifest.json"
    local tmp_manifest="${manifest}.tmp"
    jq '.resources.skills."osx-concepts".version = "0.1.0"' "$manifest" > "$tmp_manifest" && mv "$tmp_manifest" "$manifest"
    
    # Second install should upgrade
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Check for upgrade or deployed message
    [[ "$output" == *"Deployed"* ]] || [[ "$output" == *"1 skill"* ]]
    
    # Verify version was updated
    local new_version
    new_version=$(jq -r '.resources.skills."osx-concepts".version' "$manifest")
    [[ "$new_version" != "0.1.0" ]]
}

@test "install-flow: install skips skill when source version == installed version" {
    # First install
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Second install should skip (versions match)
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Should show skipped message or "0 skill" deployed
    [[ "$output" == *"Skipped"* ]] || [[ "$output" == *"0 skill"* ]] || [[ "$output" == *"are current"* ]]
}

@test "install-flow: manifest tracks deployed resources with correct versions" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    local manifest=".opencode/manifest.json"
    
    # Verify manifest has version at top level
    local top_version
    top_version=$(jq -r '.version' "$manifest")
    [ -n "$top_version" ]
    [ "$top_version" != "null" ]
    
    # Verify skills are tracked with versions
    local skill_count
    skill_count=$(jq '.resources.skills | length' "$manifest")
    [ "$skill_count" -gt 0 ]
    
    # Verify a specific skill has version
    local concept_version
    concept_version=$(jq -r '.resources.skills."osx-concepts".version' "$manifest")
    [ -n "$concept_version" ]
    [ "$concept_version" != "null" ]
    
    # Verify agents are tracked
    local agent_count
    agent_count=$(jq '.resources.agents | length' "$manifest")
    [ "$agent_count" -gt 0 ]
    
    # Verify scripts are tracked
    local script_version
    script_version=$(jq -r '.resources.scripts."osx-orchestrate".version' "$manifest")
    [ -n "$script_version" ]
    [ "$script_version" != "null" ]
}

@test "install-flow: update always deploys regardless of version" {
    # First install
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Modify a file to verify update overwrites
    echo "modified" >> ".opencode/skills/osx-concepts/SKILL.md"
    
    # Update should redeploy
    run_osx update opencode
    [ "$status" -eq 0 ]
    
    # File should not contain our modification
    ! grep -q "^modified$" ".opencode/skills/osx-concepts/SKILL.md"
}

# ========== Core tracking (--with-core) ==========

@test "install-flow: --with-core adds core section to manifest when openspec available" {
    # Check if openspec CLI is available
    if ! command -v openspec &>/dev/null; then
        skip "openspec CLI not available"
    fi
    
    run_osx install opencode --with-core
    [ "$status" -eq 0 ]
    
    # Verify core section exists in manifest
    local manifest=".opencode/manifest.json"
    local has_core
    has_core=$(jq 'has("core")' "$manifest")
    
    [ "$has_core" = "true" ]
    
    # Verify core has version
    local core_version
    core_version=$(jq -r '.core.version' "$manifest")
    [ -n "$core_version" ]
    [ "$core_version" != "null" ]
    
    # Verify core has installed flag
    local core_installed
    core_installed=$(jq -r '.core.installed' "$manifest")
    [ "$core_installed" = "true" ]
}

# ========== Validation - no false positives for scripts/lib ==========

@test "install-flow: validation shows no warnings for deployed scripts and lib" {
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Should NOT show warnings for scripts/lib resources
    [[ "$output" != *"Resource 'osx' in manifest but not deployed"* ]]
    [[ "$output" != *"Resource 'osx-orchestrate' in manifest but not deployed"* ]]
    [[ "$output" != *"Validation"* ]] || [[ "$output" == *"0 warning"* ]]
}

# ========== Core rename logic (mocked) ==========

# Helper to source installer functions without running main
load_installer_functions() {
    local installer="$PROJECT_ROOT/bin/openspec-extended"
    
    # Extract color constants and functions (everything before main())
    local code
    code=$(sed '/^main()/,$d' "$installer")
    
    # Remove the readonly declarations that cause issues
    code=$(echo "$code" | grep -v "^readonly TOOL_DIRS")
    
    # Define TOOL_DIRS as global first
    declare -gA TOOL_DIRS=(["opencode"]=".opencode" ["claude"]=".claude")
    
    # Source the remaining code
    eval "$code"
}

@test "install-flow: rename_core_resources handles opsx-* to osc-* renaming" {
    # First install to create base structure
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Create mock openspec CLI output in command/ (singular)
    mkdir -p .opencode/command
    echo "# opsx-apply command" > .opencode/command/opsx-apply.md
    echo "# opsx-archive command" > .opencode/command/opsx-archive.md
    
    # Source and call rename function
    load_installer_functions
    rename_core_resources "opencode"
    
    # Verify renamed files exist in commands/ (plural)
    assert_file_exists ".opencode/commands/osc-apply.md"
    assert_file_exists ".opencode/commands/osc-archive.md"
    
    # Verify original names don't exist
    [[ ! -f ".opencode/commands/opsx-apply.md" ]]
}

@test "install-flow: rename_core_resources consolidates command/ to commands/" {
    # First install to create base structure
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Create mock openspec CLI output in command/ (singular)
    mkdir -p .opencode/command
    echo "# osc-explore command" > .opencode/command/osc-explore.md
    echo "# osc-new command" > .opencode/command/osc-new.md
    
    # Source and call rename function
    load_installer_functions
    rename_core_resources "opencode"
    
    # Verify files moved to commands/ (plural)
    assert_file_exists ".opencode/commands/osc-explore.md"
    assert_file_exists ".opencode/commands/osc-new.md"
    
    # Verify command/ (singular) directory is removed
    [[ ! -d ".opencode/command" ]]
}

@test "install-flow: rename_core_resources moves osx/opsx subdirs to commands/osc/" {
    # First install to create base structure
    run_osx install opencode
    [ "$status" -eq 0 ]
    
    # Create mock openspec CLI output with subdirectory
    mkdir -p .opencode/command/osx
    echo "# osx subcommand" > .opencode/command/osx/phase0.md
    echo "# another subcommand" > .opencode/command/osx/phase1.md
    
    # Also test opsx subdir
    mkdir -p .opencode/command/opsx
    echo "# opsx subcommand" > .opencode/command/opsx/apply.md
    
    # Source and call rename function
    load_installer_functions
    rename_core_resources "opencode"
    
    # Verify subdirectory moved and renamed to osc/
    assert_dir_exists ".opencode/commands/osc"
    assert_file_exists ".opencode/commands/osc/phase0.md"
    assert_file_exists ".opencode/commands/osc/phase1.md"
    assert_file_exists ".opencode/commands/osc/apply.md"
    
    # Verify original subdirs don't exist
    [[ ! -d ".opencode/command" ]]
}
