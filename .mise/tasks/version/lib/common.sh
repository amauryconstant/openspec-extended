#!/usr/bin/env bash
# Shared functions for version tasks

readonly VERSION_STATE_FILE="${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo ".")}/.mise/version-state.json"
readonly PROJECT_ROOT="${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || ".")}"

validate_semver() {
  local version="$1"
  if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid semver format: '$version' (expected X.Y.Z)" >&2
    return 1
  fi
}

get_manifest_for_path() {
  local path="$1"
  case "$path" in
    resources/opencode/*) echo "$PROJECT_ROOT/resources/opencode/manifest.json" ;;
    resources/claude/*)   echo "$PROJECT_ROOT/resources/claude/manifest.json" ;;
    *) echo "" ;;
  esac
}

get_platform_for_path() {
  local path="$1"
  case "$path" in
    resources/opencode/*) echo "opencode" ;;
    resources/claude/*)   echo "claude" ;;
    *) echo "" ;;
  esac
}

get_manifest_version() {
  local manifest="$1"
  echo "$manifest" | jq -r '.version // empty' 2>/dev/null || echo ""
}

get_resource_version() {
  local manifest="$1"
  local resource_type="$2"
  local resource_name="$3"
  echo "$manifest" | jq -r ".resources[\"$resource_type\"][\"$resource_name\"].version // empty" 2>/dev/null || echo ""
}

set_resource_version() {
  local manifest_file="$1"
  local resource_type="$2"
  local resource_name="$3"
  local version="$4"
  
  local tmp_file
  tmp_file=$(mktemp)
  jq ".resources[\"$resource_type\"][\"$resource_name\"].version = \"$version\"" "$manifest_file" > "$tmp_file"
  mv "$tmp_file" "$manifest_file"
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

get_resource_info_from_path() {
  local path="$1"
  local resource_type=""
  local resource_name=""
  
  case "$path" in
    *"/skills/osx-concepts/"*)
      resource_type="skills"; resource_name="osx-concepts" ;;
    *"/skills/osx-generate-changelog/"*)
      resource_type="skills"; resource_name="osx-generate-changelog" ;;
    *"/skills/osx-maintain-ai-docs/"*)
      resource_type="skills"; resource_name="osx-maintain-ai-docs" ;;
    *"/skills/osx-modify-artifacts/"*)
      resource_type="skills"; resource_name="osx-modify-artifacts" ;;
    *"/skills/osx-review-artifacts/"*)
      resource_type="skills"; resource_name="osx-review-artifacts" ;;
    *"/skills/osx-review-test-compliance/"*)
      resource_type="skills"; resource_name="osx-review-test-compliance" ;;
    *"/skills/osx-commit/"*)
      resource_type="skills"; resource_name="osx-commit" ;;
    *"/agents/osx-analyzer"*)
      resource_type="agents"; resource_name="osx-analyzer" ;;
    *"/agents/osx-builder"*)
      resource_type="agents"; resource_name="osx-builder" ;;
    *"/agents/osx-maintainer"*)
      resource_type="agents"; resource_name="osx-maintainer" ;;
    *"/commands/osx-phase0"*)
      resource_type="commands"; resource_name="osx-phase0" ;;
    *"/commands/osx-phase1"*)
      resource_type="commands"; resource_name="osx-phase1" ;;
    *"/commands/osx-phase2"*)
      resource_type="commands"; resource_name="osx-phase2" ;;
    *"/commands/osx-phase3"*)
      resource_type="commands"; resource_name="osx-phase3" ;;
    *"/commands/osx-phase4"*)
      resource_type="commands"; resource_name="osx-phase4" ;;
    *"/commands/osx-phase5"*)
      resource_type="commands"; resource_name="osx-phase5" ;;
    *"/commands/osx-phase6"*)
      resource_type="commands"; resource_name="osx-phase6" ;;
    *"/commands/osx-review"*|*"/commands/osx/review"*)
      resource_type="commands"; resource_name="osx-review" ;;
    *"/commands/osx-modify"*|*"/commands/osx/modify"*)
      resource_type="commands"; resource_name="osx-modify" ;;
    *"/commands/osx-verify-tests"*|*"/commands/osx/verify-tests"*)
      resource_type="commands"; resource_name="osx-verify-tests" ;;
    *"/commands/osx-changelog"*|*"/commands/osx/changelog"*)
      resource_type="commands"; resource_name="osx-changelog" ;;
    *"/commands/osx-maintain-docs"*|*"/commands/osx/maintain-docs"*)
      resource_type="commands"; resource_name="osx-maintain-docs" ;;
    *"/scripts/osx-orchestrate")
      resource_type="scripts"; resource_name="osx-orchestrate" ;;
    *"/scripts/lib/osx")
      resource_type="lib"; resource_name="osx" ;;
  esac
  
  if [[ -n "$resource_type" && -n "$resource_name" ]]; then
    echo "$resource_type:$resource_name"
  fi
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

get_script_version_from_file() {
  local file="$1"
  grep -m1 '^readonly SCRIPT_VERSION=' "$file" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/' || echo ""
}

get_script_version_from_git() {
  local path="$1"
  git show "HEAD:$path" 2>/dev/null | grep -m1 '^readonly SCRIPT_VERSION=' | sed 's/.*"\([^"]*\)".*/\1/' || echo ""
}

bump_script_version_in_file() {
  local file="$1"
  local new_version="$2"
  sed -i "s/^readonly SCRIPT_VERSION=\"[^\"]*\"/readonly SCRIPT_VERSION=\"$new_version\"/" "$file"
}

is_tracked_script() {
  local path="$1"
  [[ "$path" == "install.sh" || "$path" == "bin/openspecx" ]]
}
