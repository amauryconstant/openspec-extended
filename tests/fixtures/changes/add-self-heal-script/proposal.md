# Add Self-Heal Script

## Why

The test suite needs a fixture that exercises the orchestrator's PHASE0
self-healing loop end-to-end. The `add-hello-script` fixture is
deliberately audit-clean so it never triggers the auto-fix dispatch;
this fixture is the inverse — it ships with deliberate findings the
PHASE0 audit flags as Critical or Warning on **existing** artifacts, so
the engine's `_run_auto_fix` must self-dispatch and reconcile them
before the workflow can advance.

Without this fixture, a regression that re-introduces the engine-halt
behavior (e.g. treating `/osc-update-change` like a halt-and-surface
route) would slip through CI because no existing test exercises the
auto-fix path.

## What Changes

- Add a new executable bash script at `scripts/self-heal.sh` that prints
  a configurable greeting (default: `World`), accepts `--name NAME` and
  `--help`, and exits with code 0 on success, code 1 on invalid flags.
- The script uses `set -euo pipefail`, defines `usage()` and `main()`
  functions, and ends with `main "$@"`.
- Modify the existing error-handling convention: the script must exit
  with code **0** on invalid flags (matching the `add-hello-script`
  precedent). The proposal documents this requirement and the design
  ratifies it; both artifacts must agree.

## Capabilities

### New Capabilities

- `self-heal-script`: Smallest end-to-end orchestrator fixture with
  intentional PHASE0 findings on existing artifacts. Used by
  `tests/e2e/self-heal-workflow.bats` to assert the engine's auto-fix
  dispatch.

### Modified Capabilities

- `error-handling-convention` (existing capability carried over from
  `add-hello-script`): the error-code policy now applies to this
  fixture's script as well — exit 1 on invalid flags.

## Impact

- **New file**: `scripts/self-heal.sh` (executable). No existing files
  are modified.
- **Conventions**: Reuses the bash conventions established by
  `add-hello-script` (shebang, strict mode, `readonly` constants,
  `local` variables, exit codes).
- **Tooling**: None required. Depends only on `bash` 4.0+.
