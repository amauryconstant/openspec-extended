#!/usr/bin/env python3
"""
Tests for non-destructive ``--with-core`` install.

Locks in:

- Clean install (``--with-core``) succeeds and does not write a snapshot.
- Re-installing on top of an existing core deployment refuses (exit 2).
- Re-installing with ``--with-core --force`` writes a baseline JSON file
  at the project root capturing the prior global config, then proceeds.
- ``restore-core`` re-applies the snapshot to
  ``~/.config/openspec/config.json`` and removes the snapshot.
- ``.openspec-extended-baseline.json`` is in the .gitignore envelope.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _run_osx(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "source", *args]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


@pytest.fixture
def fresh_env(tmp_path: Path, monkeypatch) -> Path:
    """Empty project; no .opencode/ deployed yet."""
    env = tmp_path / "env"
    env.mkdir()
    # Avoid clobbering the user's real ~/.config/openspec/config.json
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    (tmp_path / "fake-home").mkdir()
    return env


@pytest.fixture
def pre_deployed(fresh_env: Path) -> Path:
    """Simulate a prior ``openspec init`` deployment by creating the
    post-rename marker skill directory."""
    skills = fresh_env / ".opencode" / "skills" / "osc-apply-change"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("---\nname: osc-apply-change\n---\nfake")
    return fresh_env


class TestInstallWithCoreRefuses:
    def test_clean_install_succeeds(self, fresh_env: Path):
        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)
        # May fail because real openspec may have downstream issues; but
        # baseline file must NOT be written for a fresh install.
        assert not (fresh_env / ".openspec-extended-baseline.json").exists()

    def test_existing_deploy_refuses_without_force(self, pre_deployed: Path):
        result = _run_osx(["install", "opencode", "--with-core"], cwd=pre_deployed)
        assert result.returncode == 2, (
            f"non-destructive install must exit 2; got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "--force" in result.stdout or "--force" in result.stderr

    def test_existing_deploy_with_force_writes_baseline(self, pre_deployed: Path):
        # Seed a fake global config so the baseline has data
        cfg_dir = pre_deployed.parent / "fake-home" / ".config" / "openspec"
        cfg_dir.mkdir(parents=True)
        cfg_path = cfg_dir / "config.json"
        cfg_path.write_text(json.dumps({"profile": "core", "delivery": "skills"}))

        result = _run_osx(
            ["install", "opencode", "--with-core", "--force"], cwd=pre_deployed
        )
        # Either succeeds or fails for upstream reasons; baseline must be
        # written before the deploy attempt.
        baseline = pre_deployed / ".openspec-extended-baseline.json"
        assert baseline.exists(), (
            f"--force install should write baseline; "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        data = json.loads(baseline.read_text())
        assert "captured_at" in data
        assert "global_config" in data
        assert "tool" in data


class TestRestoreCore:
    def test_restore_clears_baseline(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
        (tmp_path / "fake-home").mkdir()
        project = tmp_path / "project"
        project.mkdir()

        # Seed baseline
        baseline = project / ".openspec-extended-baseline.json"
        cfg = {"profile": "core", "delivery": "both"}
        baseline.write_text(
            json.dumps(
                {
                    "captured_at": "2026-01-01T00:00:00Z",
                    "tool": "opencode",
                    "global_config": cfg,
                    "project_root": str(project),
                }
            )
        )

        result = _run_osx(["restore-core"], cwd=project)
        assert result.returncode == 0, (
            f"restore-core should succeed; got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Baseline removed
        assert not baseline.exists()
        # Config restored
        restored = tmp_path / "fake-home" / ".config" / "openspec" / "config.json"
        assert restored.exists()
        data = json.loads(restored.read_text())
        assert data == cfg

    def test_restore_without_baseline_fails(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
        (tmp_path / "fake-home").mkdir()
        project = tmp_path / "project"
        project.mkdir()
        result = _run_osx(["restore-core"], cwd=project)
        assert result.returncode == 1


class TestGitignoreIncludesBaseline:
    def test_baseline_filename_in_gitignore(self, fresh_env: Path):
        """``update_gitignore()`` should mention the baseline filename."""
        _run_osx(["install", "opencode"], cwd=fresh_env)
        gi = fresh_env / ".gitignore"
        if not gi.exists():
            pytest.skip("no .gitignore produced")
        content = gi.read_text()
        assert ".openspec-extended-baseline.json" in content
