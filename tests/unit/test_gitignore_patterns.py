#!/usr/bin/env python3

from pathlib import Path

import pytest

from source.cli import update_gitignore


@pytest.mark.unit
def test_active_change_ignores_are_followed_by_archive_reincludes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".gitignore").write_text("existing-pattern\n")
    monkeypatch.chdir(tmp_path)

    update_gitignore()

    lines = (tmp_path / ".gitignore").read_text().splitlines()
    filenames = (
        "state.json",
        "complete.json",
        "iterations.json",
        "decision-log.json",
        "verification-report.md",
        "reflections.md",
        "test-compliance-report.md",
        "suggestions.md",
    )
    for filename in filenames:
        ignore_index = lines.index(f"openspec/changes/*/{filename}")
        assert lines[ignore_index + 1] == f"!openspec/changes/archive/**/{filename}"

    log_index = lines.index(".osx-orchestrate-*.log")
    assert lines[log_index + 1] == (
        "!openspec/changes/archive/**/.osx-orchestrate-*.log"
    )
