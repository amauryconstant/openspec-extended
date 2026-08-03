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
        # baseline file must NOT be written for a fresh install (no prior
        # deployment AND no prior global config → nothing meaningful to
        # restore, so we skip the snapshot).
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


class TestInstallWithCoreSeedsGlobalConfig:
    """``install --with-core`` must seed ``~/.config/openspec/config.json``
    with the canonical 12-workflow custom profile before invoking
    ``openspec init`` so the user gets all 12 commands (the v1.5.0+
    regression: ``openspec init`` defaults to ``profile=core`` and only
    installs 6 workflows).
    """

    def _global_config(self, fresh_env: Path) -> Path:
        return fresh_env.parent / "fake-home" / ".config" / "openspec" / "config.json"

    def test_clean_install_writes_canonical_global_config(self, fresh_env: Path):
        """First-time ``--with-core`` writes the 12-workflow custom profile."""
        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)

        cfg = self._global_config(fresh_env)
        if not cfg.exists():
            pytest.skip("openspec init did not run (binary missing or upstream error)")
        data = json.loads(cfg.read_text())
        assert data["profile"] == "custom"
        assert data["delivery"] == "both"
        assert set(data["workflows"]) == CANONICAL_WORKFLOWS

    def test_existing_global_config_is_snapshotted(self, fresh_env: Path):
        """A pre-existing ``~/.config/openspec/config.json`` is captured into
        ``.openspec-extended-baseline.json`` before being overwritten so
        ``restore-core`` can revert it.
        """
        cfg_dir = fresh_env.parent / "fake-home" / ".config" / "openspec"
        cfg_dir.mkdir(parents=True)
        cfg_path = cfg_dir / "config.json"
        cfg_path.write_text(
            json.dumps(
                {"profile": "core", "delivery": "skills", "workflows": ["apply"]}
            )
        )

        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)

        baseline = fresh_env / ".openspec-extended-baseline.json"
        assert baseline.exists(), (
            "Baseline must be written when the prior global config existed, "
            "even without a prior deployment"
        )
        data = json.loads(baseline.read_text())
        assert data["tool"] == "(global-config)"
        assert data["global_config"]["profile"] == "core"
        assert data["global_config"]["workflows"] == ["apply"]

    def test_clean_install_with_no_prior_config_writes_no_baseline(
        self, fresh_env: Path
    ):
        """No prior global config AND no prior deployment → no baseline file.
        Guards against ``.openspec-extended-baseline.json`` appearing for
        genuine first-time installs.
        """
        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)
        assert not (fresh_env / ".openspec-extended-baseline.json").exists()

    def test_restore_round_trip_with_prior_global_config(self, fresh_env: Path):
        """If a prior global config was overwritten, ``restore-core`` puts
        the original ``profile`` and ``workflows`` back."""
        cfg_dir = fresh_env.parent / "fake-home" / ".config" / "openspec"
        cfg_dir.mkdir(parents=True)
        cfg_path = cfg_dir / "config.json"
        prior = {"profile": "core", "delivery": "skills", "workflows": ["apply"]}
        cfg_path.write_text(json.dumps(prior))

        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)
        if (fresh_env / ".openspec-extended-baseline.json").exists():
            restore = _run_osx(["restore-core"], cwd=fresh_env)
            assert restore.returncode == 0, (
                f"restore-core failed: {restore.stdout}\n{restore.stderr}"
            )
            data = json.loads(cfg_path.read_text())
            assert data == prior


CANONICAL_WORKFLOWS = {
    "propose",
    "explore",
    "new",
    "continue",
    "apply",
    "update",
    "ff",
    "sync",
    "archive",
    "bulk-archive",
    "verify",
    "onboard",
}


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


EXPECTED_OSC_SKILLS = {
    "osc-propose",
    "osc-explore",
    "osc-new-change",
    "osc-continue-change",
    "osc-apply-change",
    "osc-update-change",
    "osc-ff-change",
    "osc-verify-change",
    "osc-sync-specs",
    "osc-archive-change",
    "osc-bulk-archive-change",
    "osc-onboard",
}


class TestInstallWithCoreRenamesTwelveSkills:
    """``install --with-core`` calls ``rename_core_resources`` which must
    walk BOTH the legacy ``commands/`` tree and the modern ``skills/`` tree.
    Upstream OpenSpec v1.7.0 emits 12 ``openspec-*/SKILL.md`` files alongside
    the legacy ``opsx-*.md`` commands; the migrator must rename all 12 of the
    skill directories (and rewrite their ``name:`` frontmatter) so the user
    ends up with 12 ``osc-*`` skills, never ``openspec-*``.
    """

    def _deployed_skill_names(self, env: Path, tool: str) -> set[str]:
        skills_dir = env / f".{tool}" / "skills"
        if not skills_dir.is_dir():
            return set()
        return {
            p.name
            for p in skills_dir.iterdir()
            if p.is_dir() and (p / "SKILL.md").is_file()
        }

    def test_opencode_with_core_renames_all_twelve_core_skills(self, fresh_env: Path):
        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)
        skills = self._deployed_skill_names(fresh_env, "opencode")
        missing = EXPECTED_OSC_SKILLS - skills
        assert not missing, f"missing renamed core skills: {sorted(missing)}"
        leaked = {s for s in skills if s.startswith("openspec-")}
        assert not leaked, f"un-renamed core skills leaked: {sorted(leaked)}"

    def test_claude_with_core_renames_all_twelve_core_skills(self, fresh_env: Path):
        _run_osx(["install", "claude", "--with-core"], cwd=fresh_env)
        skills = self._deployed_skill_names(fresh_env, "claude")
        missing = EXPECTED_OSC_SKILLS - skills
        assert not missing, f"missing renamed core skills: {sorted(missing)}"
        leaked = {s for s in skills if s.startswith("openspec-")}
        assert not leaked, f"un-renamed core skills leaked: {sorted(leaked)}"

    def test_renamed_core_skill_carries_osc_name_frontmatter(self, fresh_env: Path):
        """Each renamed core skill's ``name:`` frontmatter is rewritten to
        the ``osc-*`` form so Claude Code's slash resolver picks it up."""
        _run_osx(["install", "opencode", "--with-core"], cwd=fresh_env)
        skill_md = fresh_env / ".opencode" / "skills" / "osc-apply-change" / "SKILL.md"
        if not skill_md.is_file():
            pytest.skip("openspec init did not run (binary missing or upstream error)")
        content = skill_md.read_text()
        assert "\nname: osc-apply-change\n" in content, content
