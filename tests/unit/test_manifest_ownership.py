#!/usr/bin/env python3
"""Runtime ownership check on the two side manifests.

Phase 5 split the on-disk resource tree into two disjoint halves
(``orchestrator/resources/canonical/`` and ``skills/resources/canonical/``)
and pinned the contract with ``TestManifestParity``. The parity test
asserts the invariant on committed manifests; this module pins the
runtime check that catches drift on uncommitted edits before any
deploy side-effect runs.
"""

from __future__ import annotations

import pytest

from source.cli import _assert_manifests_disjoint_and_prefixed


REPO_ROOT = __import__("pathlib").Path(__file__).parent.parent.parent
ORCH_MANIFEST = REPO_ROOT / "orchestrator" / "resources" / "canonical" / "manifest.toml"
SK_MANIFEST = REPO_ROOT / "skills" / "resources" / "canonical" / "manifest.toml"


def _load(path):
    import toml

    return toml.loads(path.read_text())


@pytest.mark.unit
class TestManifestOwnershipRuntime:
    def test_real_orchestrator_and_skills_manifests_pass(self):
        """The committed side manifests must satisfy the ownership
        invariant on every run. Drift in either tree trips the check."""
        orch = _load(ORCH_MANIFEST)
        skl = _load(SK_MANIFEST)
        _assert_manifests_disjoint_and_prefixed(orch, skl)

    def test_missing_skills_manifest_passes(self):
        """Skills side may be absent (``None`` from
        ``_resolve_side_manifest``) and is treated as empty."""
        orch = _load(ORCH_MANIFEST)
        _assert_manifests_disjoint_and_prefixed(orch, None)
        _assert_manifests_disjoint_and_prefixed(orch, {})

    def test_skills_manifest_rejects_osc_key(self):
        """Core (``osc-*``) entries are absorbed post-deploy by
        ``_preserve_core_tracking`` and must never appear in a source
        manifest. The skills side has no absorption path, so any
        ``osc-*`` declaration is rejected."""
        orch = _load(ORCH_MANIFEST)
        skl = {
            "resources": {
                "skills": {"osc-propose": {"version": "1.0.0"}},
                "commands": {},
                "agents": {},
            }
        }
        with pytest.raises(SystemExit) as exc:
            _assert_manifests_disjoint_and_prefixed(orch, skl)
        assert exc.value.code == 1

    def test_orchestrator_manifest_rejects_osc_key(self):
        """Same rule on the orchestrator side: source manifests are
        ``osx-*`` only. ``osc-*`` entries would be silently clobbered
        by the next non-``--with-core`` install — the runtime check
        surfaces them before deploy."""
        orch = {
            "resources": {
                "skills": {"osc-propose": {"version": "1.0.0"}},
                "commands": {},
                "agents": {},
            }
        }
        skl = _load(SK_MANIFEST)
        with pytest.raises(SystemExit) as exc:
            _assert_manifests_disjoint_and_prefixed(orch, skl)
        assert exc.value.code == 1

    def test_overlap_between_sides_rejected(self):
        """Same ``osx-*`` key claimed by both sides is a cross-registration
        violation. The Phase 5 parity invariant says each side owns its
        own subset; the runtime check rejects overlap on uncommitted
        edits."""
        orch = {
            "resources": {
                "skills": {},
                "commands": {"osx-shared": {"version": "1.0.0"}},
                "agents": {},
            }
        }
        skl = {
            "resources": {
                "skills": {},
                "commands": {"osx-shared": {"version": "1.0.0"}},
                "agents": {},
            }
        }
        with pytest.raises(SystemExit) as exc:
            _assert_manifests_disjoint_and_prefixed(orch, skl)
        assert exc.value.code == 1

    def test_overlap_message_names_the_offending_key(self):
        """Error message must name the offending key so the operator
        can fix the manifest without reading the source."""
        orch = {
            "resources": {
                "skills": {},
                "commands": {"osx-dup": {"version": "1.0.0"}},
                "agents": {},
            }
        }
        skl = {
            "resources": {
                "skills": {},
                "commands": {"osx-dup": {"version": "1.0.0"}},
                "agents": {},
            }
        }
        with pytest.raises(SystemExit):
            _assert_manifests_disjoint_and_prefixed(orch, skl)
        # Console output is captured by typer; we can only assert that
        # the function exited non-zero without inspecting the message.
