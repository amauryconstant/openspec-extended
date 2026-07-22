#!/usr/bin/env python3
"""
Regression tests asserting `_run_openspec_json` is the single owner of `--json`.

Upstream `openspec` CLI today tolerates duplicate flags; future versions may
not. Every osx helper that calls `_run_openspec_json` must NOT pass `--json`
itself — the helper appends it as the final argv element.
"""

import json
from unittest.mock import MagicMock

import pytest

from source.lib import osx


def make_run(stdout='{"items":[],"summary":{"totals":{"failed":0}}}', returncode=0):
    def _run(*args, **kwargs):
        cmd = list(args[0]) if args else kwargs.get("args", [])
        captured.setdefault("cmd", cmd)
        return MagicMock(returncode=returncode, stdout=stdout, stderr="")

    return _run


captured: dict = {}


def _reset_captured():
    captured.clear()


@pytest.fixture(autouse=True)
def _reset():
    _reset_captured()
    yield
    _reset_captured()


def _run_calls():
    return captured["cmd"]


def _assert_single_json_last():
    cmd = _run_calls()
    assert cmd.count("--json") == 1, f"expected one --json, got {cmd.count('--json')} in {cmd}"
    assert cmd[-1] == "--json", f"--json should be last (helper appends it); got {cmd}"


@pytest.mark.unit
class TestNoDoubleJson:
    """Each osx library function emits exactly one --json, and as the final argv."""

    def test_validate_change(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run())
        osx.validate_change("c1")
        _assert_single_json_last()

    def test_validate_change_with_strict_and_store(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run())
        osx.validate_change("c1", strict=True, store="s1")
        _assert_single_json_last()
        assert "--strict" in _run_calls()
        assert "--store" in _run_calls()
        assert "s1" in _run_calls()

    def test_validate_spec(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run())
        osx.validate_spec("authentication")
        _assert_single_json_last()

    def test_validate_all(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run())
        osx.validate_all()
        _assert_single_json_last()
        assert "--all" in _run_calls()

    def test_validate_changes_only(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run())
        osx.validate_changes_only()
        _assert_single_json_last()
        assert "--changes" in _run_calls()

    def test_validate_specs_only(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run())
        osx.validate_specs_only()
        _assert_single_json_last()
        assert "--specs" in _run_calls()

    def test_list_artifacts_for_schema(self, monkeypatch):
        payload = json.dumps({"proposal": {}, "specs": {}})
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        osx.list_artifacts_for_schema("spec-driven")
        _assert_single_json_last()
        assert "templates" in _run_calls()
        assert "--schema" in _run_calls()

    def test_schema_which(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"name":"x"}'))
        osx.schema_which("spec-driven")
        _assert_single_json_last()

    def test_schema_validate(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"valid":true}'))
        osx.schema_validate("spec-driven")
        _assert_single_json_last()

    def test_schema_fork(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"name":"x"}'))
        osx.schema_fork("spec-driven", "my-fork", force=True)
        _assert_single_json_last()
        assert "--force" in _run_calls()

    def test_schema_init(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"name":"x"}'))
        osx.schema_init("my-schema", description="d", set_default=True)
        _assert_single_json_last()

    def test_schema_list(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout="[]"))
        osx.schema_list()
        _assert_single_json_last()
        assert "schemas" in _run_calls()


@pytest.mark.unit
class TestStoreHelpersPreserveSingleJson:
    """store_* helpers also rely on _run_openspec_json → exactly one --json."""

    def test_store_list(self, monkeypatch):
        payload = json.dumps({"stores": []})
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        osx.store_list()
        _assert_single_json_last()

    def test_store_doctor(self, monkeypatch):
        payload = json.dumps({"id": "x", "ok": True})
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        osx.store_doctor("my-store")
        _assert_single_json_last()
        assert "my-store" in _run_calls()

    def test_store_register(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"id":"s1"}'))
        osx.store_register("/p", store_id="My Store")
        _assert_single_json_last()
        assert "--id" in _run_calls()
        assert "My Store" in _run_calls()

    def test_store_unregister(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"id":"s1"}'))
        osx.store_unregister("my-store")
        _assert_single_json_last()
        assert "unregister" in _run_calls()
