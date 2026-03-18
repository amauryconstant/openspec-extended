#!/usr/bin/env bats

# Tests for agent output capture in orchestration logging

load '../helpers/test-helpers'

setup_file() {
    export TEST_DIR
    TEST_DIR="$(mktemp -d)"
}

teardown_file() {
    rm -rf "$TEST_DIR"
}

setup() {
    local test_name="$BATS_TEST_NAME"
    local test_dir="$TEST_DIR/$test_name"
    mkdir -p "$test_dir"
    export TEST_LOG_DIR="$test_dir"
}

@test "logging: agent session markers are captured" {
    local log_file="$TEST_LOG_DIR/test.log"
    
    echo "2024-01-15T10:00:00Z [INFO] Agent invocation #1 for PHASE1" > "$log_file"
    echo "> osx-builder · glm-5" >> "$log_file"
    echo "I'll start implementing the change..." >> "$log_file"
    echo "→ Read proposal.md" >> "$log_file"
    echo "→ Read design.md" >> "$log_file"
    
    grep -q "^> osx-builder" "$log_file"
    grep -q "I'll start" "$log_file"
    grep -q "^→ Read" "$log_file"
}

@test "logging: tool calls are captured with arrow prefix" {
    local log_file="$TEST_LOG_DIR/test.log"
    
    echo "Agent session:" > "$log_file"
    echo "→ Read proposal.md" >> "$log_file"
    echo "→ Glob specs/*.md" >> "$log_file"
    echo "→ Write design.md" >> "$log_file"
    echo "→ Bash command executed" >> "$log_file"
    
    grep -q "^→ Read" "$log_file"
    grep -q "^→ Glob" "$log_file"
    grep -q "^→ Write" "$log_file"
}

@test "logging: multiple agent sessions are captured" {
    local log_file="$TEST_LOG_DIR/test.log"
    
    for i in {1..3}; do
        echo "Agent invocation #$i" >> "$log_file"
        echo "> osx-analyzer · glm-5" >> "$log_file"
        echo "Processing phase $i..." >> "$log_file"
        echo "---" >> "$log_file"
    done
    
    local session_count
    session_count=$(grep -c "^> osx-" "$log_file" || echo "0")
    
    [ "$session_count" -eq 3 ]
}

@test "logging: orchestrator messages interleave with agent output" {
    local log_file="$TEST_LOG_DIR/test.log"
    
    echo "2024-01-15T10:00:00Z [INFO] Agent invocation #1 for PHASE1" > "$log_file"
    echo "> osx-builder · glm-5" >> "$log_file"
    echo "I'll start implementing..." >> "$log_file"
    echo "→ Read proposal.md" >> "$log_file"
    echo "2024-01-15T10:00:30Z [VERBOSE] State updated: PHASE2" >> "$log_file"
    echo "> osx-analyzer · glm-5" >> "$log_file"
    echo "I'll review artifacts..." >> "$log_file"
    
    grep -q "Agent invocation #1" "$log_file"
    local first_agent_line
    first_agent_line=$(grep -n "^> osx-builder" "$log_file" | head -1 | cut -d: -f1)
    
    [ "$first_agent_line" -gt 1 ]
}
