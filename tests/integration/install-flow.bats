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
    
    [[ "$output" == *"Installed"* ]] || [[ "$output" == *"Copied"* ]]
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

@test "install-flow: update shows updated message" {
    # First install
    run_osx install opencode
    
    run_osx update opencode
    [ "$status" -eq 0 ]
    
    [[ "$output" == *"Updated"* ]]
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
