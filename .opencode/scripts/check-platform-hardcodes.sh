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
    # Phase 2-pattern: catch per-adapter branches that hardcode a SPECIFIC
    # tool name on the new dispatch axes. Comparisons against the
    # *axis values* themselves ("flat", "skills-only", "claude_print",
    # "/", etc.) are legitimate dispatch and stay unflagged — they
    # enumerate the supported literals, not per-tool names.
    'adapter\.commands_style[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
    'adapter\.skill_prefix[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
    'adapter\.runner_kind[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
    # L1.5: cross_ref_prefix joined the axis family.
    'adapter\.cross_ref_prefix[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
    # L1.7: generic pattern covering the new fields added in L1.1, L1.3,
    # L1.4, L1.5, L1.6. Per-axis duplicates above stay so each new axis
    # also gets its own line for grep diagnostics.
    'adapter\.(ask_tool|cross_ref_prefix|runner_args|frontmatter_extras|install_hint)[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
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