#!/usr/bin/env bash
# Detect version bump type for root scripts (install.sh, bin/openspecx)
# Output: "type:reason:confidence" (e.g., "patch:whitespace_only:high")

set -euo pipefail

FILE="${1:-}"
if [[ -z "$FILE" ]]; then
  echo "error:missing_file:error"
  exit 1
fi

DIFF=$(git diff --cached "$FILE" 2>/dev/null || echo "")

if ! git show "HEAD:$FILE" &>/dev/null; then
  echo "minor:new_file:high"
  exit 0
fi

COMMIT_MSG=$(git log -1 --format=%s HEAD 2>/dev/null || echo "")

case "$COMMIT_MSG" in
  break:*|breaking:*|major:*|remove:*) echo "major:commit_prefix:high"; exit 0 ;;
  feat:*|feature:*|add:*|minor:*)      echo "minor:commit_prefix:high"; exit 0 ;;
  fix:*|bug:*|patch:*|correct:*|typo:*) echo "patch:commit_prefix:high"; exit 0 ;;
esac

if echo "$DIFF" | grep -qE '^-function\s|^\-\s*function\s|^-readonly\s+\w+\s*=\s*\(' | grep -vE 'readonly\s+(COLOR_|SCRIPT_VERSION)'; then
  echo "major:removed_function:high"
  exit 0
fi

if echo "$DIFF" | grep -qE '^\+function\s|^\+\s*function\s|^\+readonly\s+\w+\s*=\s*\(\)'; then
  echo "minor:new_function:medium"
  exit 0
fi

if echo "$DIFF" | grep -qE '^\s*-[a-z_]+\(\)\s*\{?\s*$'; then
  echo "major:removed_function:high"
  exit 0
fi

if echo "$DIFF" | grep -qE '^\s*\+[a-z_]+\(\)\s*\{?\s*$'; then
  echo "minor:new_function:medium"
  exit 0
fi

DIFF_CONTENT=$(echo "$DIFF" | grep -E '^[+-]' | grep -v '^[+-]{3}' | grep -vE '^[+-]\s*$')
if [[ -z "$DIFF_CONTENT" ]]; then
  echo "patch:whitespace_only:high"
  exit 0
fi

NON_WHITESPACE=$(echo "$DIFF_CONTENT" | grep -vE '^[+-]\s*#')
if [[ -z "$NON_WHITESPACE" ]]; then
  echo "patch:comment_only:medium"
  exit 0
fi

if echo "$DIFF" | grep -qE '^[+-].*(log_info|log_success|log_warn|log_error|echo\s+-e)'; then
  echo "patch:logging_change:medium"
  exit 0
fi

if echo "$DIFF" | grep -qE '^[+-].*^\s*(if|case|while|for)\s'; then
  echo "minor:control_flow:medium"
  exit 0
fi

CHANGED_LINE_COUNT=$(echo "$DIFF_CONTENT" | wc -l)
if [[ $CHANGED_LINE_COUNT -le 3 ]]; then
  echo "patch:minor_edit:medium"
  exit 0
fi

echo "patch:ambiguous:low"
