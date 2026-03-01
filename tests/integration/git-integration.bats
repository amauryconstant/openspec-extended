#!/usr/bin/env bats
# Integration tests for git operations with state

load '../helpers/test-helpers'

setup() {
    setup_test_env
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
}

teardown() {
    teardown_test_env
}

@test "git-integration: baseline is recorded with commit hash" {
    run_osc_baseline "record"
    [ "$status" -eq 0 ]
    
    local commit
    commit=$(jq -r '.commit' ".openspec-baseline.json")
    [ -n "$commit" ]
    [ "$commit" != "null" ]
    [[ "$commit" =~ ^[a-f0-9]{40}$ ]]
}

@test "git-integration: baseline persists across state operations" {
    run_osc_baseline "record"
    [ "$status" -eq 0 ]
    
    local recorded_commit
    recorded_commit=$(jq -r '.commit' ".openspec-baseline.json")
    
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1}'
    
    run_osc_phase "test-change" advance
    [ "$status" -eq 0 ]
    
    run_osc_baseline "get"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".commit" "$recorded_commit"
}

@test "git-integration: git status integrates with context" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":1}'
    
    echo "test content" > "openspec/changes/test-change/test-file.txt"
    git add "openspec/changes/test-change/test-file.txt"
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    
    local added_count
    added_count=$(echo "$output" | jq '.added | length')
    [ "$added_count" -ge 1 ]
}

@test "git-integration: branch name is captured correctly" {
    run_osc_baseline "record"
    [ "$status" -eq 0 ]
    
    local branch
    branch=$(jq -r '.branch' ".openspec-baseline.json")
    [ -n "$branch" ]
    [ "$branch" != "null" ]
}

@test "git-integration: git status detects untracked files in change directory" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":1}'
    
    git add openspec/changes/test-change/*.md
    git commit -q -m "Track change files"
    
    mkdir -p "openspec/changes/test-change/newdir"
    echo "new file" > "openspec/changes/test-change/newdir/untracked.md"
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    
    local untracked_count
    untracked_count=$(echo "$output" | jq '.untracked | length')
    [ "$untracked_count" -ge 1 ]
}

@test "git-integration: git status reflects change directory modifications" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":1}'
    
    git add "openspec/changes/test-change/"
    git commit -q -m "Track change files"
    
    echo "modified content" >> "openspec/changes/test-change/proposal.md"
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    
    local modified_count
    modified_count=$(echo "$output" | jq '.modified | length')
    [ "$modified_count" -ge 1 ]
}
