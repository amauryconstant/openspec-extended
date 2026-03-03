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
    *"/skills/openspec-concepts/"*)
      resource_type="skills"; resource_name="openspec-concepts" ;;
    *"/skills/openspec-generate-changelog/"*)
      resource_type="skills"; resource_name="openspec-generate-changelog" ;;
    *"/skills/openspec-maintain-ai-docs/"*)
      resource_type="skills"; resource_name="openspec-maintain-ai-docs" ;;
    *"/skills/openspec-modify-artifacts/"*)
      resource_type="skills"; resource_name="openspec-modify-artifacts" ;;
    *"/skills/openspec-review-artifacts/"*)
      resource_type="skills"; resource_name="openspec-review-artifacts" ;;
    *"/skills/openspec-review-test-compliance/"*)
      resource_type="skills"; resource_name="openspec-review-test-compliance" ;;
    *"/agents/openspec-analyzer"*)
      resource_type="agents"; resource_name="openspec-analyzer" ;;
    *"/agents/openspec-builder"*)
      resource_type="agents"; resource_name="openspec-builder" ;;
    *"/agents/openspec-maintainer"*)
      resource_type="agents"; resource_name="openspec-maintainer" ;;
    *"/commands/openspec-phase0"*)
      resource_type="commands"; resource_name="openspec-phase0" ;;
    *"/commands/openspec-phase1"*)
      resource_type="commands"; resource_name="openspec-phase1" ;;
    *"/commands/openspec-phase2"*)
      resource_type="commands"; resource_name="openspec-phase2" ;;
    *"/commands/openspec-phase3"*)
      resource_type="commands"; resource_name="openspec-phase3" ;;
    *"/commands/openspec-phase4"*)
      resource_type="commands"; resource_name="openspec-phase4" ;;
    *"/commands/openspec-phase5"*)
      resource_type="commands"; resource_name="openspec-phase5" ;;
    *"/commands/openspec-phase6"*)
      resource_type="commands"; resource_name="openspec-phase6" ;;
    *"/commands/opsx-review"*|*"/commands/opsx/review"*)
      resource_type="commands"; resource_name="opsx-review" ;;
    *"/commands/opsx-modify"*|*"/commands/opsx/modify"*)
      resource_type="commands"; resource_name="opsx-modify" ;;
    *"/commands/opsx-verify-tests"*|*"/commands/opsx/verify-tests"*)
      resource_type="commands"; resource_name="opsx-verify-tests" ;;
    *"/commands/opsx-changelog"*|*"/commands/opsx/changelog"*)
      resource_type="commands"; resource_name="opsx-changelog" ;;
    *"/commands/opsx-maintain-docs"*|*"/commands/opsx/maintain-docs"*)
      resource_type="commands"; resource_name="opsx-maintain-docs" ;;
    *"/scripts/openspec-auto")
      resource_type="scripts"; resource_name="openspec-auto" ;;
    *"/scripts/lib/osc-common"*)
      resource_type="lib"; resource_name="osc-common" ;;
    *"/scripts/lib/osc-state"*)
      resource_type="lib"; resource_name="osc-state" ;;
    *"/scripts/lib/osc-ctx"*)
      resource_type="lib"; resource_name="osc-ctx" ;;
    *"/scripts/lib/osc-iterations"*)
      resource_type="lib"; resource_name="osc-iterations" ;;
    *"/scripts/lib/osc-log"*)
      resource_type="lib"; resource_name="osc-log" ;;
    *"/scripts/lib/osc-git"*)
      resource_type="lib"; resource_name="osc-git" ;;
    *"/scripts/lib/osc-baseline"*)
      resource_type="lib"; resource_name="osc-baseline" ;;
    *"/scripts/lib/osc-complete"*)
      resource_type="lib"; resource_name="osc-complete" ;;
    *"/scripts/lib/osc-phase"*)
      resource_type="lib"; resource_name="osc-phase" ;;
    *"/scripts/lib/osc-validate"*)
      resource_type="lib"; resource_name="osc-validate" ;;
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
