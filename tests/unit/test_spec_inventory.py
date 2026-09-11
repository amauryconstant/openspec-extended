#!/usr/bin/env python3
"""Tests for ``list_specs`` and ``show_spec`` (v1.13.0+ consumers).

OpenSpec v1.13.0 introduced the ``--specs`` flag on ``openspec list``
and the ``--type spec`` flag on ``openspec show``. Generated guidance
uses these to build a spec inventory and then drill into each spec with
a filtered read (``--no-scenarios``). PHASE0 spec-aware review
(``osx-review-artifacts`` Step 2) consumes the same shape to detect
"capability already exists" drift before approving ``ADDED Requirements``
deltas.

These tests pin the in-process readers (``list_specs``, ``show_spec``).
The CLI surface (PHASE0 review) is covered by
``tests/unit/test_resource_contract.py::TestOrchestratorContracts``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from source.lib import osx as osx_lib
from source.lib.osx import OSXError, list_specs, show_spec


@pytest.fixture
def mock_run(monkeypatch):
    """Mock ``_run_openspec_json`` so we can drive ``list_specs`` /
    ``show_spec`` without spawning ``openspec``.

    Stores the payload the mocked helper returns and the args / kwargs it
    was called with. Tests set ``captured["payload"]`` to whatever shape
    the v1.13.0 envelope (or older-core envelope) would have.
    """
    captured: dict = {}

    def _fake(args, timeout=10):
        captured["args"] = list(args)
        captured["timeout"] = timeout
        return captured.get("payload", {})

    monkeypatch.setattr(osx_lib, "_run_openspec_json", _fake)
    return captured


@pytest.mark.unit
class TestListSpecs:
    """A.9 (v1.13.0+): the in-process reader for the
    ``openspec list --specs --json`` envelope."""

    def test_returns_specs_array(self, mock_run) -> None:
        """v1.13.0 envelope shape: ``{"specs": [...], "root": {...}}``."""
        mock_run["payload"] = {
            "specs": [
                {"id": "auth/oauth-flow", "path": "openspec/specs/auth/oauth-flow/spec.md"},
                {"id": "billing/invoice", "path": "openspec/specs/billing/invoice/spec.md"},
            ],
            "root": {"kind": "project", "root": "/repo"},
        }
        result = list_specs()
        assert result == [
            {"id": "auth/oauth-flow", "path": "openspec/specs/auth/oauth-flow/spec.md"},
            {"id": "billing/invoice", "path": "openspec/specs/billing/invoice/spec.md"},
        ]
        assert mock_run["args"] == ["list", "--specs"]
        assert mock_run["timeout"] == 30

    def test_empty_inventory(self, mock_run) -> None:
        """v1.13.0 with no specs yet: ``{"specs": []}``."""
        mock_run["payload"] = {"specs": [], "root": {"kind": "project", "root": "/repo"}}
        assert list_specs() == []

    def test_store_propagation(self, mock_run) -> None:
        """``store=`` kwarg adds ``--store <id>`` to the argv."""
        mock_run["payload"] = {"specs": []}
        list_specs(store="my-store")
        assert "--store" in mock_run["args"]
        assert mock_run["args"][mock_run["args"].index("--store") + 1] == "my-store"

    def test_older_core_returns_none(self, monkeypatch) -> None:
        """v1.13.0-: ``--specs`` is unknown; the CLI exits non-zero and the
        helper returns ``None``. Consumers degrade gracefully."""

        def _raise(args, timeout=10):
            raise OSXError("cli_error", "unknown flag", args=args)

        monkeypatch.setattr(osx_lib, "_run_openspec_json", _raise)
        assert list_specs() is None

    def test_non_dict_envelope_returns_none(self, mock_run) -> None:
        """Defensive: a non-dict envelope returns ``None`` rather than
        raising — the helper never raises."""
        mock_run["payload"] = ["not", "a", "dict"]
        assert list_specs() is None

    def test_missing_specs_key_returns_none(self, mock_run) -> None:
        """Defensive: a dict without ``specs`` (e.g. core bug) returns
        ``None`` rather than returning an empty list (which would falsely
        signal "no specs in the project")."""
        mock_run["payload"] = {"root": {"kind": "project"}}
        assert list_specs() is None

    def test_non_list_specs_returns_none(self, mock_run) -> None:
        """Defensive: a non-list ``specs`` (e.g. core bug) returns ``None``
        rather than raising."""
        mock_run["payload"] = {"specs": "not-a-list"}
        assert list_specs() is None

    def test_non_dict_entries_filtered(self, mock_run) -> None:
        """Defensive: non-dict entries (e.g. ``None`` from upstream bugs)
        are silently dropped rather than poisoning the returned list."""
        mock_run["payload"] = {
            "specs": [
                {"id": "auth/oauth-flow"},
                None,
                "string-entry",
                42,
                {"id": "billing/invoice"},
            ]
        }
        result = list_specs()
        assert result == [
            {"id": "auth/oauth-flow"},
            {"id": "billing/invoice"},
        ]


@pytest.mark.unit
class TestShowSpec:
    """A.9 (v1.13.0+): the in-process reader for the filtered
    ``openspec show <id> --type spec --json --no-scenarios`` envelope."""

    def test_returns_envelope(self, mock_run) -> None:
        """Happy path: ``--type spec --json --no-scenarios`` envelope."""
        mock_run["payload"] = {
            "id": "auth/oauth-flow",
            "purpose": "OAuth flow",
            "requirements": [{"id": "R: login"}, {"id": "R: refresh"}],
        }
        result = show_spec("auth/oauth-flow")
        assert result == mock_run["payload"]
        assert mock_run["args"] == [
            "show",
            "auth/oauth-flow",
            "--type",
            "spec",
            "--json",
            "--no-scenarios",
        ]

    def test_store_propagation(self, mock_run) -> None:
        mock_run["payload"] = {"id": "auth/oauth-flow"}
        show_spec("auth/oauth-flow", store="my-store")
        assert "--store" in mock_run["args"]
        assert mock_run["args"][mock_run["args"].index("--store") + 1] == "my-store"

    def test_older_core_returns_none(self, monkeypatch) -> None:
        """v1.13.0-: ``--type spec`` is unknown; helper returns ``None``."""

        def _raise(args, timeout=10):
            raise OSXError("cli_error", "unknown flag", args=args)

        monkeypatch.setattr(osx_lib, "_run_openspec_json", _raise)
        assert show_spec("auth/oauth-flow") is None

    def test_non_dict_envelope_returns_none(self, mock_run) -> None:
        """Defensive: a non-dict envelope (e.g. core bug) returns ``None``
        rather than raising."""
        mock_run["payload"] = ["not", "a", "dict"]
        assert show_spec("auth/oauth-flow") is None
