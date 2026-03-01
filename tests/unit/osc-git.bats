#!/usr/bin/env bats
# Unit tests for osc-git

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

@test "osc-git: returns error outside git repository" {
    rm -rf .git
    
    run_osc_git
    [ "$status" -eq 1 ]
    assert_output_contains "not_git_repo"
}

@test "osc-git: general status returns clean for new repo" {
    run_osc_git
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".clean"
}

@test "osc-git: general status detects modified files" {
    echo "test" > test-file.txt
    
    run_osc_git
    [ "$status" -eq 0 ]
    assert_json_false "$output" ".clean"
}

@test "osc-git: general status returns branch name" {
    run_osc_git
    [ "$status" -eq 0 ]
    
    # Default branch in new repo
    local branch
    branch=$(echo "$output" | jq -r '.branch')
    [ -n "$branch" ]
}

@test "osc-git: nonexistent change returns error" {
    run_osc_git "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-git: change status returns clean when no change files modified" {
    setup_change "test-change"
    git add .
    git commit -m "initial" -q
    
    # Modify something outside change dir
    echo "other" > other-file.txt
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".clean"
}

@test "osc-git: change status detects modified files in change dir" {
    setup_change "test-change"
    git add .
    git commit -m "initial" -q
    
    echo "modified" >> openspec/changes/test-change/proposal.md
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    assert_json_false "$output" ".clean"
}

@test "osc-git: change status detects untracked files in change dir" {
    setup_change "test-change"
    git add .
    git commit -m "initial" -q
    
    echo "new" > openspec/changes/test-change/new-file.md
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    assert_json_false "$output" ".clean"
}

@test "osc-git: change status includes change name in output" {
    setup_change "test-change"
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".change" "test-change"
}

@test "osc-git: returns arrays for modified, added, untracked" {
    echo "modified" > file1.txt
    echo "new" > file2.txt
    git add file1.txt
    
    run_osc_git
    [ "$status" -eq 0 ]
    
    # Verify structure has these arrays
    local has_modified has_added has_untracked
    has_modified=$(echo "$output" | jq 'has("modified")')
    has_added=$(echo "$output" | jq 'has("added")')
    has_untracked=$(echo "$output" | jq 'has("untracked")')
    
    [ "$has_modified" == "true" ]
    [ "$has_added" == "true" ]
    [ "$has_untracked" == "true" ]
}

@test "osc-git: handles committed repo correctly" {
    setup_change "test-change"
    git add .
    git commit -m "initial" -q
    
    run_osc_git
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".clean"
}

@test "osc-git: change status filters to change directory only" {
    setup_change "test-change"
    git add .
    git commit -m "initial" -q
    
    # Modify file outside change directory
    echo "external" > external-file.txt
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    # Should be clean because change dir has no modifications
    assert_json_true "$output" ".clean"
}
