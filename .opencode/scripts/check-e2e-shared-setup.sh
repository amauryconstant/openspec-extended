#!/usr/bin/env bash
#MISE description="E2E bats regression guard: any tests/e2e/*.bats that defines its own setup_file() must also invoke setup_shared_e2e_dir (defined in tests/e2e/helpers/e2e-helpers.bash). Same rule for teardown_file/teardown_shared_e2e_dir. Prevents the 'cp: cannot stat /.opencode' failure mode where the per-file setup_file shadows the helper's and SHARED_E2E_DIR is never populated."
#USAGE flag "--check" help="Verify all E2E bats files that override setup_file/teardown_file properly chain the shared setup helpers (default; used by pre-commit)"

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

readonly E2E_DIR="$PROJECT_ROOT/tests/e2e"
readonly HELPER="$E2E_DIR/helpers/e2e-helpers.bash"

if [[ ! -d "$E2E_DIR" ]]; then
    echo "SKIP: $E2E_DIR does not exist"
    exit 0
fi

if [[ ! -f "$HELPER" ]]; then
    echo "FAIL: helper not found: $HELPER" >&2
    exit 1
fi

# Helper must expose the renamed functions for callers to chain.
for fn in setup_shared_e2e_dir teardown_shared_e2e_dir; do
    if ! grep -qE "^${fn}\s*\(\s*\)" "$HELPER"; then
        echo "FAIL: $HELPER does not define ${fn}()" >&2
        echo "      Regression-guarded bats files chain into this function." >&2
        exit 1
    fi
done

violations=0
while IFS= read -r -d '' bats_file; do
    defines_setup=false
    defines_teardown=false
    calls_setup_shared=false
    calls_teardown_shared=false

    if grep -qE '^[[:space:]]*setup_file[[:space:]]*\([[:space:]]*\)[[:space:]]*\{' "$bats_file"; then
        defines_setup=true
    fi
    if grep -qE '^[[:space:]]*teardown_file[[:space:]]*\([[:space:]]*\)[[:space:]]*\{' "$bats_file"; then
        defines_teardown=true
    fi
    grep -q 'setup_shared_e2e_dir' "$bats_file" && calls_setup_shared=true
    grep -q 'teardown_shared_e2e_dir' "$bats_file" && calls_teardown_shared=true

    if $defines_setup && ! $calls_setup_shared; then
        echo "FAIL: $bats_file defines setup_file() without invoking setup_shared_e2e_dir" >&2
        echo "      Without it, SHARED_E2E_DIR is never populated and setup_e2e_repo fails on /<missing>/.opencode." >&2
        violations=$((violations + 1))
    fi
    if $defines_teardown && ! $calls_teardown_shared; then
        echo "FAIL: $bats_file defines teardown_file() without invoking teardown_shared_e2e_dir" >&2
        echo "      Leaves /tmp/openspec-shared-* behind after the run." >&2
        violations=$((violations + 1))
    fi
done < <(find "$E2E_DIR" -maxdepth 1 -type f -name "*.bats" -print0)

if (( violations > 0 )); then
    echo "" >&2
    echo "Fix: chain the shared helpers from your setup_file / teardown_file," >&2
    echo "or remove the override entirely (the helper's defaults are fine for most files)." >&2
    exit 1
fi
echo "OK: every E2E bats file that overrides setup_file/teardown_file chains the shared helpers."
