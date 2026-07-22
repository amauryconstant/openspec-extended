#!/usr/bin/env python3
"""
Tests for ``source.lib.osx.get_core_version`` and the orchestrator's
minimum-version gate.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from source.lib import osx


@pytest.mark.unit
class TestGetCoreVersion:
    """Unit tests for ``get_core_version``."""

    def test_min_version_is_1_6_0(self):
        assert osx.MIN_OPENSPEC_VERSION == (1, 6, 0)

    def test_cli_module_no_longer_exports_script_version(self):
        """`__version__` in source/__init__.py is the canonical version.
        The legacy `SCRIPT_VERSION` literal was removed from source/cli.py
        to eliminate the duplicate source-of-truth.
        """
        import source.cli as cli_mod

        assert not hasattr(cli_mod, "SCRIPT_VERSION"), (
            "source.cli.SCRIPT_VERSION must not be defined; "
            "the canonical version lives in source.__version__"
        )
        assert hasattr(cli_mod, "__version__")
        assert cli_mod.__version__ == osx.__version__ if hasattr(
            osx, "__version__"
        ) else True  # osx is a library module; just assert cli imports it

    def test_version_callback_uses_dunder_version(self):
        """The `--version` callback prints `__version__`, not SCRIPT_VERSION."""
        from source.cli import app

        captured: list[str] = []

        from unittest.mock import patch

        from typer.testing import CliRunner

        runner = CliRunner()
        with patch("source.cli.console.print", side_effect=captured.append):
            result = runner.invoke(app, ["--version"], color=False)
        assert result.exit_code == 0
        joined = "\n".join(captured)
        assert "openspec-extended" in joined
        # The version printed must equal `__version__`.
        from source import __version__

        assert __version__ in joined


    def test_returns_none_when_binary_missing(self, monkeypatch):
        """No `openspec` on PATH → None (not an exception)."""
        with patch(
            "source.lib.osx.subprocess.run",
            side_effect=FileNotFoundError("no openspec"),
        ):
            assert osx.get_core_version() is None

    def test_returns_tuple_on_valid_output(self, monkeypatch):
        from unittest.mock import MagicMock

        fake = MagicMock(
            returncode=0,
            stdout="@fission-ai/openspec/1.7.2 linux-x64 node-v20.19.0",
            stderr="",
        )
        with patch("source.lib.osx.subprocess.run", return_value=fake):
            assert osx.get_core_version() == (1, 7, 2)

    def test_returns_none_on_garbage(self, monkeypatch):
        from unittest.mock import MagicMock

        fake = MagicMock(returncode=0, stdout="hi mom", stderr="")
        with patch("source.lib.osx.subprocess.run", return_value=fake):
            assert osx.get_core_version() is None

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("openspec 1.6.0", (1, 6, 0)),
            ("@fission-ai/openspec/1.6.3 (darwin)", (1, 6, 3)),
            ("@fission-ai/openspec/2.0.0", (2, 0, 0)),
            ("garbage output", None),
        ],
    )
    def test_parses_versions(self, monkeypatch, raw, expected):
        from unittest.mock import MagicMock

        fake = MagicMock(returncode=0, stdout=raw, stderr="")
        with patch("source.lib.osx.subprocess.run", return_value=fake):
            assert osx.get_core_version() == expected


@pytest.mark.integration
class TestCoreVersionGate:
    """The orchestrator must refuse to start with openspec < 1.6.0."""

    def test_orchestrator_refuses_old_core(self, tmp_path, monkeypatch):
        """If openspec reports < 1.6.0, run_orchestrator exits 2."""

        # Skip AI probe / git / jq so we get to the openspec version check
        # before any side effects.

        from source.orchestrator import engine as eng

        # Mock the early subprocess probes to succeed.
        def fake_run(cmd, *a, **kw):
            from unittest.mock import MagicMock

            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(eng.subprocess, "run", fake_run)

        # Make `openspec --version` report 1.5.3
        import source.lib.osx as osx_lib

        monkeypatch.setattr(osx_lib, "get_core_version", lambda: (1, 5, 3))

        # Stub validate_* and record_baseline so we hit only the gate
        for fn in (
            "validate_skills",
            "validate_commands",
            "validate_git",
            "validate_change_dir",
            "validate_schema",
            "record_baseline",
        ):
            monkeypatch.setattr(eng, fn, lambda s: None)

        # find_change_dir is called before preflight; stub it to return the
        # tmp_path so we get to the gate.
        monkeypatch.setattr(eng, "find_change_dir", lambda *a, **kw: tmp_path)

        monkeypatch.chdir(tmp_path)
        state = eng.OrchestratorState(
            change_id="c",
            change_dir=tmp_path,
            clean=False,
            force=True,
        )

        with pytest.raises(SystemExit) as exc:
            eng.run_orchestrator(state)

        assert exc.value.code == 2

    def test_orchestrator_accepts_new_core(self, tmp_path, monkeypatch):
        """openspec 1.6.0+ passes the gate; further validation runs."""
        from source.orchestrator import engine as eng
        import source.lib.osx as osx_lib

        def fake_run(cmd, *a, **kw):
            from unittest.mock import MagicMock

            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(eng.subprocess, "run", fake_run)
        monkeypatch.setattr(osx_lib, "get_core_version", lambda: (1, 6, 0))

        called = {"v": False}

        def fake_validate(s):
            called["v"] = True
            raise SystemExit(0)

        monkeypatch.setattr(eng, "validate_skills", fake_validate)
        for fn in (
            "validate_commands",
            "validate_git",
            "validate_change_dir",
            "validate_schema",
            "record_baseline",
        ):
            monkeypatch.setattr(eng, fn, lambda s: None)
        monkeypatch.setattr(
            eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0))
        )
        monkeypatch.setattr(eng, "find_change_dir", lambda *a, **kw: tmp_path)

        monkeypatch.chdir(tmp_path)
        state = eng.OrchestratorState(
            change_id="c",
            change_dir=tmp_path,
            clean=False,
            force=True,
        )

        with pytest.raises(SystemExit):
            eng.run_orchestrator(state)

        assert called["v"] is True
