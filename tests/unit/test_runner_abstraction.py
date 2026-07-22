#!/usr/bin/env python3
"""
Unit tests for source.orchestrator.runner.

Tests the Runner abstraction without actually spawning AI subprocesses.
"""

from unittest.mock import MagicMock

import pytest

from source.lib.osx import OSXError


@pytest.mark.unit
class TestDetectRunner:
    def test_detects_opencode(self, tmp_path, monkeypatch):
        (tmp_path / ".opencode").mkdir()
        monkeypatch.chdir(tmp_path)
        from source.orchestrator.runner import detect_runner
        runner = detect_runner(tmp_path)
        assert runner.name == "opencode"

    def test_detects_claude(self, tmp_path, monkeypatch):
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)
        from source.orchestrator.runner import detect_runner
        runner = detect_runner(tmp_path)
        assert runner.name == "claude"

    def test_opencode_takes_precedence(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        (tmp_path / ".claude").mkdir()
        from source.orchestrator.runner import detect_runner
        runner = detect_runner(tmp_path)
        assert runner.name == "opencode"

    def test_no_runner_raises(self, tmp_path):
        from source.orchestrator.runner import detect_runner
        with pytest.raises(OSXError) as e:
            detect_runner(tmp_path)
        assert e.value.code == "no_runner_detected"


@pytest.mark.unit
class TestRunResult:
    def test_run_result_has_pid_field(self):
        from source.orchestrator.runner import RunResult
        result = RunResult(exit_code=0, log_path=None, timed_out=False, error=None, pid=12345)
        assert result.pid == 12345

    def test_run_result_pid_default_none(self):
        from source.orchestrator.runner import RunResult
        result = RunResult(exit_code=0)
        assert result.pid is None


@pytest.mark.unit
class TestOpencodeRunner:
    def test_missing_binary_raises(self, monkeypatch):
        from source.orchestrator.runner import OpencodeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: None)
        runner = OpencodeRunner()
        with pytest.raises(OSXError) as e:
            runner.run(RunRequest(command="osx-phase0", agent="osx-analyzer", change_id="foo"))
        assert e.value.code == "runner_not_found"

    def test_successful_run(self, monkeypatch):
        from source.orchestrator.runner import OpencodeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 4242
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = OpencodeRunner()
        result = runner.run(
            RunRequest(
                command="osx-phase0",
                agent="osx-analyzer",
                change_id="my-change",
                title="Test",
            ),
        )
        assert result.exit_code == 0
        assert result.pid == 4242
        assert "opencode" in captured["cmd"]
        assert "run" in captured["cmd"]
        assert "--command" in captured["cmd"]
        assert "osx-phase0" in captured["cmd"]
        assert "--agent" in captured["cmd"]
        assert "osx-analyzer" in captured["cmd"]
        assert "my-change" in captured["cmd"]

    def test_includes_model_when_set(self, monkeypatch):
        from source.orchestrator.runner import OpencodeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = OpencodeRunner()
        runner.run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="x",
                model="claude-opus-4",
            ),
        )
        assert "--model=claude-opus-4" in captured["cmd"]


@pytest.mark.unit
class TestClaudeRunner:
    def test_missing_binary_raises(self, monkeypatch):
        from source.orchestrator.runner import ClaudeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: None)
        runner = ClaudeRunner()
        with pytest.raises(OSXError) as e:
            runner.run(RunRequest(command="osx-phase0", agent="osx-analyzer", change_id="foo"))
        assert e.value.code == "runner_not_found"

    def test_successful_run(self, monkeypatch):
        from source.orchestrator.runner import ClaudeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 7777
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = ClaudeRunner()
        result = runner.run(
            RunRequest(
                command="osx-phase0",
                agent="osx-analyzer",
                change_id="my-change",
            ),
        )
        assert result.exit_code == 0
        assert result.pid == 7777
        assert captured["cmd"][0] == "claude"
        assert "--print" in captured["cmd"]
        prompt = captured["cmd"][-1]
        assert "/osx-phase0" in prompt
        assert "my-change" in prompt

    def test_includes_model_when_set(self, monkeypatch):
        from source.orchestrator.runner import ClaudeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = ClaudeRunner()
        runner.run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="x",
                model="claude-opus-4",
            ),
        )
        idx = captured["cmd"].index("--model")
        assert captured["cmd"][idx + 1] == "claude-opus-4"

    def test_env_is_merged_and_forwarded(self, monkeypatch):
        from source.orchestrator.runner import OpencodeRunner, RunRequest
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["env"] = kwargs["env"]
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 4242
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        OpencodeRunner().run(
            RunRequest(
                command="osx-phase0",
                agent="osx-analyzer",
                change_id="my-change",
                env={"OSX_AUTONOMOUS": "1"},
            )
        )

        import os

        assert captured["env"]["OSX_AUTONOMOUS"] == "1"
        assert captured["env"]["PATH"] == os.environ["PATH"]