#!/usr/bin/env python3
"""
Unit tests for ``validate_archive`` integrity checks.

Covers the C4 fix: ``validate_archive`` previously only checked that an
archive directory matching ``*-<change>`` existed under the planning home's
``changes/archive`` folder. It now also asserts:

  - ``decision-log.json`` is present in the archive
  - ``iterations.json`` is present in the archive
  - ``git log -1 -- .`` resolves in the archive directory (i.e. the
    archive has at least one commit touching it)

The transient-presence check (``state.json``/``complete.json`` no longer
present) is enforced post-cleanup in the engine, not in
``validate_archive``.
"""

import json
import subprocess
from unittest.mock import MagicMock

import pytest

from source.lib import osx


def make_run(stdout="", returncode=0, stderr="", exc=None, git_result=None):
    """Build a fake subprocess.run callable for openspec CLI mocks.

    `git_result` overrides the response for any `git log` invocation, so a
    test that wants the real-fallback path (openspec binary missing) can
    still get a successful git commit check. `exc` is raised for every
    non-git call; pass `git_result=None` to also raise for git.
    """

    def _run(*args, **kwargs):
        cmd = list(args[0]) if args else kwargs.get("args", [])
        if cmd and cmd[0] == "git":
            if git_result is not None:
                return git_result
            if exc is not None:
                raise exc
            return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)
        if exc is not None:
            raise exc
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    return _run


@pytest.fixture(autouse=True)
def _clear_paths_cache():
    """Clear osx._PATHS_CACHE before and after each test."""
    osx._PATHS_CACHE.clear()
    yield
    osx._PATHS_CACHE.clear()


def _init_git_repo(env_dir):
    """Init a git repo and make a baseline commit in env_dir."""
    subprocess.run(["git", "init", "-q"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=env_dir, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=env_dir, check=True)
    (env_dir / "README.md").write_text("# Test repo")
    subprocess.run(["git", "add", "README.md"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=env_dir, check=True
    )


def _make_archive(env_dir, change_name, timestamp="2024-01-15"):
    """Create the archive directory at the expected convention path."""
    archive = (
        env_dir / "openspec" / "changes" / "archive" / f"{timestamp}-{change_name}"
    )
    archive.mkdir(parents=True)
    return archive


@pytest.mark.unit
class TestValidateArchiveIntegrity:
    """Integrity checks added by the C4 fix."""

    def test_validate_archive_missing_decision_log(self, tmp_path, monkeypatch):
        """Archive directory exists but no decision-log.json -> invalid."""
        _init_git_repo(tmp_path)
        archive = _make_archive(tmp_path, "test-change")
        (archive / "iterations.json").write_text("[]")

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=tmp_path,
            check=True,
        )

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))

        result = osx.validate_archive("test-change")

        assert result["valid"] is False
        assert any(e["check"] == "decision-log" for e in result["errors"])

    def test_validate_archive_missing_iterations_log(self, tmp_path, monkeypatch):
        """Archive directory exists but no iterations.json -> invalid."""
        _init_git_repo(tmp_path)
        archive = _make_archive(tmp_path, "test-change")
        (archive / "decision-log.json").write_text("[]")

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=tmp_path,
            check=True,
        )

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))

        result = osx.validate_archive("test-change")

        assert result["valid"] is False
        assert any(e["check"] == "iterations" for e in result["errors"])

    def test_validate_archive_no_commit(self, tmp_path, monkeypatch):
        """Archive directory exists in a non-git working tree -> commit error."""
        _make_archive(tmp_path, "test-change")
        (
            tmp_path
            / "openspec"
            / "changes"
            / "archive"
            / "2024-01-15-test-change"
            / "decision-log.json"
        ).write_text("[]")
        (
            tmp_path
            / "openspec"
            / "changes"
            / "archive"
            / "2024-01-15-test-change"
            / "iterations.json"
        ).write_text("[]")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))

        result = osx.validate_archive("test-change")

        assert result["valid"] is False
        assert any(e["check"] == "commit" for e in result["errors"])

    def test_validate_archive_full_archive_passes(self, tmp_path, monkeypatch):
        """Archive directory with all required files + a real commit -> valid."""
        _init_git_repo(tmp_path)
        archive = _make_archive(tmp_path, "test-change")
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "proposal.md").write_text("# Proposal")
        (archive / "tasks.md").write_text("# Tasks")

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=tmp_path,
            check=True,
        )

        monkeypatch.chdir(tmp_path)
        git_ok = MagicMock(returncode=0, stdout="deadbeef\n", stderr="")
        monkeypatch.setattr(
            osx.subprocess,
            "run",
            make_run(exc=FileNotFoundError(), git_result=git_ok),
        )

        result = osx.validate_archive("test-change")

        assert result["valid"] is True
        assert result["archive"].endswith("2024-01-15-test-change")

    def test_validate_archive_with_stale_transients_passes_pre_cleanup(
        self, tmp_path, monkeypatch
    ):
        """Stale transients in archive are NOT rejected by validate_archive.

        Transients (``state.json``/``complete.json``) are present until the
        orchestrator's cleanup runs. validate_archive is called BEFORE
        cleanup, so it must accept archives that still carry transients.
        The cleanup() function in the engine is responsible for removing
        them and asserting they are gone.
        """
        _init_git_repo(tmp_path)
        archive = _make_archive(tmp_path, "test-change")
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "state.json").write_text(
            '{"phase": "PHASE6", "phase_complete": true}'
        )
        (archive / "complete.json").write_text('{"status": "COMPLETE"}')

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=tmp_path,
            check=True,
        )

        monkeypatch.chdir(tmp_path)
        git_ok = MagicMock(returncode=0, stdout="deadbeef\n", stderr="")
        monkeypatch.setattr(
            osx.subprocess,
            "run",
            make_run(exc=FileNotFoundError(), git_result=git_ok),
        )

        result = osx.validate_archive("test-change")

        assert result["valid"] is True
        assert result["archive"].endswith("2024-01-15-test-change")

    def test_validate_archive_multiple_archives_still_fails(
        self, tmp_path, monkeypatch
    ):
        """Pre-existing behavior: multiple archives -> single error."""
        _make_archive(tmp_path, "test-change", timestamp="2024-01-10")
        _make_archive(tmp_path, "test-change", timestamp="2024-01-15")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))

        result = osx.validate_archive("test-change")

        assert result["valid"] is False
        assert any(
            e["check"] == "archive" and "Multiple archives" in e["message"]
            for e in result["errors"]
        )

    def test_validate_archive_zero_archives_still_fails(self, tmp_path, monkeypatch):
        """Pre-existing behavior: zero archives -> single error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))

        result = osx.validate_archive("test-change")

        assert result["valid"] is False
        assert result["errors"] == [
            {"check": "archive", "message": "Change not archived"}
        ]

    def test_validate_archive_store_kwarg_invokes_git_in_resolved_path(
        self, tmp_path, monkeypatch
    ):
        """When store= is provided, validate_archive calls git log in the store archive dir."""
        _init_git_repo(tmp_path)
        archive = _make_archive(tmp_path, "test-change")
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "proposal.md").write_text("# Proposal")

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=tmp_path,
            check=True,
        )

        store_root = tmp_path / "store-root"
        store_root.mkdir()
        store_change_root = store_root / "openspec" / "changes" / "test-change"
        store_change_root.mkdir(parents=True)
        store_archive = (
            store_root / "openspec" / "changes" / "archive" / "2024-01-15-test-change"
        )
        store_archive.mkdir(parents=True)
        (store_archive / "decision-log.json").write_text("[]")
        (store_archive / "iterations.json").write_text("[]")
        (store_archive / "proposal.md").write_text("# Proposal")

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Store archive test-change"],
            cwd=tmp_path,
            check=True,
        )

        captured = {}

        def _run(*args, **kwargs):
            cmd = list(args[0]) if args else kwargs.get("args", [])
            cwd = kwargs.get("cwd")
            captured.setdefault("calls", []).append((cmd, cwd))
            if cmd[:3] == ["openspec", "status", "--change"]:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "changeRoot": str(store_change_root),
                            "planningHome": {
                                "kind": "repo",
                                "root": str(store_root),
                            },
                        }
                    ),
                    stderr="",
                )
            return MagicMock(returncode=0, stdout="deadbeef\n", stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)

        result = osx.validate_archive("test-change", store="my-store")

        assert result["valid"] is True
        git_calls = [c for c in captured["calls"] if c[0][:1] == ["git"]]
        assert git_calls, "expected at least one git log invocation"
        cwd_used = git_calls[0][1]
        assert cwd_used is not None
        assert str(cwd_used).endswith("2024-01-15-test-change")
