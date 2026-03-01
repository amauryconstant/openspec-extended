#!/usr/bin/env bats
# Unit tests for osc-validate

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# Usage/Errors

@test "osc-validate: missing arguments shows usage error" {
    run_osc_validate
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-validate: nonexistent change returns error for change-dir" {
    run_osc_validate "nonexistent-change" change-dir
    [ "$status" -eq 1 ]
    assert_output_contains "valid"
    assert_json_false "$output" ".valid"
}

@test "osc-validate: unknown action returns error" {
    setup_change "test-change"
    
    run_osc_validate "test-change" invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

# json action

@test "osc-validate: json returns valid for valid JSON file" {
    setup_change "test-change"
    echo '{"test":true}' > "openspec/changes/test-change/test.json"
    
    run_osc_validate "test-change" json "openspec/changes/test-change/test.json"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
}

@test "osc-validate: json returns invalid for corrupted JSON" {
    setup_change "test-change"
    echo 'not valid json' > "openspec/changes/test-change/test.json"
    
    run_osc_validate "test-change" json "openspec/changes/test-change/test.json"
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
}

@test "osc-validate: json returns invalid for missing file" {
    setup_change "test-change"
    
    run_osc_validate "test-change" json "openspec/changes/test-change/nonexistent.json"
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "File not found"
}

@test "osc-validate: json requires file argument" {
    setup_change "test-change"
    
    run_osc_validate "test-change" json
    [ "$status" -eq 1 ]
    assert_output_contains "missing_value"
}

# skills action

@test "osc-validate: skills returns valid when all skills exist" {
    setup_skills_dir
    
    run_osc_validate "test-change" skills
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
}

@test "osc-validate: skills returns invalid with missing skills" {
    mkdir -p ".opencode/skills/openspec-concepts"
    echo "# concepts" > ".opencode/skills/openspec-concepts/SKILL.md"
    
    run_osc_validate "test-change" skills
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "Missing skill"
}

# commands action

@test "osc-validate: commands returns valid when all commands exist" {
    setup_commands_dir
    
    run_osc_validate "test-change" commands
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
}

@test "osc-validate: commands returns invalid with missing commands" {
    mkdir -p ".opencode/commands"
    echo "# phase0" > ".opencode/commands/openspec-phase0.md"
    
    run_osc_validate "test-change" commands
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "Missing command"
}

# change-dir action

@test "osc-validate: change-dir returns valid for complete change" {
    setup_change "test-change"
    
    run_osc_validate "test-change" change-dir
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
}

@test "osc-validate: change-dir returns invalid missing tasks.md" {
    setup_change "test-change"
    rm "openspec/changes/test-change/tasks.md"
    
    run_osc_validate "test-change" change-dir
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "tasks.md"
}

@test "osc-validate: change-dir returns invalid missing proposal.md" {
    setup_change "test-change"
    rm "openspec/changes/test-change/proposal.md"
    
    run_osc_validate "test-change" change-dir
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "proposal.md"
}

@test "osc-validate: change-dir returns invalid missing design.md" {
    setup_change "test-change"
    rm "openspec/changes/test-change/design.md"
    
    run_osc_validate "test-change" change-dir
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "design.md"
}

@test "osc-validate: change-dir returns invalid missing specs/" {
    mkdir -p "openspec/changes/test-change"
    echo "# Proposal" > "openspec/changes/test-change/proposal.md"
    echo "# Design" > "openspec/changes/test-change/design.md"
    echo "# Tasks" > "openspec/changes/test-change/tasks.md"
    
    run_osc_validate "test-change" change-dir
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "specs"
}

@test "osc-validate: change-dir returns invalid with empty specs/" {
    mkdir -p "openspec/changes/test-change/specs"
    echo "# Proposal" > "openspec/changes/test-change/proposal.md"
    echo "# Design" > "openspec/changes/test-change/design.md"
    echo "# Tasks" > "openspec/changes/test-change/tasks.md"
    
    run_osc_validate "test-change" change-dir
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "No spec files"
}

# archive action

@test "osc-validate: archive returns valid for single archive" {
    setup_change "test-change"
    setup_archive "test-change"
    
    run_osc_validate "test-change" archive
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
    assert_json_has_field "$output" "archive"
}

@test "osc-validate: archive returns invalid for no archive" {
    setup_change "test-change"
    
    run_osc_validate "test-change" archive
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "not archived"
}

@test "osc-validate: archive returns invalid for multiple archives" {
    setup_change "test-change"
    setup_archive "test-change" "2024-01-15"
    setup_archive "test-change" "2024-01-16"
    
    run_osc_validate "test-change" archive
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "Multiple archives"
}

# iterations action

@test "osc-validate: iterations returns valid for existing file" {
    setup_change_with_iterations "test-change" '[{"iteration":1}]'
    
    run_osc_validate "test-change" iterations
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
}

@test "osc-validate: iterations returns invalid for missing file" {
    setup_change "test-change"
    
    run_osc_validate "test-change" iterations
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "not found"
}

# completion action

@test "osc-validate: completion validates all required files" {
    setup_change "test-change"
    echo '{"phase":"PHASE0"}' > "openspec/changes/test-change/state.json"
    echo '{"status":"COMPLETE"}' > "openspec/changes/test-change/complete.json"
    echo '[{"iteration":1}]' > "openspec/changes/test-change/iterations.json"
    echo '[{"entry":1}]' > "openspec/changes/test-change/decision-log.json"
    setup_archive "test-change"
    
    run_osc_validate "test-change" completion
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".valid"
}

@test "osc-validate: completion returns errors for missing files" {
    setup_change "test-change"
    
    run_osc_validate "test-change" completion
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".valid"
    assert_output_contains "state.json"
}
