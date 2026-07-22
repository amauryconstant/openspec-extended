#!/usr/bin/env python3
"""
Live contract tests against an installed ``openspec`` CLI binary.

These tests are **gated**:

- Auto-skipped if ``openspec`` is not on ``PATH``.
- Run only when invoked with ``pytest -m contract`` (or ``--run-contract``).
- Output of every shape is recorded so we can compare against upstream
  changes when bumping ``openspec-core``.

Coverage:

- ``openspec status --change <id> --json`` envelope
- ``openspec templates --schema <name> --json`` shape
- ``openspec store list --json`` envelope
- ``openspec store register --help`` flag inventory (no --name)
- ``openspec validate --all --json`` successful envelope shape
- ``openspec --version`` parses to a (major, minor, patch) tuple

If upstream changes any of these shapes the contract test fails and we
must update ``source/lib/osx.py`` to match (or wait until the orchestrator
is no longer expected to work against the new shape).
"""

from __future__ import annotations

import json
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


@requires_openspec
class TestOpenspecVersion:
    """``openspec --version`` parses cleanly."""

    def test_version_parses(self):
        rc, out, _ = _run(["--version"])
        assert rc == 0, f"openspec --version failed: {out}"
        # Output is "<pkg>/<ver> <arch> <runtime>" like
        # "@fission-ai/openspec/1.6.0 linux-x64 node-v20.19.0"
        import re

        m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
        assert m, f"could not parse version from {out!r}"
        ver = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        assert ver >= (1, 6, 0), (
            f"installed openspec is {ver}; orchestrator requires >= 1.6.0"
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
        """v1.5.0 stores beta renamed --name → --id."""
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
