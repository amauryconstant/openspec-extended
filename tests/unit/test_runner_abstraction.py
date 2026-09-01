#!/usr/bin/env python3
"""
Unit tests for source.orchestrator.runner.

Tests the Runner abstraction without actually spawning AI subprocesses.
"""

from pathlib import Path
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
class TestRunRequestExtraPrompt:
    """A.4: ``RunRequest.extra_prompt`` carries project-level operation
    guidance to the runner. OpenCode attaches it via ``--file``; Claude
    prepends it to the slash-command prompt."""

    def test_extra_prompt_defaults_to_empty(self):
        from source.orchestrator.runner import RunRequest

        req = RunRequest(command="osx-phase1", agent="osx-builder", change_id="x")
        assert req.extra_prompt == ""

    def test_extra_prompt_round_trips(self):
        from source.orchestrator.runner import RunRequest

        req = RunRequest(
            command="osx-phase1",
            agent="osx-builder",
            change_id="x",
            extra_prompt="hello",
        )
        assert req.extra_prompt == "hello"

    def test_opencode_attaches_extra_prompt_via_file_flag(self, monkeypatch):
        from source.orchestrator.runner import OpencodeRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")
        captured: dict = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            # Read the guidance file *during* Popen — the runner deletes
            # it in its ``finally`` block, so by the time the test sees
            # the path it's gone.
            captured["file_path"] = Path(cmd[cmd.index("--file") + 1])
            captured["file_content"] = captured["file_path"].read_text()
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 4242
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        OpencodeRunner().run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="my-change",
                extra_prompt="Always run unit tests.",
            )
        )

        # ``opencode run --file <path>`` is the documented way to attach
        # additional context to the message (positional args are forwarded
        # as ``$1``/``$2``/... to the slash command, so prepending there
        # would break the templates).
        cmd = captured["cmd"]
        assert "--file" in cmd
        assert cmd[cmd.index("--file") + 1].endswith(".md")
        assert captured["file_content"] == "Always run unit tests."

    def test_opencode_omits_file_flag_when_extra_prompt_empty(self, monkeypatch):
        from source.orchestrator.runner import OpencodeRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")
        captured: dict = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 4242
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        OpencodeRunner().run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="my-change",
            )
        )

        assert "--file" not in captured["cmd"]

    def test_opencode_cleans_up_temp_file_after_run(self, monkeypatch):
        """The guidance temp file is removed once the subprocess returns."""
        from source.orchestrator.runner import OpencodeRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/opencode")
        captured: dict = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["file_path"] = Path(cmd[cmd.index("--file") + 1])
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 4242
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        OpencodeRunner().run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="my-change",
                extra_prompt="guidance body",
            )
        )

        # Temp file existed during the run (file content was readable
        # because Popen captured the path); afterwards it is gone.
        assert not captured["file_path"].exists()

    def test_claude_prepends_extra_prompt_to_slash_command(self, monkeypatch):
        from source.orchestrator.runner import ClaudeRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
        captured: dict = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 7777
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        ClaudeRunner().run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="my-change",
                extra_prompt="Always run unit tests.",
            )
        )

        prompt = captured["cmd"][-1]
        assert prompt.startswith("Always run unit tests.")
        assert "/osx-phase1 my-change" in prompt

    def test_claude_prompt_unchanged_when_extra_prompt_empty(self, monkeypatch):
        from source.orchestrator.runner import ClaudeRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
        captured: dict = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 7777
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        ClaudeRunner().run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="my-change",
            )
        )

        assert captured["cmd"][-1] == "/osx-phase1 my-change"


@pytest.mark.unit
class TestRunResult:
    def test_run_result_has_pid_field(self):
        from source.orchestrator.runner import RunResult

        result = RunResult(
            exit_code=0, log_path=None, timed_out=False, error=None, pid=12345
        )
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
            runner.run(
                RunRequest(command="osx-phase0", agent="osx-analyzer", change_id="foo")
            )
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
            runner.run(
                RunRequest(command="osx-phase0", agent="osx-analyzer", change_id="foo")
            )
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


@pytest.mark.unit
class TestRunRequestStoreAndSchema:
    """M18: RunRequest carries ``store`` and ``schema_name``; the helper
    injects them as ``OSX_STORE`` / ``OSX_SCHEMA`` env vars in the
    subprocess so the AI-side ``osx`` CLI picks them up."""

    def test_store_injects_osx_store_env(self, monkeypatch):
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
                store="team-store",
            )
        )

        assert captured["env"]["OSX_STORE"] == "team-store"
        assert "OSX_SCHEMA" not in captured["env"]

    def test_schema_name_injects_osx_schema_env(self, monkeypatch):
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
                schema_name="spec-driven",
            )
        )

        assert captured["env"]["OSX_SCHEMA"] == "spec-driven"
        assert "OSX_STORE" not in captured["env"]

    def test_both_store_and_schema_inject_both_envs(self, monkeypatch):
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
                store="team-store",
                schema_name="custom",
            )
        )

        assert captured["env"]["OSX_STORE"] == "team-store"
        assert captured["env"]["OSX_SCHEMA"] == "custom"

    def test_no_store_no_env_var(self, monkeypatch):
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
            )
        )

        assert "OSX_STORE" not in captured["env"]
        assert "OSX_SCHEMA" not in captured["env"]

    def test_claude_runner_also_forwards_store(self, monkeypatch):
        from source.orchestrator.runner import ClaudeRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/claude")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["env"] = kwargs["env"]
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 4242
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        ClaudeRunner().run(
            RunRequest(
                command="osx-phase0",
                agent="osx-analyzer",
                change_id="my-change",
                store="team-store",
            )
        )

        assert captured["env"]["OSX_STORE"] == "team-store"
