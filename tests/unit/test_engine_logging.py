#!/usr/bin/env python3
# ruff: noqa: EXE001 - shebang is intentional
"""
Contract tests for engine log helpers (`log`, `log_success`, `log_warning`,
`log_error`) and their file-write side.

Locks in:

- Each ``log_*`` writes its message to ``state.log_file`` when set (in
  addition to stdout/stderr).
- The file write is ANSI-stripped so the on-disk log stays greppable.
- A failed write to ``state.log_file`` does not raise — it logs to
  stderr and the orchestrator continues.
- ``log_verbose`` retains its asymmetric semantics (file when verbose is
  off, stdout only when verbose is on).

If any of these regress, the E2E ``log: has expected content`` test
turns red because the orchestrator's startup banner is missing from the
archived log file. See ``orchestrator/source/orchestrator/engine.py`` for
the implementation under test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from source.orchestrator.engine import (
    OrchestratorState,
    _append_log_to_file,
    log,
    log_error,
    log_success,
    log_verbose,
    log_warning,
    show_progress,
)

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _state(tmp_path, *, name: str = "log.log", verbose: bool = False) -> OrchestratorState:
    """Build an OrchestratorState with a writable log_file path."""
    return OrchestratorState(
        change_id="test-change",
        no_color=True,
        verbose=verbose,
        log_file=tmp_path / name,
    )


@pytest.mark.unit
class TestLogWritesToFile:
    """Each ``log_*`` helper writes to ``state.log_file`` (ANSI-stripped)."""

    def test_log_writes_to_file(self, tmp_path, capsys):
        state = _state(tmp_path)
        log(state, "hello world")
        assert state.log_file.read_text(encoding="utf-8").strip().endswith(
            "hello world"
        )
        assert "[INFO]" in state.log_file.read_text(encoding="utf-8")

    def test_log_success_writes_to_file(self, tmp_path):
        state = _state(tmp_path)
        log_success(state, "ok")
        text = state.log_file.read_text(encoding="utf-8")
        assert text.strip().endswith("ok")
        assert "[OK]" in text

    def test_log_warning_writes_to_file(self, tmp_path):
        state = _state(tmp_path)
        log_warning(state, "be careful")
        text = state.log_file.read_text(encoding="utf-8")
        assert text.strip().endswith("be careful")
        assert "[WARN]" in text

    def test_log_error_writes_to_file(self, tmp_path):
        state = _state(tmp_path)
        log_error(state, "boom")
        text = state.log_file.read_text(encoding="utf-8")
        assert text.strip().endswith("boom")
        assert "[ERROR]" in text

    def test_messages_append_in_order(self, tmp_path):
        state = _state(tmp_path)
        log(state, "one")
        log_success(state, "two")
        log_warning(state, "three")
        log_error(state, "four")
        lines = [
            line
            for line in state.log_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert any(line.endswith("one") for line in lines)
        assert any(line.endswith("two") for line in lines)
        assert any(line.endswith("three") for line in lines)
        assert any(line.endswith("four") for line in lines)

    def test_file_write_is_ansi_stripped(self, tmp_path, capsys):
        """Rich-colored output from a non-no_color run must not leave ESC bytes."""
        state = OrchestratorState(
            change_id="test-change",
            no_color=False,
            verbose=False,
            log_file=tmp_path / "log.log",
        )
        log(state, "color me")
        text = state.log_file.read_text(encoding="utf-8")
        assert "color me" in text
        assert ANSI_ESCAPE.search(text) is None, (
            f"log file should be ANSI-stripped; got: {text!r}"
        )


@pytest.mark.unit
class TestLogFileWriteResilience:
    """A failed file write must never raise out of ``_append_log_to_file``."""

    def test_no_log_file_is_noop(self):
        state = OrchestratorState(change_id="test-change", log_file=None)
        # Must not raise.
        _append_log_to_file(state, "anything")

    def test_unwritable_path_does_not_raise(self, tmp_path, capsys):
        # Force a permission failure by pointing at a path whose parent
        # is a regular file (so creating the log file inside it fails).
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        state = OrchestratorState(
            change_id="test-change",
            log_file=blocker / "log.log",
        )
        # Must not raise — orchestrator must not die because of its log file.
        _append_log_to_file(state, "should not crash")
        # The helper logs the failure to stderr (avoids recursion).
        assert "Failed to append to log file" in capsys.readouterr().err


@pytest.mark.unit
class TestLogVerboseSemantics:
    """``log_verbose`` keeps its asymmetric behavior across the fix."""

    def test_verbose_writes_to_stdout_only(self, tmp_path, capsys):
        state = _state(tmp_path, verbose=True)
        log_verbose(state, "spammy")
        out = capsys.readouterr().out
        assert "spammy" in out
        # File should be untouched when verbose is on.
        assert not state.log_file.exists()

    def test_non_verbose_writes_to_file(self, tmp_path, capsys):
        state = _state(tmp_path, verbose=False)
        # ``log_verbose`` only appends when the file already exists; the
        # orchestrator's startup banner creates it before any verbose
        # line is emitted, so pre-create it here to mirror that order.
        state.log_file.touch()
        log_verbose(state, "quiet")
        text = state.log_file.read_text(encoding="utf-8")
        assert "quiet" in text
        # Stdout should NOT have it (the helper only writes to one place).
        assert "quiet" not in capsys.readouterr().out


@pytest.mark.unit
class TestLogPostUnlinkSurvives:
    """``log*`` recreates ``state.log_file`` after an unlink.

    Relevant because ``engine.py``'s ``--clean`` path unlinks the prior
    ``.osx-orchestrate-{id}.log`` during the prelude. If the unlink ran
    *after* the banner had been written, the orchestrator's own banner
    would be missing from the archived log. ``open(..., "a")`` recreates
    the file — so the helpers stay correct across that wipe — but the
    ordering in engine.py is still load-bearing. ``TestPreludeOrderLock``
    below locks that ordering on the source file directly.
    """

    def test_log_after_unlink_survives(self, tmp_path):
        state = _state(tmp_path)

        log(state, "before")
        assert state.log_file.exists()
        state.log_file.unlink()
        assert not state.log_file.exists()

        log(state, "after")

        assert state.log_file.exists()
        text = state.log_file.read_text(encoding="utf-8")
        assert "before" not in text, (
            "the unlink should have removed the prior content; "
            "a stale read would indicate the unlink didn't run"
        )
        assert "after" in text, (
            "log() must recreate the log file (open mode 'a') and "
            "append — without this, --clean would wipe the orchestrator's "
            "banner from the archived osx-orchestrate.log"
        )


@pytest.mark.unit
class TestPreludeOrderLock:
    """The ``--clean`` block must precede the banner log calls in engine.py.

    Pure source-order lock: cheapest way to keep the prelude from drifting
    back into the wrong order. Catches the same regression that
    ``tests/e2e/full-workflow.bats::'log: has expected content'`` flags,
    without needing an end-to-end AI run to surface it.
    """

    ENGINE_PATH = (
        Path(__file__).resolve().parents[2]
        / "orchestrator"
        / "source"
        / "orchestrator"
        / "engine.py"
    )

    def test_engine_source_exists(self):
        assert self.ENGINE_PATH.is_file(), (
            f"engine.py not found at {self.ENGINE_PATH}; "
            f"if the file moved, update TestPreludeOrderLock.ENGINE_PATH"
        )

    def test_clean_block_precedes_banner(self):
        text = self.ENGINE_PATH.read_text(encoding="utf-8")

        clean_idx = text.find("if state.clean:")
        banner_idx = text.find('"OpenSpec Autonomous Implementation"')

        assert clean_idx != -1, (
            "engine.py must still contain the `if state.clean:` block; "
            "if the prelude was refactored, replace this lock with a "
            "behavioral equivalent"
        )
        assert banner_idx != -1, (
            "engine.py must still emit the orchestrator's banner; "
            "if the banner was renamed, replace this lock with a regex "
            "over the new banner line"
        )
        assert clean_idx < banner_idx, (
            "engine.py: the `if state.clean:` block must precede the "
            "orchestrator's banner `log(...)` call. Running --clean "
            "after the banner would wipe the just-written banner from "
            "state.log_file, dropping it from the archived "
            "osx-orchestrate.log. See the regression history in "
            "`tests/unit/test_engine_logging.py`."
        )


@pytest.mark.unit
class TestShowProgressMirrorsToFile:
    """``show_progress()`` mirrors its output through ``log()`` so the
    Progress Summary reaches ``state.log_file``.

    Regression coverage for ``tests/e2e/full-workflow.bats::'log: has
    expected content'``. Before the fix, every line in ``show_progress``
    used ``print()`` and the archived ``osx-orchestrate.log`` was missing
    the Progress Summary block even though it landed in stdout. This
    suite pins the contract at unit-test speed.
    """

    def test_progress_summary_lands_in_file(self, tmp_path):
        state = _state(tmp_path)
        show_progress(state)
        text = state.log_file.read_text(encoding="utf-8")
        assert "Progress Summary" in text

    def test_summary_includes_field_lines(self, tmp_path):
        state = OrchestratorState(
            change_id="test-change",
            no_color=True,
            verbose=False,
            log_file=tmp_path / "log.log",
            total_invocations=42,
        )
        show_progress(state)
        text = state.log_file.read_text(encoding="utf-8")
        for needle in (
            "Change ID: test-change",
            "Total invocations: 42",
            "Elapsed time:",
            "================================",
        ):
            assert needle in text, (
                f"show_progress output missing {needle!r}; "
                f"full file:\n{text}"
            )

    def test_summary_is_ansi_stripped(self, tmp_path):
        state = OrchestratorState(
            change_id="test-change",
            no_color=False,
            verbose=False,
            log_file=tmp_path / "log.log",
        )
        show_progress(state)
        text = state.log_file.read_text(encoding="utf-8")
        assert ANSI_ESCAPE.search(text) is None, (
            f"show_progress must mirror through log() so the file stays "
            f"ANSI-stripped; got: {text!r}"
        )

    def test_summary_does_not_raise_with_none_change_dir(self, tmp_path):
        state = OrchestratorState(
            change_id="test-change",
            no_color=True,
            verbose=False,
            log_file=tmp_path / "log.log",
            change_dir=None,
        )
        show_progress(state)
        assert "Progress Summary" in state.log_file.read_text(encoding="utf-8")
