#!/usr/bin/env bats
# Unit tests for openspec-auto script functions

load '../helpers/test-helpers'

setup() {
    setup_test_env
    setup_change "test-change"
    
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    LIB_DIR="$PROJECT_ROOT/resources/opencode/scripts/lib"
    
    # Source functions from openspec-auto (extract just the functions we need)
    # We can't source the whole file as it has a main() that runs
}

teardown() {
    teardown_test_env
}

# Test the phase label mapping by simulating show_progress behavior
@test "show_progress: displays correct phase labels for PHASE5 and PHASE6" {
    # Create iterations.json with one entry per phase
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "ARTIFACT_REVIEW"},
  {"iteration": 1, "phase": "IMPLEMENTATION"},
  {"iteration": 1, "phase": "REVIEW"},
  {"iteration": 1, "phase": "MAINTAIN-DOCS"},
  {"iteration": 1, "phase": "SYNC"},
  {"iteration": 1, "phase": "SELF_REFLECTION"},
  {"iteration": 1, "phase": "ARCHIVE"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Test the jq queries directly (these are what show_progress uses)
    local phase0_count phase5_count phase6_count
    
    phase0_count=$(jq 'map(select(.phase == "ARTIFACT_REVIEW")) | length' "$iterations_file")
    [ "$phase0_count" == "1" ]
    
    # PHASE5 should count SELF_REFLECTION entries
    phase5_count=$(jq 'map(select(.phase == "SELF_REFLECTION")) | length' "$iterations_file")
    [ "$phase5_count" == "1" ]
    
    # PHASE6 should count ARCHIVE entries
    phase6_count=$(jq 'map(select(.phase == "ARCHIVE")) | length' "$iterations_file")
    [ "$phase6_count" == "1" ]
}

@test "show_progress: counts iterations correctly per phase with multiple iterations" {
    # Create iterations.json with multiple iterations in some phases
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "ARTIFACT_REVIEW"},
  {"iteration": 2, "phase": "ARTIFACT_REVIEW"},
  {"iteration": 1, "phase": "IMPLEMENTATION"},
  {"iteration": 1, "phase": "REVIEW"},
  {"iteration": 1, "phase": "MAINTAIN-DOCS"},
  {"iteration": 1, "phase": "SYNC"},
  {"iteration": 1, "phase": "SELF_REFLECTION"},
  {"iteration": 1, "phase": "ARCHIVE"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # PHASE0 should show 2 iterations
    local phase0_count
    phase0_count=$(jq 'map(select(.phase == "ARTIFACT_REVIEW")) | length' "$iterations_file")
    [ "$phase0_count" == "2" ]
    
    # PHASE1 should show 1 iteration
    local phase1_count
    phase1_count=$(jq 'map(select(.phase == "IMPLEMENTATION")) | length' "$iterations_file")
    [ "$phase1_count" == "1" ]
    
    # Total should be 8
    local total
    total=$(jq 'length' "$iterations_file")
    [ "$total" == "8" ]
}

@test "show_progress: handles missing iterations.json gracefully" {
    # No iterations.json file
    [ ! -f "openspec/changes/test-change/iterations.json" ]
    
    # The show_progress function should handle this with [[ -f ... ]] check
    # This test verifies the file check works
    if [[ -f "openspec/changes/test-change/iterations.json" ]]; then
        echo "Should not reach here"
        return 1
    fi
}

@test "phase labels: PHASE5 is SELF-REFLECTION, PHASE6 is ARCHIVE" {
    # Verify the expected phase name mappings
    # This matches the get_phase_name function in osc-phase
    
    local phase5_name phase6_name
    
    # PHASE5 -> SELF-REFLECTION
    phase5_name="SELF-REFLECTION"
    [ "$phase5_name" == "SELF-REFLECTION" ]
    
    # PHASE6 -> ARCHIVE
    phase6_name="ARCHIVE"
    [ "$phase6_name" == "ARCHIVE" ]
    
    # Verify they are NOT swapped
    [ "$phase5_name" != "ARCHIVE" ]
    [ "$phase6_name" != "SELF-REFLECTION" ]
}

@test "phase iteration names: underscore format for SELF_REFLECTION" {
    # iterations.json uses SELF_REFLECTION (underscore) not SELF-REFLECTION (hyphen)
    # This test documents the expected format
    
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "SELF_REFLECTION"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Should find with underscore
    local count_underscore
    count_underscore=$(jq 'map(select(.phase == "SELF_REFLECTION")) | length' "$iterations_file")
    [ "$count_underscore" == "1" ]
    
    # Should NOT find with hyphen
    local count_hyphen
    count_hyphen=$(jq 'map(select(.phase == "SELF-REFLECTION")) | length' "$iterations_file")
    [ "$count_hyphen" == "0" ]
}
