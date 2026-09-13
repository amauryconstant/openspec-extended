#!/usr/bin/env python3
"""
Unit tests for source.orchestrator.runner.

Tests the Runner abstraction without actually spawning AI subprocesses.
"""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from source.lib.osx import OSXError
from source.tools import REGISTRY, ToolAdapter


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


# ---------------------------------------------------------------------------
# Phase 1C tests — registry-driven dispatch + adapter plumbing.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectRunnerWalksRegistry:
    """Phase 1C: ``detect_runner`` walks ``REGISTRY`` in registration order
    and returns the runner for the first adapter whose ``detect_paths``
    includes an existing directory at ``project_root``. The four original
    tests above (``test_detects_opencode``, ``test_detects_claude``,
    ``test_opencode_takes_precedence``, ``test_no_runner_raises``) cover
    the shipped set; this class exercises the dispatch shape more
    deliberately, including a synthetic third adapter.
    """

    def test_detects_opencode_via_registry(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        from source.orchestrator.runner import OpencodeRunner, detect_runner

        runner = detect_runner(tmp_path)
        assert runner.name == "opencode"
        assert isinstance(runner, OpencodeRunner)
        assert runner.adapter is REGISTRY["opencode"]

    def test_detects_claude_via_registry(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        from source.orchestrator.runner import ClaudeRunner, detect_runner

        runner = detect_runner(tmp_path)
        assert runner.name == "claude"
        assert isinstance(runner, ClaudeRunner)
        assert runner.adapter is REGISTRY["claude"]

    def test_opencode_wins_ties_via_registration_order(self, tmp_path):
        # opencode is registered first; verify the registry walk produces
        # the same precedence as today's literal check.
        (tmp_path / ".opencode").mkdir()
        (tmp_path / ".claude").mkdir()
        from source.orchestrator.runner import detect_runner

        runner = detect_runner(tmp_path)
        assert runner.name == "opencode"

    def test_no_runner_detected_when_no_marker_dir(self, tmp_path):
        from source.orchestrator.runner import detect_runner

        with pytest.raises(OSXError) as e:
            detect_runner(tmp_path)
        assert e.value.code == "no_runner_detected"
        # Hint message lists registered tools so a user with a future
        # adapter knows their options.
        assert e.value.context.get("hint")
        assert "opencode" in e.value.context["hint"]
        assert "claude" in e.value.context["hint"]

    def test_detect_runner_uses_detect_paths_per_adapter(
        self, tmp_path, monkeypatch
    ):
        # Inject a synthetic third adapter that detects on .foo/. Detect
        # must walk past the opencode/claude defaults to find it.
        #
        # The synthetic adapter uses ``runner_kind == "opencode_run"``
        # (which exists today) so commit 1 doesn't need
        # ``GenericPrintRunner`` yet — that lands in commit 2.
        from source.orchestrator.runner import OpencodeRunner, detect_runner

        foo_adapter = ToolAdapter(
            tool_id="foo",
            skills_dir=".foo",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="foo-",
            skill_prefix="/",
            runner_binary="foo",
            runner_kind="opencode_run",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Foo",
            detect_paths=(".foo",),
        )
        monkeypatch.setitem(REGISTRY, "foo", foo_adapter)
        try:
            (tmp_path / ".foo").mkdir()
            runner = detect_runner(tmp_path)
            # ``name`` on a class-attribute runner class (OpencodeRunner /
            # ClaudeRunner) is fixed at class level — it identifies the
            # runner kind, not the adapter. Use the adapter's tool_id to
            # verify the synthetic adapter was selected.
            assert isinstance(runner, OpencodeRunner)
            assert runner.adapter is foo_adapter
            assert runner.adapter.tool_id == "foo"
        finally:
            monkeypatch.delitem(REGISTRY, "foo")


@pytest.mark.unit
class TestRunnerForFactory:
    """``_runner_for(adapter)`` maps ``runner_kind`` to a concrete class."""

    def test_opencode_kind_returns_opencode_runner(self):
        from source.orchestrator.runner import OpencodeRunner, _runner_for

        runner = _runner_for(REGISTRY["opencode"])
        assert isinstance(runner, OpencodeRunner)
        assert runner.adapter is REGISTRY["opencode"]

    def test_claude_kind_returns_claude_runner(self):
        from source.orchestrator.runner import ClaudeRunner, _runner_for

        runner = _runner_for(REGISTRY["claude"])
        assert isinstance(runner, ClaudeRunner)
        assert runner.adapter is REGISTRY["claude"]

    def test_unknown_kind_raises(self):
        from source.orchestrator.runner import _runner_for

        adapter = ToolAdapter(
            tool_id="bad",
            skills_dir=".bad",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="bad",
            runner_kind="does_not_exist",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Bad",
            detect_paths=(".bad",),
        )
        with pytest.raises(OSXError) as e:
            _runner_for(adapter)
        assert e.value.code == "unknown_runner_kind"
        assert "does_not_exist" in e.value.message

    def test_generic_print_kind_returns_generic_runner(self):
        from source.orchestrator.runner import GenericPrintRunner, _runner_for

        adapter = ToolAdapter(
            tool_id="cursor",
            skills_dir=".cursor",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="cursor",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Cursor",
            detect_paths=(".cursor",),
        )
        runner = _runner_for(adapter)
        assert isinstance(runner, GenericPrintRunner)
        assert runner.adapter is adapter


@pytest.mark.unit
class TestAdapterAwareBinary:
    """``OpencodeRunner._binary()`` / ``ClaudeRunner._binary()`` resolve
    from ``adapter.runner_binary`` when set, fall back to the literal
    when the runner was constructed without an adapter (legacy call
    paths).
    """

    def test_opencode_runner_binary_defaults_to_opencode(self):
        from source.orchestrator.runner import OpencodeRunner

        runner = OpencodeRunner()
        assert runner._binary() == "opencode"

    def test_opencode_runner_binary_reads_from_adapter(self):
        from source.orchestrator.runner import OpencodeRunner

        adapter = replace(REGISTRY["opencode"], runner_binary="oc-renamed")
        runner = OpencodeRunner(adapter=adapter)
        assert runner._binary() == "oc-renamed"

    def test_claude_runner_binary_defaults_to_claude(self):
        from source.orchestrator.runner import ClaudeRunner

        runner = ClaudeRunner()
        assert runner._binary() == "claude"

    def test_claude_runner_binary_reads_from_adapter(self):
        from source.orchestrator.runner import ClaudeRunner

        adapter = replace(REGISTRY["claude"], runner_binary="cc-renamed")
        runner = ClaudeRunner(adapter=adapter)
        assert runner._binary() == "cc-renamed"


@pytest.mark.unit
class TestDetectRunnerErrorMessage:
    """The ``no_runner_detected`` error message lists registered tool ids
    so a user seeing it knows which commands to run."""

    def test_error_hint_lists_registered_tools(self, tmp_path):
        from source.orchestrator.runner import detect_runner

        with pytest.raises(OSXError) as e:
            detect_runner(tmp_path)
        hint = e.value.context["hint"]
        assert "opencode" in hint
        assert "claude" in hint

    def test_error_message_includes_project_root(self, tmp_path):
        from source.orchestrator.runner import detect_runner

        with pytest.raises(OSXError) as e:
            detect_runner(tmp_path)
        assert str(tmp_path) in e.value.message


@pytest.mark.unit
class TestGenericPrintRunner:
    """The v1.11.0 runner skeleton. Exercises the ``generic_print`` shape
    using a synthetic cursor-shaped adapter.

    No v1.10.0 adapter declares ``runner_kind == "generic_print"``, so the
    class is unreachable at runtime in this release — every test below
    constructs an explicit ``GenericPrintRunner(<synthetic adapter>)``.
    """

    def _make_adapter(self):
        return ToolAdapter(
            tool_id="cursor",
            skills_dir=".cursor",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="cursor",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Cursor",
            detect_paths=(".cursor",),
        )

    def test_missing_binary_raises(self, monkeypatch):
        from source.orchestrator.runner import GenericPrintRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: None)
        runner = GenericPrintRunner(self._make_adapter())
        with pytest.raises(OSXError) as e:
            runner.run(
                RunRequest(
                    command="osx-phase0", agent="osx-analyzer", change_id="foo"
                )
            )
        assert e.value.code == "runner_not_found"
        assert "cursor" in e.value.message

    def test_successful_run_spawns_expected_cmd(self, monkeypatch):
        from source.orchestrator.runner import GenericPrintRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/cursor")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 9999
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = GenericPrintRunner(self._make_adapter())
        result = runner.run(
            RunRequest(
                command="osx-phase0", agent="osx-analyzer", change_id="x"
            )
        )

        assert result.exit_code == 0
        assert result.pid == 9999
        assert captured["cmd"][0] == "cursor"
        assert "--print" in captured["cmd"]
        assert "--dangerously-skip-permissions" in captured["cmd"]
        prompt = captured["cmd"][-1]
        # Adapter's slash_prefix drives the prompt shape.
        assert prompt.endswith("/osx-phase0 x")

    def test_extra_prompt_prepended_to_prompt(self, monkeypatch):
        from source.orchestrator.runner import GenericPrintRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/cursor")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            mock.pid = 9999
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = GenericPrintRunner(self._make_adapter())
        runner.run(
            RunRequest(
                command="osx-phase1",
                agent="osx-builder",
                change_id="x",
                extra_prompt="Run unit tests.",
            )
        )
        prompt = captured["cmd"][-1]
        assert prompt.startswith("Run unit tests.")
        assert "/osx-phase1 x" in prompt

    def test_includes_model_when_set(self, monkeypatch):
        from source.orchestrator.runner import GenericPrintRunner, RunRequest

        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/cursor")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = GenericPrintRunner(self._make_adapter())
        runner.run(
            RunRequest(
                command="osx-phase0",
                agent="osx-analyzer",
                change_id="x",
                model="claude-opus-4",
            )
        )
        idx = captured["cmd"].index("--model")
        assert captured["cmd"][idx + 1] == "claude-opus-4"

    def test_name_attribute_is_adapter_tool_id(self):
        from source.orchestrator.runner import GenericPrintRunner

        runner = GenericPrintRunner(self._make_adapter())
        assert runner.name == "cursor"

    def test_slash_prefix_does_not_affect_prompt_shape(self, monkeypatch):
        # Mirrors ClaudeRunner's convention: the prompt is always
        # ``/<command> <change_id>``. The adapter's ``slash_prefix`` is a
        # deploy-time concern (how the tool spells slash commands in its
        # filesystem layout); at runtime each tool resolves its own
        # slash-command form from the deployed files. So whether the
        # adapter declares ``slash_prefix="osx-"`` or ``"osx:"``, the
        # prompt is the canonical ``/osx-phase0 x`` and the tool
        # interprets it against its own layout.
        from source.orchestrator.runner import GenericPrintRunner, RunRequest

        claude_style = ToolAdapter(
            tool_id="cursor-claude-style",
            skills_dir=".cursor",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="osx:",
            skill_prefix="/",
            runner_binary="cursor",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Cursor",
            detect_paths=(".cursor",),
        )
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/cursor")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            mock = MagicMock()
            mock.wait.return_value = 0
            mock.stdout = iter([])
            return mock

        monkeypatch.setattr("subprocess.Popen", fake_popen)
        runner = GenericPrintRunner(claude_style)
        runner.run(
            RunRequest(
                command="osx-phase0", agent="osx-analyzer", change_id="x"
            )
        )
        prompt = captured["cmd"][-1]
        assert prompt.endswith("/osx-phase0 x")
