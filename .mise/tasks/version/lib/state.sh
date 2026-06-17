#!/usr/bin/env bash
# State file helpers for version tasks.
# Source this file from check / update. Do not run directly.

STATE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_PROJECT_ROOT="$(cd "$STATE_LIB_DIR/../../../.." && pwd)"
STATE_FILE="$STATE_PROJECT_ROOT/.mise/version-state.json"

# Write status + files array to the state file.
write_version_state() {
    local status="$1"
    local files_json="$2"
    mkdir -p "$(dirname "$STATE_FILE")"
    jq -n \
        --arg status "$status" \
        --argjson files "$files_json" \
        '{status: $status, files: $files}' > "$STATE_FILE"
}

# Echo the current status, or empty string if no state.
get_state_status() {
    [[ -f "$STATE_FILE" ]] || { return 0; }
    jq -r '.status // ""' "$STATE_FILE" 2>/dev/null
}

# Echo the files array as JSON, or "[]" if no state.
get_state_files() {
    [[ -f "$STATE_FILE" ]] || { printf '[]\n'; return 0; }
    jq -c '.files // []' "$STATE_FILE" 2>/dev/null
}
