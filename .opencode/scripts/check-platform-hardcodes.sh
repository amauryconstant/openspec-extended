#!/usr/bin/env bash
#MISE description="Phase 1G regression guard: fail if any cli.py / runner.py / engine.py / lib/osx.py hardcodes opencode/claude in a conditional or direct dict access."
#USAGE flag "--check" help="Verify no platform hardcodes slipped in (default; used by pre-commit)"

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

readonly -a SCAN_DIRS=(
    "$PROJECT_ROOT/orchestrator/source/cli.py"
    "$PROJECT_ROOT/orchestrator/source/orchestrator"
    "$PROJECT_ROOT/orchestrator/source/lib"
)

# Files exempt from the check (where literals are legitimate).
readonly EXCLUDE_PATTERN='^/tmp/|^.*/tests/|^.*/orchestrator/core/|^.*/orchestrator/resources/|^.*/skills/resources/|^.*/.opencode/|^.*/source/tools\.py$|^.*/AGENTS\.md$|^.*/README\.md$|^.*/CHANGELOG\.md$'

# Patterns indicating a hardcoded platform literal in code.
readonly -a PATTERNS=(
    'if[[:space:]].*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
    'elif[[:space:]].*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
    '[[:space:]]!=[^=].*["'"'"'](opencode|claude)["'"'"']'
    '[[:space:]]in[[:space:]]+\[(.*["'"'"'](opencode|claude)["'"'"'])'
    'TOOL_DIRS\[["'"'"'](opencode|claude)["'"'"']\]'
    'PLATFORM_TOKENS\[["'"'"'](opencode|claude)["'"'"']\]'
)

violations=0
for path in "${SCAN_DIRS[@]}"; do
    [[ -e "$path" ]] || continue
    while IFS= read -r -d '' file; do
        [[ "$file" =~ $EXCLUDE_PATTERN ]] && continue
        for pattern in "${PATTERNS[@]}"; do
            matches=$(grep -nE "$pattern" "$file" || true)
            if [[ -n "$matches" ]]; then
                echo "FAIL: $file" >&2
                echo "$matches" | sed 's/^/  /' >&2
                violations=$((violations + 1))
            fi
        done
    done < <(find "$path" -type f -name "*.py" -print0)
done

if (( violations > 0 )); then
    echo "" >&2
    echo "Add a ToolAdapter entry to source/tools.py:REGISTRY instead." >&2
    echo "If this is a false positive, see .opencode/scripts/check-platform-hardcodes.sh." >&2
    exit 1
fi
echo "OK: no platform hardcodes detected."