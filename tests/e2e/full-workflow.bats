#!/usr/bin/env bats
# E2E full workflow tests - complete PHASE0 through PHASE6
# Requires E2E_CONFIRM=1 to run (uses real AI calls, ~5-10 min per test)

load 'helpers/e2e-helpers'

# Use longer timeout for full workflow tests
E2E_TIMEOUT=3600

setup() {
    require_e2e_confirm
    setup_e2e_repo
    copy_fixture "add-hello-script"
}

teardown() {
    teardown_e2e_repo
}

@test "complete workflow with archive validation" {
    local change="add-hello-script"
    local change_dir="openspec/changes/$change"

    run_openspec_auto_streaming "$change" --force --verbose --max-iterations 3 --timeout 600
    [ "$status" -eq 0 ]

    # 1. Verify artifact was created and works
    assert_file_exists "scripts/hello.sh"
    [[ -x "scripts/hello.sh" ]]
    run ./scripts/hello.sh
    [ "$status" -eq 0 ]
    [[ "$output" == *"Hello"* ]]
    
    # 2. Verify change is archived (not in active directory)
    [ ! -d "$change_dir" ]
    
    # 3. Find archive directory
    local archive_dir
    archive_dir=$(find openspec/changes/archive -name "*-$change" -type d 2>/dev/null | head -1)
    [ -n "$archive_dir" ]
    [ -d "$archive_dir" ]
    
    # 4. Verify all required files in archive
    [ -f "$archive_dir/proposal.md" ]
    [ -f "$archive_dir/design.md" ]
    [ -f "$archive_dir/tasks.md" ]
    [ -d "$archive_dir/specs" ]
    [ -f "$archive_dir/iterations.json" ]
    [ -f "$archive_dir/decision-log.json" ]
    
    # 5. Verify state files cleaned (not in archive or project root)
    [ ! -f "$archive_dir/state.json" ]
    [ ! -f "$archive_dir/complete.json" ]
    [ ! -f ".openspec-baseline.json" ]
    
    # 6. Verify iterations.json has all 7 phases
    local phase_count
    phase_count=$(jq '. | length' "$archive_dir/iterations.json")
    [[ "$phase_count" -ge 7 ]]
    
    # 7. Verify decision-log.json has entries
    local log_count
    log_count=$(jq '. | length' "$archive_dir/decision-log.json")
    [[ "$log_count" -ge 7 ]]
    
    # 8. Verify no PHASE0 restart happened (only 1 ARTIFACT_REVIEW iteration)
    local phase0_count
    phase0_count=$(jq '[.[] | select(.phase == "ARTIFACT_REVIEW")] | length' "$archive_dir/iterations.json")
    [[ "$phase0_count" -eq 1 ]]
    
    # 9. Verify AGENTS.md updates in single PHASE3 commit
    local agents_commits
    agents_commits=$(git log --oneline --all -- '*/AGENTS.md' 'AGENTS.md' 2>/dev/null | wc -l)
    [[ "$agents_commits" -le 1 ]]
}
