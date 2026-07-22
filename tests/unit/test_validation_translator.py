#!/usr/bin/env python3
"""
Unit tests for the validate_* functions and _translate_validate_payload helper
in source.lib.osx.

Subprocess is mocked so tests do not depend on a real `openspec` binary.
"""

import json
from unittest.mock import MagicMock

import pytest

from source.lib import osx


def make_run(stdout="", returncode=0, stderr="", exc=None):
    """Build a fake subprocess.run callable."""

    def _run(*args, **kwargs):
        if exc is not None:
            raise exc
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    return _run


@pytest.mark.unit
class TestTranslateValidatePayload:
    def test_translates_validation_failure(self):
        payload = {
            "items": [
                {
                    "id": "add-auth",
                    "type": "change",
                    "valid": False,
                    "issues": [
                        {"level": "ERROR", "path": "specs.auth/foo.md", "message": "missing SHALL"},
                    ],
                    "durationMs": 5,
                }
            ],
            "summary": {
                "totals": {"items": 1, "passed": 0, "failed": 1},
                "byType": {"change": {"items": 1, "passed": 0, "failed": 1}},
            },
            "version": "1.0",
            "root": {"path": "/tmp/proj", "source": "nearest"},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["message"] == "missing SHALL"
        assert result["errors"][0]["target"] == "add-auth"
        assert result["warnings"] == []
        assert result["info"] == []

    def test_translates_warning(self):
        payload = {
            "items": [
                {
                    "id": "spec-x",
                    "type": "spec",
                    "valid": True,
                    "issues": [
                        {"level": "WARNING", "path": "overview", "message": "too brief"},
                    ],
                    "durationMs": 3,
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is True
        assert result["errors"] == []
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["message"] == "too brief"

    def test_translates_info_level(self):
        payload = {
            "items": [
                {
                    "id": "spec-y",
                    "type": "spec",
                    "valid": True,
                    "issues": [{"level": "INFO", "path": "requirements[0].text", "message": "too long"}],
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert len(result["info"]) == 1
        assert result["info"][0]["message"] == "too long"

    def test_translates_prevalidation_error(self):
        payload = {
            "status": [
                {
                    "severity": "error",
                    "code": "no_openspec_root",
                    "message": "No openspec/ directory found",
                    "fix": "Run openspec init",
                }
            ]
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is False
        assert result["diagnostics"][0]["code"] == "no_openspec_root"
        assert result["diagnostics"][0]["fix"] == "Run openspec init"
        assert result["errors"][0]["check"] == "no_openspec_root"

    def test_translates_ambiguous_item_error(self):
        payload = {
            "status": [
                {
                    "severity": "error",
                    "code": "ambiguous_item",
                    "message": "Ambiguous item 'foo'",
                    "fix": "Pass --type change|spec.",
                }
            ]
        }
        result = osx._translate_validate_payload(payload)
        assert result["diagnostics"][0]["code"] == "ambiguous_item"

    def test_preserves_line_numbers(self):
        payload = {
            "items": [
                {
                    "id": "spec-z",
                    "type": "spec",
                    "valid": False,
                    "issues": [
                        {"level": "ERROR", "path": "file", "message": "structure issue", "line": 42},
                    ],
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 0, "failed": 1}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["errors"][0]["line"] == 42

    def test_preserves_root_info(self):
        payload = {
            "items": [{"id": "a", "type": "spec", "valid": True, "issues": []}],
            "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
            "version": "1.0",
            "root": {"path": "/x", "source": "store", "store_id": "my-store"},
        }
        result = osx._translate_validate_payload(payload)
        assert result["root"]["source"] == "store"
        assert result["root"]["store_id"] == "my-store"

    def test_empty_items_list(self):
        payload = {
            "items": [],
            "summary": {"totals": {"items": 0, "passed": 0, "failed": 0}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_failed_returns_unverifiable(self):
        """A success envelope without summary.totals.failed is unverifiable.

        Returns valid=None (unknown) and emits a warning diagnostic so callers
        downstream do not silently treat a malformed upstream payload as a
        pass. Any pre-existing per-item warnings are preserved alongside the
        new diagnostic.
        """
        payload = {
            "items": [
                {
                    "id": "spec-w",
                    "type": "spec",
                    "valid": True,
                    "issues": [
                        {"level": "WARNING", "path": "overview", "message": "too brief"},
                    ],
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 1}},
            "version": "1.0",
            "root": {"path": "/tmp/proj", "source": "nearest"},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is None
        codes = [w.get("code") for w in result["warnings"]]
        assert "unverifiable_envelope" in codes
        envelope_warning = next(
            w for w in result["warnings"] if w.get("code") == "unverifiable_envelope"
        )
        assert envelope_warning["severity"] == "warning"
        assert "summary.totals.failed" in envelope_warning["message"]
        assert result["root"]["source"] == "nearest"
        assert any(w.get("message") == "too brief" for w in result["warnings"])

    def test_missing_totals_returns_unverifiable(self):
        """summary present but totals absent is also unverifiable."""
        payload = {
            "items": [],
            "summary": {},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is None
        assert any(
            w.get("code") == "unverifiable_envelope" for w in result["warnings"]
        )


@pytest.mark.unit
class TestValidateChange:
    def test_includes_change_id_in_args(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "items": [{"id": "my-change", "type": "change", "valid": True, "issues": []}],
                    "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
                    "version": "1.0",
                    "root": {},
                }),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        result = osx.validate_change("my-change")
        assert "validate" in captured["cmd"]
        assert "my-change" in captured["cmd"]
        assert "--json" in captured["cmd"]
        assert "--no-interactive" in captured["cmd"]
        assert result["valid"] is True

    def test_appends_store_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_change("c", store="my-store")
        assert "--store" in captured["cmd"]
        assert "my-store" in captured["cmd"]

    def test_appends_strict_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_change("c", strict=True)
        assert "--strict" in captured["cmd"]


@pytest.mark.unit
class TestValidateSpec:
    def test_includes_type_spec(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_spec("authentication")
        assert "--type" in captured["cmd"]
        idx = captured["cmd"].index("--type")
        assert captured["cmd"][idx + 1] == "spec"


@pytest.mark.unit
class TestValidateAll:
    def test_includes_concurrency(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_all(concurrency=12)
        assert "--concurrency" in captured["cmd"]
        idx = captured["cmd"].index("--concurrency")
        assert captured["cmd"][idx + 1] == "12"

    def test_uses_extended_timeout(self, monkeypatch):
        captured_kwargs = {}

        def _run(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_all()
        assert captured_kwargs.get("timeout") == 60


@pytest.mark.unit
class TestValidateChangesOnly:
    def test_uses_changes_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_changes_only()
        assert "--changes" in captured["cmd"]
        assert "--all" not in captured["cmd"]


@pytest.mark.unit
class TestValidateSpecsOnly:
    def test_uses_specs_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps({"items": [], "summary": {"totals": {}}, "version": "1.0", "root": {}}),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_specs_only()
        assert "--specs" in captured["cmd"]
        assert "--all" not in captured["cmd"]