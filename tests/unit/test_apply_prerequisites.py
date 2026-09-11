#!/usr/bin/env python3
"""Tests for ``fetch_apply_prerequisites`` (v1.13.0+ consumer).

OpenSpec v1.13.0 added the ``missingPrerequisites`` array to the
``openspec instructions apply --change <id> --json`` envelope. The array
names the **full build-order chain** for an apply whose ``applyRequires``
set is not yet satisfied — not just the first hop. PHASE1 logs the chain
in the decision log; logging is informational, not blocking.

These tests pin the in-process reader (``fetch_apply_prerequisites``).
The CLI surface (PHASE1 logging) is covered by
``tests/unit/test_resource_contract.py::TestOrchestratorContracts``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from source.lib import osx as osx_lib
from source.lib.osx import OSXError, fetch_apply_prerequisites


@pytest.fixture
def mock_instructions(monkeypatch):
    """Mock ``fetch_instructions`` so we can drive ``fetch_apply_prerequisites``
    without spawning ``openspec``.

    Stores the payload the mocked helper returns and the kwargs it was
    called with; tests set ``captured["payload"]`` to whatever shape the
    v1.13.0 envelope (or older-core envelope) would have.
    """
    captured: dict = {}

    def _fake(operation, change_id, *, store=None):
        captured["operation"] = operation
        captured["change_id"] = change_id
        captured["store"] = store
        return captured.get("payload", {})

    monkeypatch.setattr(osx_lib, "fetch_instructions", _fake)
    return captured


@pytest.mark.unit
class TestFetchApplyPrerequisites:
    """A.8 (v1.13.0+): the in-process reader for the
    ``missingPrerequisites`` field on ``openspec instructions apply --json``.
    """

    def test_empty_chain_returns_empty_list(self, mock_instructions) -> None:
        """Apply-ready: ``missingPrerequisites`` is present but empty."""
        mock_instructions["payload"] = {"missingPrerequisites": []}
        result = fetch_apply_prerequisites("add-auth")
        assert result == []
        assert mock_instructions["operation"] == "apply"
        assert mock_instructions["change_id"] == "add-auth"

    def test_non_empty_chain_returns_list(self, mock_instructions) -> None:
        """Apply blocked: ``missingPrerequisites`` carries the full chain."""
        mock_instructions["payload"] = {
            "missingPrerequisites": ["proposal", "specs", "tasks"],
        }
        result = fetch_apply_prerequisites("add-auth")
        assert result == ["proposal", "specs", "tasks"]

    def test_field_absent_returns_none(self, mock_instructions) -> None:
        """Older core (< v1.13.0): the field is absent; the helper returns
        ``None`` so consumers can distinguish "feature unavailable" from
        "apply-ready on a newer core"."""
        mock_instructions["payload"] = {"context": "x", "operationGuidance": []}
        assert fetch_apply_prerequisites("add-auth") is None

    def test_non_string_entries_are_filtered(self, mock_instructions) -> None:
        """Defensive: non-string entries (e.g. ``None`` from upstream bugs)
        are silently dropped rather than poisoning the returned list."""
        mock_instructions["payload"] = {
            "missingPrerequisites": ["proposal", None, 42, "tasks", {"x": 1}],
        }
        assert fetch_apply_prerequisites("add-auth") == ["proposal", "tasks"]

    def test_non_list_field_returns_none(self, mock_instructions) -> None:
        """Defensive: a non-list ``missingPrerequisites`` (e.g. core bug)
        returns ``None`` rather than raising — the helper never raises."""
        mock_instructions["payload"] = {"missingPrerequisites": "proposal"}
        assert fetch_apply_prerequisites("add-auth") is None

    def test_non_dict_envelope_returns_none(self, mock_instructions) -> None:
        """Defensive: a non-dict envelope (e.g. core emitted a bare list)
        returns ``None`` rather than raising."""
        mock_instructions["payload"] = ["not", "a", "dict"]
        assert fetch_apply_prerequisites("add-auth") is None

    def test_cli_failure_returns_none(self, monkeypatch) -> None:
        """``openspec instructions apply`` CLI failure → ``None``.
        Consumers degrade gracefully (PHASE1 logs ``[]``)."""

        def _raise(operation, change_id, *, store=None):
            raise OSXError("cli_error", "openspec failed", args=[operation])

        monkeypatch.setattr(osx_lib, "fetch_instructions", _raise)
        assert fetch_apply_prerequisites("add-auth") is None

    def test_store_propagation(self, mock_instructions) -> None:
        """``store=`` kwarg propagates to the underlying fetch."""
        mock_instructions["payload"] = {"missingPrerequisites": []}
        fetch_apply_prerequisites("add-auth", store="my-store")
        assert mock_instructions["store"] == "my-store"
