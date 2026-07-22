#!/usr/bin/env python3
"""
Tests for the orchestrator's preflight step.

Regression coverage for Fix 5 + Fix 6:
- Preflight runs even when `--clean` is NOT passed (was previously gated on clean).
- AI binary probe is platform-aware (opencode vs claude).
- `--from-phase` still skips preflight.
- `--clean` still wipes transient state files (its semantics are preserved).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def env_opencode(tmp_path: Path) -> Path:
    """Minimal OpenCode-flavoured fixture: .opencode/ + openspec/changes/<id> + git repo."""
    env = tmp_path
    subprocess.run(["git", "init", "-q"], cwd=env, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=env, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=env, check=True)
    (env / "README.md").write_text("x")
    subprocess.run(["git", "add", "README.md"], cwd=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=env, check=True)

    (env / "openspec" / "changes" / "c1").mkdir(parents=True)
    (env / ".opencode" / "skills").mkdir(parents=True)
    (env / ".opencode" / "commands").mkdir(parents=True)

    # Required skills per validate_skills
    for skill in [
        "osx-concepts",
        "osx-workflow",
        "osx-review-artifacts",
        "osx-modify-artifacts",
        "osx-review-test-compliance",
        "osx-maintain-ai-docs",
        "osx-commit",
    ]:
        (env / ".opencode" / "skills" / skill).mkdir(parents=True)
        (env / ".opencode" / "skills" / skill / "SKILL.md").write_text("# x")

    for phase in range(7):
        (env / ".opencode" / "commands" / f"osx-phase{phase}.md").write_text("# x")
    return env


@pytest.fixture
def env_claude(tmp_path: Path) -> Path:
    """Minimal Claude-flavoured fixture: .claude/ instead of .opencode/."""
    env = tmp_path
    subprocess.run(["git", "init", "-q"], cwd=env, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=env, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=env, check=True)
    (env / "README.md").write_text("x")
    subprocess.run(["git", "add", "README.md"], cwd=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=env, check=True)

    (env / "openspec" / "changes" / "c1").mkdir(parents=True)
    (env / ".claude" / "skills").mkdir(parents=True)
    (env / ".claude" / "commands" / "osx").mkdir(parents=True)

    for skill in [
        "osx-concepts",
        "osx-workflow",
        "osx-review-artifacts",
        "osx-modify-artifacts",
        "osx-review-test-compliance",
        "osx-maintain-ai-docs",
        "osx-commit",
    ]:
        (env / ".claude" / "skills" / skill).mkdir(parents=True)
        (env / ".claude" / "skills" / skill / "SKILL.md").write_text("# x")

    for phase in range(7):
        (env / ".claude" / "commands" / "osx" / f"osx-phase{phase}.md").write_text("# x")
    return env


def _mock_subprocess_ok(probed: dict):
    """Return a fake subprocess.run that records the binaries it was asked about."""

    def _run(cmd, *args, **kwargs):
        probed.setdefault("binaries", []).append(cmd[0])
        if cmd[0] == "git" and "rev-parse" in cmd:
            return MagicMock(returncode=0, stdout="abc123\n", stderr="")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    return _run


def _patch_preflight_env(monkeypatch, env: Path):
    """Patch subprocess.run so tool probes succeed; count validate_* invocations.

    Also mocks ``osx_lib.get_core_version()`` to return (1, 6, 0) so the
    orchestrator's minimum-version gate does not block the test. Tests that
    exercise the gate itself patch it explicitly.
    """
    probed: dict = {}
    monkeypatch.setattr(
        "source.orchestrator.engine.subprocess.run", _mock_subprocess_ok(probed)
    )
    # Gate the minimum-core-version check so preflight tests focus on the
    # preflight behaviour, not the floor enforced in commit 6.
    import source.lib.osx as _osx
    monkeypatch.setattr(_osx, "get_core_version", lambda: (1, 6, 0))
    return probed


@pytest.mark.integration
class TestPreflightAlwaysRuns:
    """Without --clean, preflight still runs (Fix 5)."""

    def test_preflight_runs_without_clean_flag(self, env_opencode, monkeypatch):
        """Normal first-run (no --clean) must still probe tools and validate skills."""
        from source.orchestrator import engine as eng

        probed = _patch_preflight_env(monkeypatch, env_opencode)

        calls = {"validate_skills": 0, "validate_commands": 0, "validate_git": 0,
                 "validate_change_dir": 0, "validate_schema": 0, "record_baseline": 0}

        monkeypatch.setattr(eng, "validate_skills",
                            lambda s: calls.__setitem__("validate_skills", calls["validate_skills"] + 1))
        monkeypatch.setattr(eng, "validate_commands",
                            lambda s: calls.__setitem__("validate_commands", calls["validate_commands"] + 1))
        monkeypatch.setattr(eng, "validate_git",
                            lambda s: calls.__setitem__("validate_git", calls["validate_git"] + 1))
        monkeypatch.setattr(eng, "validate_change_dir",
                            lambda s: calls.__setitem__("validate_change_dir", calls["validate_change_dir"] + 1))
        monkeypatch.setattr(eng, "validate_schema",
                            lambda s: calls.__setitem__("validate_schema", calls["validate_schema"] + 1))
        monkeypatch.setattr(eng, "record_baseline",
                            lambda s: calls.__setitem__("record_baseline", calls["record_baseline"] + 1))

        # Skip AI runner dispatch
        monkeypatch.setattr(eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0)))

        state = eng.OrchestratorState(
            change_id="c1",
            change_dir=env_opencode / "openspec" / "changes" / "c1",
            clean=False,
            force=True,
        )

        monkeypatch.chdir(env_opencode)
        with pytest.raises(SystemExit):
            eng.run_orchestrator(state)

        for k, v in calls.items():
            assert v == 1, f"{k} should run once during preflight; got {v}"

        assert "git" in probed["binaries"]
        assert "jq" in probed["binaries"]
        assert "openspec" in probed["binaries"]
        assert "opencode" in probed["binaries"]

    def test_preflight_runs_with_clean_flag(self, env_opencode, monkeypatch):
        """--clean wipes state files AND runs preflight (preflight was previously double-gated)."""
        from source.orchestrator import engine as eng

        # Write a state file that --clean should remove
        state_file = env_opencode / "openspec" / "changes" / "c1" / "state.json"
        state_file.write_text('{"phase":"PHASE2","iteration":1}')
        baseline = env_opencode / ".openspec-baseline.json"
        baseline.write_text("{}")

        _patch_preflight_env(monkeypatch, env_opencode)

        called = {"validate_skills": False, "record_baseline": False}
        monkeypatch.setattr(eng, "validate_skills", lambda s: called.__setitem__("validate_skills", True))
        monkeypatch.setattr(eng, "validate_commands", lambda s: None)
        monkeypatch.setattr(eng, "validate_git", lambda s: None)
        monkeypatch.setattr(eng, "validate_change_dir", lambda s: None)
        monkeypatch.setattr(eng, "validate_schema", lambda s: None)
        monkeypatch.setattr(eng, "record_baseline", lambda s: called.__setitem__("record_baseline", True))

        monkeypatch.setattr(eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0)))

        state = eng.OrchestratorState(
            change_id="c1",
            change_dir=env_opencode / "openspec" / "changes" / "c1",
            clean=True,
            force=True,
        )
        monkeypatch.chdir(env_opencode)
        with pytest.raises(SystemExit):
            eng.run_orchestrator(state)

        # State files wiped
        assert not state_file.exists()
        assert not baseline.exists()
        # Preflight still ran
        assert called["validate_skills"] is True
        assert called["record_baseline"] is True

    def test_preflight_skipped_with_from_phase(self, env_opencode, monkeypatch):
        """--from-phase continues to skip preflight."""
        from source.orchestrator import engine as eng

        probed = _patch_preflight_env(monkeypatch, env_opencode)

        called = {"validate_skills": False}
        monkeypatch.setattr(eng, "validate_skills", lambda s: called.__setitem__("validate_skills", True))
        monkeypatch.setattr(eng, "validate_commands", lambda s: None)
        monkeypatch.setattr(eng, "validate_git", lambda s: None)
        monkeypatch.setattr(eng, "validate_change_dir", lambda s: None)
        monkeypatch.setattr(eng, "validate_schema", lambda s: None)
        monkeypatch.setattr(eng, "record_baseline", lambda s: None)

        monkeypatch.setattr(eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0)))

        state = eng.OrchestratorState(
            change_id="c1",
            change_dir=env_opencode / "openspec" / "changes" / "c1",
            clean=False,
            force=True,
            from_phase="PHASE3",
        )
        monkeypatch.chdir(env_opencode)
        with pytest.raises(SystemExit):
            eng.run_orchestrator(state)

        assert called["validate_skills"] is False
        assert probed.get("binaries", []) == [], "no tool probes should fire under --from-phase"


@pytest.mark.integration
class TestPreflightPlatformAware:
    """AI binary probe matches the active platform (Fix 6)."""

    def test_opencode_repo_probes_opencode(self, env_opencode, monkeypatch):
        from source.orchestrator import engine as eng

        probed = _patch_preflight_env(monkeypatch, env_opencode)

        for fn in ("validate_skills", "validate_commands", "validate_git",
                   "validate_change_dir", "validate_schema", "record_baseline"):
            monkeypatch.setattr(eng, fn, lambda s: None)
        monkeypatch.setattr(eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0)))

        state = eng.OrchestratorState(
            change_id="c1",
            change_dir=env_opencode / "openspec" / "changes" / "c1",
            clean=False,
            force=True,
        )
        monkeypatch.chdir(env_opencode)
        with pytest.raises(SystemExit):
            eng.run_orchestrator(state)

        assert "opencode" in probed["binaries"]
        assert "claude" not in probed["binaries"]

    def test_claude_repo_probes_claude(self, env_claude, monkeypatch):
        from source.orchestrator import engine as eng

        probed = _patch_preflight_env(monkeypatch, env_claude)

        for fn in ("validate_skills", "validate_commands", "validate_git",
                   "validate_change_dir", "validate_schema", "record_baseline"):
            monkeypatch.setattr(eng, fn, lambda s: None)
        monkeypatch.setattr(eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0)))

        state = eng.OrchestratorState(
            change_id="c1",
            change_dir=env_claude / "openspec" / "changes" / "c1",
            clean=False,
            force=True,
        )
        monkeypatch.chdir(env_claude)
        with pytest.raises(SystemExit):
            eng.run_orchestrator(state)

        assert "claude" in probed["binaries"]
        assert "opencode" not in probed["binaries"]
