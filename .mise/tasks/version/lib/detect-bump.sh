#!/usr/bin/env bash
# Detect version bump type from staged file diff
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

if echo "$DIFF" | grep -qE '^-export|^-function\s|^-class\s|^-readonly\s+\w+=.*require'; then
  echo "major:removed_code:high"
  exit 0
fi

if echo "$DIFF" | grep -qE '^\+export|^\+function\s|^\+class\s|^\+readonly\s+\w+=.*require'; then
  echo "minor:new_code:medium"
  exit 0
fi

if echo "$DIFF" | grep -qE '^\+##\s+\w|^\+###\s+\w'; then
  echo "minor:new_section:medium"
  exit 0
fi

if [[ "$FILE" == *.md ]]; then
  if echo "$DIFF" | grep -qE '^\+##|^\+###|^\+\*\*[^*]+\*\*:'; then
    echo "minor:doc_expansion:medium"
    exit 0
  fi
fi

DIFF_CONTENT=$(echo "$DIFF" | grep -E '^[+-]' | grep -v '^[+-]{3}' | grep -vE '^[+-]\s*$')
if [[ -z "$DIFF_CONTENT" ]]; then
  echo "patch:whitespace_only:high"
  exit 0
fi

NON_WHITESPACE=$(echo "$DIFF_CONTENT" | grep -vE '^[+-]\s*(#|//|/\*|\*|<!--|-->)')
if [[ -z "$NON_WHITESPACE" ]]; then
  echo "patch:comment_only:medium"
  exit 0
fi

if [[ "$FILE" == *.md ]]; then
  DOC_ONLY=$(echo "$DIFF_CONTENT" | grep -vE '^[+-](---|\s*name:|\s*description:|\s*license:|\s*metadata:|\s*author:|\s*version:)')
  if [[ -z "$DOC_ONLY" ]]; then
    echo "patch:metadata_only:medium"
    exit 0
  fi
fi

if echo "$DIFF" | grep -qE '^\+.*(catch|throw|Error|console\.|logger)'; then
  echo "patch:error_handling:medium"
  exit 0
fi

CHANGED_LINE_COUNT=$(echo "$DIFF_CONTENT" | wc -l)
if [[ $CHANGED_LINE_COUNT -le 3 ]]; then
  echo "patch:minor_edit:medium"
  exit 0
fi

echo "patch:ambiguous:low"
