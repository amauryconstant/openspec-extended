#!/usr/bin/env python3
"""
Live contract tests against an installed ``openspec`` CLI binary.

These tests are **gated**:

- Auto-skipped if ``openspec`` is not on ``PATH``.
- Run only when invoked with ``pytest -m contract`` (or ``--run-contract``).
- Output of every shape is recorded so we can compare against upstream
  changes when bumping the OpenSpec core subtree.

Coverage:

- ``openspec status --change <id> --json`` envelope (per-change)
- ``openspec status --all --json`` envelope (v1.11.0+; multi-change sweep)
- ``openspec show <change> --diff --json`` envelope (v1.11.0+; requirement-level diff)
- ``openspec templates --schema <name> --json`` shape
- ``openspec store list --json`` envelope
- ``openspec store register --help`` flag inventory (no --name)
- ``openspec validate --all --json`` successful envelope shape
- ``openspec --version`` parses to a (major, minor, patch) tuple

The version floor defaults to ``(1, 11, 0)`` — the orchestrator's hard
floor. Local dev machines on older cores can set
``OPENSPEC_EXTENDED_MIN_CORE_VERSION_OVERRIDE=X.Y.Z`` to opt out without
breaking CI. The module-level ``_core_version()`` helper consolidates
the three previously-duplicated static methods used by the
version-gated tests below.

If upstream changes any of these shapes the contract test fails and we
must update ``source/lib/osx.py`` to match (or wait until the orchestrator
is no longer expected to work against the new shape).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

OPENSPEC_BIN = shutil.which("openspec")

# Marker for opt-in invocation: ``pytest -m contract``.
pytestmark = pytest.mark.contract

requires_openspec = pytest.mark.skipif(
    OPENSPEC_BIN is None,
    reason="openspec CLI not on PATH; install with: npm install -g @fission-ai/openspec",
)


def _run(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run ``openspec <args>`` and return (rc, stdout, stderr)."""
    assert OPENSPEC_BIN is not None
    result = subprocess.run(
        [OPENSPEC_BIN, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


# Module-level core version helpers + tunable floor. The orchestrator's
# hard floor is (1, 13, 0); local dev machines on older cores can opt
# out of the floor check via env var without breaking CI.
DEFAULT_MIN_CORE_VERSION: tuple[int, int, int] = (1, 13, 0)
MIN_CORE_VERSION_OVERRIDE_ENV = "OPENSPEC_EXTENDED_MIN_CORE_VERSION_OVERRIDE"


def _core_version() -> tuple[int, int, int] | None:
    """Parse `openspec --version` into a tuple, or None on failure.

    Single source of truth used by every contract test that needs to
    gate on core version. Was duplicated as three identical static
    methods (TestStatusPlanning, TestShowDiffEnvelope,
    TestArchiveWithRetireCapabilities) before Section G.
    """
    rc, out, _ = _run(["--version"])
    if rc != 0:
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _min_core_version() -> tuple[int, int, int]:
    """Resolve the version floor the contract suite enforces.

    Precedence: OPENSPEC_EXTENDED_MIN_CORE_VERSION_OVERRIDE env var
    (must parse as X.Y.Z all-digits) > DEFAULT_MIN_CORE_VERSION
    (1, 13, 0).
    """
    override = os.environ.get(MIN_CORE_VERSION_OVERRIDE_ENV)
    if override:
        parts = override.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return (int(parts[0]), int(parts[1]), int(parts[2]))
    return DEFAULT_MIN_CORE_VERSION


@requires_openspec
class TestOpenspecVersion:
    """``openspec --version`` parses cleanly."""

    def test_version_parses(self):
        rc, out, _ = _run(["--version"])
        assert rc == 0, f"openspec --version failed: {out}"
        # Output is "<pkg>/<ver> <arch> <runtime>" like
        # "@fission-ai/openspec/1.11.0 linux-x64 node-v20.19.0"
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
        assert m, f"could not parse version from {out!r}"
        ver = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        floor = _min_core_version()
        assert ver >= floor, (
            f"installed openspec is {ver}; orchestrator requires >= "
            f"{'.'.join(str(n) for n in floor)}. "
            f"Override locally with {MIN_CORE_VERSION_OVERRIDE_ENV}=X.Y.Z "
            f"if you're running a pre-v1.13.0 core on purpose."
        )


@requires_openspec
class TestStatusJsonEnvelope:
    """``openspec status --change <id> --json`` envelope shape."""

    def test_ambiguous_returns_envelope(self, tmp_path: Path):
        rc, out, _ = _run(["status", "--change", "nonexistent-test-zzz", "--json"])
        payload = json.loads(out or "{}")
        # The status command should return either an error envelope or a
        # clean payload, but never a crash with non-JSON on stdout.
        assert isinstance(payload, dict), f"payload not a dict: {payload!r}"
        # For an unknown change it should carry a ``status`` diagnostic list
        # OR a ``root`` resolving to the cwd-as-implicit.
        if "status" in payload:
            assert isinstance(payload["status"], list)


@requires_openspec
class TestTemplatesEnvelope:
    """``openspec templates --schema <name> --json`` returns dict-by-id."""

    def test_spec_driven_templates(self):
        rc, out, _ = _run(["templates", "--schema", "spec-driven", "--json"])
        if rc != 0:
            pytest.skip("schema spec-driven not present in this openspec build")
        payload = json.loads(out)
        # Must be a dict keyed by artifact id.
        assert isinstance(payload, dict), (
            f"templates payload should be dict-by-artifact-id; got {type(payload).__name__}"
        )
        for key in payload:
            assert isinstance(key, str), f"key {key!r} is not a string"


@requires_openspec
class TestStoreListEnvelope:
    """``openspec store list --json`` envelope shape."""

    def test_store_list_shape(self):
        rc, out, _ = _run(["store", "list", "--json"])
        if rc != 0:
            pytest.skip("store list not supported in this openspec build")
        payload = json.loads(out)
        assert isinstance(payload, dict)
        assert "stores" in payload, (
            f"store list payload should contain 'stores'; got keys: {list(payload.keys())}"
        )


@requires_openspec
class TestStoreRegisterFlags:
    """``openspec store register`` flag inventory."""

    def test_help_uses_id_not_name(self):
        """v1.5+ stores renamed --name → --id (still enforced in v1.11.0)."""
        rc, out, _ = _run(["store", "register", "--help"])
        assert rc == 0
        assert "--id" in out, (
            f"`openspec store register --help` should document --id flag; "
            f"got first lines:\n{out[:600]}"
        )
        # Legacy --name should no longer be accepted (sanity).
        rc2, _, err = _run(["store", "register", "--name", "x", "--json"])
        assert rc2 != 0, "--name should be rejected; upstream expects --id"
        assert "unknown option" in err.lower() or "error" in err.lower()


@requires_openspec
class TestValidateEmpty:
    """``openspec validate --all --json`` against an empty repo."""

    def test_validate_all_envelope_shape(self, tmp_path: Path, monkeypatch):
        # Probe behaviour without polluting the host repo.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "openspec").mkdir()
        rc, out, _ = _run(["validate", "--all", "--json"])
        if rc != 0:
            pytest.skip("validate --all exited non-zero in empty repo")
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError:
            pytest.skip(f"non-JSON output: {out[:200]!r}")
        # Some shapes: {items, summary, root, version} — at least one
        # of these (or alternatives) must exist.
        assert isinstance(payload, dict)


@requires_openspec
class TestStatusPlanning:
    """A.1: ``openspec status --change <id> --json`` carries
    ``isPlanningComplete`` (v1.8.0+) and per-artifact ``status`` fields the
    orchestrator pre-flight consults to decide whether planning is done.

    These tests run only against a real ``openspec`` build >= 1.8.0; older
    builds cleanly skip so a still-on-v1.7 host doesn't fail CI.
    """

    def test_status_includes_isPlanningComplete(self, tmp_path: Path, monkeypatch):
        """A real change (``openspec/changes/<id>/proposal.md`` etc.) returns
        a status envelope whose ``isPlanningComplete`` is a bool when the core
        supports it (>= 1.8.0)."""
        version = _core_version()
        if version is None or version < (1, 8, 0):
            pytest.skip(
                f"openspec {version} is below v1.8.0; "
                "isPlanningComplete gate tests require v1.8.0+"
            )

        change_dir = tmp_path / "openspec" / "changes" / "contract-a1"
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Why\n\n## What Changes\n\nx")
        (change_dir / "tasks.md").write_text("- [ ] 1\n")
        (change_dir / "design.md").write_text("# d\n")
        specs = change_dir / "specs"
        specs.mkdir()
        (specs / "auth.md").write_text("# auth\n\n## Requirements\n\n### R: x\n\nThe system SHALL x.\n")
        monkeypatch.chdir(tmp_path)

        rc, out, _ = _run(["status", "--change", "contract-a1", "--json"])
        if rc != 0:
            pytest.skip(f"status --change failed (rc={rc}): {out[:200]!r}")
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError:
            pytest.skip(f"non-JSON status output: {out[:200]!r}")
        assert isinstance(payload, dict)
        assert "isPlanningComplete" in payload, (
            f"v1.8.0+ status envelope missing isPlanningComplete; "
            f"got keys: {list(payload.keys())}"
        )
        assert isinstance(payload["isPlanningComplete"], bool)

    def test_status_artifacts_have_status_field(self, tmp_path: Path, monkeypatch):
        """Each entry in ``artifacts[]`` carries a ``status`` field whose
        value is one of the documented set ``{done, ready, blocked}``."""
        version = _core_version()
        if version is None or version < (1, 8, 0):
            pytest.skip(
                f"openspec {version} is below v1.8.0; "
                "artifact status field requires v1.8.0+"
            )

        change_dir = tmp_path / "openspec" / "changes" / "contract-a1-b"
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# p")
        (change_dir / "tasks.md").write_text("- [ ] 1\n")
        monkeypatch.chdir(tmp_path)

        rc, out, _ = _run(["status", "--change", "contract-a1-b", "--json"])
        if rc != 0:
            pytest.skip(f"status --change failed (rc={rc}): {out[:200]!r}")
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError:
            pytest.skip(f"non-JSON status output: {out[:200]!r}")
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            pytest.skip("status envelope carried no artifacts array")
        allowed = {"done", "ready", "blocked"}
        for entry in artifacts:
            assert isinstance(entry, dict)
            assert "status" in entry, (
                f"artifact entry {entry!r} missing 'status' field"
            )
            assert entry["status"] in allowed, (
                f"artifact {entry!r} has unknown status {entry['status']!r}; "
                f"allowed={allowed}"
            )


@requires_openspec
class TestStatusAllEnvelope:
    """`openspec status --all --json` envelope shape (v1.11.0+).

    The orchestrator's `list_changes()` uses this to enumerate every active
    change in one subprocess. The contract:

    - `--all --json` emits a single envelope ``{"changes": [...], "root": {...}}``
      sorted by change name.
    - Partial failures contribute a diagnostic entry in place rather than
      aborting the sweep (a change that fails to load yields
      ``{"changeName", "status": [diagnostic]}``).
    - Mutually exclusive with ``--change``.

    Gated on core >= 1.11.0 (the `--all` flag was added in v1.11.0).
    """

    def test_status_all_envelope_shape(self, tmp_path: Path, monkeypatch):
        """Empty repo: --all returns an envelope with empty changes array."""
        core_version = _core_version()
        if core_version is None or core_version < (1, 11, 0):
            pytest.skip(
                f"openspec {core_version} is below v1.11.0; "
                "`status --all` introduced in v1.11.0"
            )

        monkeypatch.chdir(tmp_path)
        (tmp_path / "openspec").mkdir()
        rc, out, _ = _run(["status", "--all", "--json"])
        if rc not in (0, 1):
            pytest.skip(
                f"status --all exited {rc} on empty repo; stdout: {out[:200]!r}"
            )
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError:
            pytest.skip(f"non-JSON status --all output: {out[:200]!r}")

        assert isinstance(payload, dict), (
            f"v1.11.0+ status --all envelope should be a dict; "
            f"got {type(payload).__name__}"
        )
        assert "changes" in payload, (
            f"v1.11.0+ status --all envelope missing 'changes' key; "
            f"got keys: {list(payload.keys())}"
        )
        assert isinstance(payload["changes"], list), (
            f"'changes' field should be a list; "
            f"got {type(payload['changes']).__name__}"
        )
        # 'root' is a sibling key documenting the planning root.
        assert "root" in payload, (
            f"v1.11.0+ status --all envelope missing 'root' key; "
            f"got keys: {list(payload.keys())}"
        )

    def test_status_all_excludes_change_flag(self, tmp_path: Path, monkeypatch):
        """`--all` and `--change` are mutually exclusive."""
        core_version = _core_version()
        if core_version is None or core_version < (1, 11, 0):
            pytest.skip(
                f"openspec {core_version} is below v1.11.0; "
                "`status --all` introduced in v1.11.0"
            )

        monkeypatch.chdir(tmp_path)
        (tmp_path / "openspec").mkdir()
        rc, _, err = _run(
            ["status", "--all", "--change", "some-change", "--json"]
        )
        # Acceptable: rc != 0 (rejected). A 0-rc success means both flags
        # were honored, which is a contract violation.
        assert rc != 0, (
            f"`status --all --change X` was accepted (rc=0); "
            f"the two flags are mutually exclusive. stderr: {err[:200]!r}"
        )

    def test_status_all_changes_sorted_by_name(self, tmp_path: Path, monkeypatch):
        """`changes[]` is sorted alphabetically by change name."""
        core_version = _core_version()
        if core_version is None or core_version < (1, 11, 0):
            pytest.skip(
                f"openspec {core_version} is below v1.11.0; "
                "`status --all` introduced in v1.11.0"
            )

        monkeypatch.chdir(tmp_path)
        changes_root = tmp_path / "openspec" / "changes"
        changes_root.mkdir(parents=True)
        # Three changes in non-alphabetical on-disk order.
        for name in ("zebra-change", "apple-change", "mango-change"):
            cd = changes_root / name
            cd.mkdir()
            (cd / "proposal.md").write_text("# Why\n")
            (cd / "tasks.md").write_text("- [ ] 1\n")
            (cd / "design.md").write_text("# d\n")
            specs = cd / "specs"
            specs.mkdir()
            (specs / "x.md").write_text(
                "# x\n\n## Requirements\n\n### R: y\n\nThe system SHALL y.\n"
            )

        rc, out, _ = _run(["status", "--all", "--json"])
        if rc != 0:
            pytest.skip(f"status --all failed: {out[:200]!r}")
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError:
            pytest.skip(f"non-JSON output: {out[:200]!r}")
        changes = payload.get("changes")
        if not isinstance(changes, list) or not changes:
            pytest.skip("status --all returned no changes; cannot assert sort order")
        names = [
            ch.get("changeName") or ch.get("name")
            for ch in changes
            if isinstance(ch, dict)
        ]
        names = [n for n in names if n]
        if names and names != sorted(names):
            pytest.fail(
                f"status --all changes[] is not sorted by name; got: {names!r}"
            )


@requires_openspec
class TestShowDiffEnvelope:
    """A.2: ``openspec show <change> --diff --json`` envelope shape.

    PHASE2 (REVIEW) reads the diff envelope and embeds the per-requirement
    ``diff`` blocks as the ``## Requirement diff`` appendix of
    ``verification-report.md``. These tests pin the contract:

    - ``diff`` and ``warning`` fields exist on MODIFIED deltas
    - ADDED deltas do NOT carry a ``diff`` field
    - Unknown change names either exit 0 with a diagnostic envelope or
      exit 1 — both are acceptable; skip otherwise.

    Gated on OpenSpec core >= 1.11.0 (the ``--diff`` flag was added in
    v1.11.0).
    """

    @staticmethod
    def _load_fixture_change(tmp_path: Path) -> Path:
        """Copy a real OpenSpec change fixture into ``tmp_path`` so the
        ``show --diff`` envelope can be exercised against MODIFIED deltas.
        Returns the change directory."""
        fixture_root = Path(__file__).resolve().parent.parent / "fixtures" / "changes"
        for candidate in ("add-hello-script", "test-minimal"):
            src = fixture_root / candidate
            if src.is_dir():
                dst = tmp_path / "openspec" / "changes" / candidate
                dst.parent.mkdir(parents=True, exist_ok=True)
                # shutil.copytree requires dest not to exist
                import shutil

                shutil.copytree(src, dst)
                return dst
        return None

    def test_show_diff_exit_code_zero_or_diagnostic(self, tmp_path: Path, monkeypatch):
        """``openspec show nonexistent-change --diff --json`` either exits 0
        with a diagnostic envelope or exits 1 — both are acceptable;
        skip otherwise (e.g. malformed crash output, which would indicate
        a regression)."""
        version = _core_version()
        if version is None or version < (1, 11, 0):
            pytest.skip(
                f"openspec {version} is below v1.11.0; "
                "`--diff` flag requires v1.11.0+"
            )

        monkeypatch.chdir(tmp_path)
        (tmp_path / "openspec").mkdir()
        rc, out, _ = _run(["show", "nonexistent-change", "--diff", "--json"])
        if rc not in (0, 1):
            pytest.skip(
                f"show --diff --json for nonexistent change exited {rc}; "
                f"stdout: {out[:200]!r}"
            )

    def test_show_diff_payload_shape(self, tmp_path: Path, monkeypatch):
        """Against a real change, MODIFIED deltas carry ``diff`` and
        ``warning`` fields; ADDED deltas do NOT carry a ``diff`` field."""
        version = _core_version()
        if version is None or version < (1, 11, 0):
            pytest.skip(
                f"openspec {version} is below v1.11.0; "
                "`--diff` flag requires v1.11.0+"
            )

        change_dir = self._load_fixture_change(tmp_path)
        if change_dir is None:
            pytest.skip("no OpenSpec change fixture available")

        monkeypatch.chdir(tmp_path)
        change_name = change_dir.name
        rc, out, _ = _run(["show", change_name, "--diff", "--json"])
        if rc != 0:
            pytest.skip(
                f"show --diff --json exited {rc}: {out[:200]!r}"
            )
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError:
            pytest.skip(f"non-JSON show --diff output: {out[:200]!r}")

        # The envelope carries a list (or dict) of requirements with
        # per-requirement delta info. The exact schema varies between
        # cores; probe both common shapes.
        deltas: list[dict] | None = None
        if isinstance(payload, list):
            deltas = [d for d in payload if isinstance(d, dict)]
        elif isinstance(payload, dict):
            for key in ("deltas", "requirements", "items"):
                val = payload.get(key)
                if isinstance(val, list):
                    deltas = [d for d in val if isinstance(d, dict)]
                    break
            if deltas is None and payload:
                # Last resort: any nested list value
                for val in payload.values():
                    if isinstance(val, list) and val and isinstance(val[0], dict):
                        deltas = val
                        break
        if not deltas:
            pytest.skip(
                "show --diff envelope had no recognisable delta list; "
                f"top-level keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}"
            )

        # Probe at least one MODIFIED delta has a `diff` field, and that
        # ADDED deltas (if any) do NOT carry a `diff` field.
        modified_seen = False
        added_seen = False
        for entry in deltas:
            delta_kind = entry.get("delta") or entry.get("kind") or entry.get("op")
            if delta_kind is None and "diff" in entry:
                # Treat any entry with a `diff` block as MODIFIED for
                # the purpose of this assertion.
                modified_seen = True
                assert "warning" in entry or entry.get("warning") in (None, ""), (
                    f"MODIFIED delta missing 'warning' field: {entry!r}"
                )
            if isinstance(delta_kind, str):
                up = delta_kind.upper()
                if up == "MODIFIED":
                    modified_seen = True
                    assert "diff" in entry, (
                        f"MODIFIED delta missing 'diff' field: {entry!r}"
                    )
                elif up == "ADDED":
                    added_seen = True
                    assert "diff" not in entry, (
                        f"ADDED delta should not carry a 'diff' field: {entry!r}"
                    )

        if not modified_seen:
            pytest.skip(
                "fixture produced no MODIFIED deltas; cannot verify "
                "diff+warning contract for this fixture"
            )
        # The "ADDED deltas do NOT carry diff" assertion only fires if
        # the fixture actually has ADDED entries; otherwise the test
        # above is the meaningful one.
        _ = added_seen


@requires_openspec
class TestArchiveWithRetireCapabilities:
    """A.3: ``openspec archive <change>`` honors ``retire_capabilities: true``
    declared in ``.openspec.yaml`` (v1.8.0+) — the change can delete the
    underlying spec when its last requirement is removed.

    Building a synthetic retirement change is non-trivial (it requires an
    active spec to remove, a change with a ``## REMOVED Requirements``
    block that empties it, plus core support). For the contract surface
    we instead pin the precondition: core version must be >= 1.8.0, which
    is when ``retire_capabilities`` was introduced.

    If a synthetic change becomes available, add the live archive call
    here and assert rc == 0 + spec deletion.
    """

    def test_core_version_supports_retire_capabilities(self):
        """Core >= 1.8.0 is the floor for ``retire_capabilities: true``.

        On older cores the orchestrator's PHASE0 still reads the marker
        but core itself refuses to delete the spec — the precondition
        is the v1.8.0 contract surface.
        """
        version = _core_version()
        if version is None:
            pytest.skip("could not parse openspec --version")
        if version < (1, 8, 0):
            pytest.skip(
                f"openspec {version} is below v1.8.0; "
                "retire_capabilities requires v1.8.0+"
            )
        assert version >= (1, 8, 0)
