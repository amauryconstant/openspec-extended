#!/usr/bin/env bash
# Shared functions for version tasks

readonly VERSION_STATE_FILE="${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo ".")}/.mise/version-state.json"

validate_semver() {
  local version="$1"
  if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid semver format: '$version' (expected X.Y.Z)" >&2
    return 1
  fi
}

get_version_yaml() {
  local content="$1"
  echo "$content" | grep -A2 "^metadata:" | grep "version:" | head -1 | sed 's/.*version: *["'\'']*\([^"'\'']*\)["'\'']*.*/\1/' || echo ""
}

get_version_bash() {
  local content="$1"
  echo "$content" | grep "^readonly SCRIPT_VERSION=" | head -1 | sed 's/^readonly SCRIPT_VERSION="\([^"]*\)"/\1/' || echo ""
}

get_version_from_file() {
  local file="$1"
  local content
  content=$(cat "$file" 2>/dev/null) || return 1
  
  if [[ "$file" == *.md ]]; then
    get_version_yaml "$content"
  else
    get_version_bash "$content"
  fi
}

bump_version() {
  local version="$1"
  local bump_type="$2"
  
  IFS='.' read -r major minor patch <<< "$version"
  
  case "$bump_type" in
    patch) echo "${major}.${minor}.$((patch + 1))" ;;
    minor) echo "${major}.$((minor + 1)).0" ;;
    major) echo "$((major + 1)).0.0" ;;
  esac
}

bump_priority() {
  local status="$1"
  case "$status" in
    needs_major) echo 3 ;;
    needs_minor) echo 2 ;;
    needs_patch) echo 1 ;;
    *) echo 0 ;;
  esac
}

highest_bump_type() {
  local statuses="$1"
  local highest="patch"
  local highest_priority=0
  
  for status in $statuses; do
    local priority
    priority=$(bump_priority "$status")
    if [[ $priority -gt $highest_priority ]]; then
      highest_priority=$priority
      highest=$(echo "$status" | sed 's/needs_//')
    fi
  done
  
  echo "$highest"
}

get_concept_from_path() {
  local path="$1"
  
  case "$path" in
    *"/openspec-concepts/"*|*"/opsx-concepts."*|*"/opsx/concepts."*)
      echo "concepts" ;;
    *"/openspec-generate-changelog/"*|*"/opsx-changelog."*|*"/opsx/changelog."*)
      echo "changelog" ;;
    *"/openspec-maintain-ai-docs/"*|*"/opsx-maintain-docs."*|*"/opsx/maintain-docs."*)
      echo "maintain-docs" ;;
    *"/openspec-modify-artifacts/"*|*"/opsx-modify."*|*"/opsx/modify."*)
      echo "modify" ;;
    *"/openspec-review-artifacts/"*|*"/opsx-review."*|*"/opsx/review."*)
      echo "review" ;;
    *"/openspec-review-test-compliance/"*|*"/opsx-verify-tests."*|*"/opsx/verify-tests."*)
      echo "verify-tests" ;;
    *"/scripts/openspec-auto")
      echo "openspec-auto" ;;
    *"/agents/openspec-analyzer"*)
      echo "openspec-analyzer" ;;
    *"/agents/openspec-builder"*)
      echo "openspec-builder" ;;
    *"/agents/openspec-maintainer"*)
      echo "openspec-maintainer" ;;
    *)
      echo ""
  esac
}

write_version_state() {
  local status="$1"
  local files_json="$2"
  
  cat > "$VERSION_STATE_FILE" << EOF
{
  "status": "$status",
  "files": $files_json,
  "timestamp": "$(date -Iseconds)"
}
EOF
}

read_version_state() {
  if [[ ! -f "$VERSION_STATE_FILE" ]]; then
    echo "Error: No state file found. Run 'mise run version:check' first." >&2
    return 1
  fi
  cat "$VERSION_STATE_FILE"
}

get_state_status() {
  read_version_state | jq -r '.status // "unknown"'
}

get_state_files() {
  read_version_state | jq -c '.files // []'
}
