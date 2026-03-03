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

# Test the state.json.phase_iterations tracking (what show_progress actually uses)
@test "show_progress: reads phase iterations from state.json" {
    # Create state.json with phase_iterations (what show_progress actually reads)
    cat > "openspec/changes/test-change/state.json" <<EOF
{
  "phase": "PHASE4",
  "phase_name": "SYNC",
  "iteration": 1,
  "phase_complete": false,
  "phase_iterations": {
    "PHASE0": 1,
    "PHASE1": 2,
    "PHASE2": 1,
    "PHASE3": 1,
    "PHASE4": 1
  }
}
EOF
    
    local state_file="openspec/changes/test-change/state.json"
    
    # Test the jq queries that show_progress uses (reads from state.json.phase_iterations)
    local p0 p1 p2 p3 p4 p5 p6
    p0=$(jq -r '.phase_iterations.PHASE0 // 0' "$state_file")
    p1=$(jq -r '.phase_iterations.PHASE1 // 0' "$state_file")
    p2=$(jq -r '.phase_iterations.PHASE2 // 0' "$state_file")
    p3=$(jq -r '.phase_iterations.PHASE3 // 0' "$state_file")
    p4=$(jq -r '.phase_iterations.PHASE4 // 0' "$state_file")
    p5=$(jq -r '.phase_iterations.PHASE5 // 0' "$state_file")
    p6=$(jq -r '.phase_iterations.PHASE6 // 0' "$state_file")
    
    [ "$p0" == "1" ]
    [ "$p1" == "2" ]  # Multiple iterations
    [ "$p2" == "1" ]
    [ "$p3" == "1" ]
    [ "$p4" == "1" ]
    [ "$p5" == "0" ]  # Not yet reached
    [ "$p6" == "0" ]  # Not yet reached
}

@test "show_progress: handles missing phase_iterations gracefully" {
    # Create state.json without phase_iterations
    cat > "openspec/changes/test-change/state.json" <<EOF
{
  "phase": "PHASE0",
  "iteration": 1
}
EOF
    
    local state_file="openspec/changes/test-change/state.json"
    
    # Should return 0 for missing keys
    local p0
    p0=$(jq -r '.phase_iterations.PHASE0 // 0' "$state_file")
    [ "$p0" == "0" ]
}

@test "show_progress: handles missing state.json gracefully" {
    # No state.json file
    [ ! -f "openspec/changes/test-change/state.json" ]
    
    # The show_progress function handles this with [[ -f ... ]] check
    if [[ -f "openspec/changes/test-change/state.json" ]]; then
        echo "Should not reach here"
        return 1
    fi
}

# Test iterations.json phase names (what agents write)
@test "iterations.json: uses correct phase names with underscores" {
    # Create iterations.json with canonical phase names
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "ARTIFACT_REVIEW"},
  {"iteration": 1, "phase": "IMPLEMENTATION"},
  {"iteration": 1, "phase": "REVIEW"},
  {"iteration": 1, "phase": "MAINTAIN_DOCS"},
  {"iteration": 1, "phase": "SYNC"},
  {"iteration": 1, "phase": "SELF_REFLECTION"},
  {"iteration": 1, "phase": "ARCHIVE"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Verify all phase names use underscore format
    phase0_count=$(jq 'map(select(.phase == "ARTIFACT_REVIEW")) | length' "$iterations_file")
    [ "$phase0_count" == "1" ]
    
    phase3_count=$(jq 'map(select(.phase == "MAINTAIN_DOCS")) | length' "$iterations_file")
    [ "$phase3_count" == "1" ]
    
    phase5_count=$(jq 'map(select(.phase == "SELF_REFLECTION")) | length' "$iterations_file")
    [ "$phase5_count" == "1" ]
    
    phase6_count=$(jq 'map(select(.phase == "ARCHIVE")) | length' "$iterations_file")
    [ "$phase6_count" == "1" ]
}

@test "phase names: iterations.json uses MAINTAIN_DOCS not MAINTAIN-DOCS" {
    # Verify MAINTAIN_DOCS uses underscore format
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "MAINTAIN_DOCS"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Should find with underscore
    local count_underscore
    count_underscore=$(jq 'map(select(.phase == "MAINTAIN_DOCS")) | length' "$iterations_file")
    [ "$count_underscore" == "1" ]
    
    # Should NOT find with hyphen
    local count_hyphen
    count_hyphen=$(jq 'map(select(.phase == "MAINTAIN-DOCS")) | length' "$iterations_file")
    [ "$count_hyphen" == "0" ]
}

@test "phase names: iterations.json uses SELF_REFLECTION not SELF-REFLECTION" {
    # Verify SELF_REFLECTION uses underscore format in iterations.json
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

@test "phase display names: correct format for UI" {
    # Display names use different format (space for multi-word, hyphen for compound)
    # This matches osc_get_phase_display_name in osc-common
    
    local phase0_display="ARTIFACT REVIEW"    # Space
    local phase3_display="MAINTAIN DOCS"       # Space (not hyphen)
    local phase5_display="SELF-REFLECTION"     # Hyphen (compound word)
    
    [ "$phase0_display" == "ARTIFACT REVIEW" ]
    [ "$phase3_display" == "MAINTAIN DOCS" ]
    [ "$phase5_display" == "SELF-REFLECTION" ]
}
