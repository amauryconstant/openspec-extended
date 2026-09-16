#!/usr/bin/env python3
"""Unit tests for ``purge_managed_resources``.

Covers path-scoping, prefix ownership, keep-set semantics, layout
differences between OpenCode and Claude, and symlink safety. No subprocess,
no AI, no filesystem outside ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from source.cli import (
    _backup_existing,
    _core_keep_set,
    _expected_extension_names,
    _purge_identical_backups,
    _purge_nested_core_orphans,
    _rewrite_renamed_references,
    purge_managed_resources,
    rename_core_resources,
)
from source.tools import REGISTRY

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _seed_opencode_legacy(target_dir: Path) -> None:
    """Seed a fully populated OpenCode-style target tree."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Skills (managed dirs + a custom one)
    for skill in ("osx-concepts", "osx-workflow", "osx-old-skill", "osc-apply-change"):
        _write(target_dir / "skills" / skill / "SKILL.md", skill)
    _write(target_dir / "skills" / "custom-review" / "SKILL.md", "kept")

    # Agents
    _write(target_dir / "agents" / "osx-analyzer.md")
    _write(target_dir / "agents" / "osx-old-agent.md")
    _write(target_dir / "agents" / "local-reviewer.md", "kept")

    # Commands (flat)
    _write(target_dir / "commands" / "osx-phase0.md")
    _write(target_dir / "commands" / "osx-old-cmd.md")
    _write(target_dir / "commands" / "openspec-old-legacy.md")
    _write(target_dir / "commands" / "custom.md", "kept")


def _seed_claude_legacy(target_dir: Path) -> None:
    """Seed a fully populated Claude-style target tree."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Skills
    for skill in (
        "osx-concepts",
        "osx-workflow",
        "osx-old-skill",
        "osc-archive-change",
    ):
        _write(target_dir / "skills" / skill / "SKILL.md", skill)
    _write(target_dir / "skills" / "custom-review" / "SKILL.md", "kept")

    # Commands nested under osx/ and osc/
    for name in ("phase0", "phase1", "old-cmd", "phase99"):
        _write(target_dir / "commands" / "osx" / f"{name}.md")
    for name in ("apply-change", "archive-change", "old-osc-cmd"):
        _write(target_dir / "commands" / "osc" / f"{name}.md")

    # Legacy flat files that should also be purged
    _write(target_dir / "commands" / "openspec-legacy-flat.md")

    # Custom command subdir with custom file (must NOT be touched)
    _write(target_dir / "commands" / "custom" / "my-command.md", "kept")


# ---------------------------------------------------------------------------
# Per-tool cleanup (OpenCode + Claude)
# ---------------------------------------------------------------------------


class TestCleanup:
    """Covers ``purge_managed_resources`` per-tool behaviour on a fully
    seeded tree. Each row is one of the original ``TestOpenCodeCleanup`` /
    ``TestClaudeCleanup`` cases."""

    @pytest.mark.parametrize(
        "tool_id,seed_func,keep,prefixes,must_be_gone,must_remain",
        [
            # OpenCode cases
            (
                "opencode",
                _seed_opencode_legacy,
                {"osx-concepts", "osx-workflow", "osx-phase0"},
                ("osx-",),
                [Path("skills/osx-old-skill")],
                [Path("skills/osx-concepts"), Path("skills/osx-workflow"), Path("skills/custom-review")],
            ),
            (
                "opencode",
                _seed_opencode_legacy,
                {"osx-phase0", "osx-concepts", "osx-workflow", "osx-analyzer"},
                ("osx-",),
                [Path("commands/osx-old-cmd.md")],
                [Path("commands/osx-phase0.md"), Path("commands/custom.md")],
            ),
            (
                "opencode",
                _seed_opencode_legacy,
                {"osx-analyzer", "osx-concepts", "osx-workflow", "osx-phase0"},
                ("osx-",),
                [Path("agents/osx-old-agent.md")],
                [Path("agents/osx-analyzer.md"), Path("agents/local-reviewer.md")],
            ),
            (
                "opencode",
                _seed_opencode_legacy,
                {"osx-concepts", "osx-workflow", "osx-phase0", "osx-analyzer"},
                ("osx-",),
                [Path("commands/openspec-old-legacy.md")],
                [],
            ),
            (
                "opencode",
                _seed_opencode_legacy,
                {"osx-concepts", "osx-workflow", "osx-phase0", "osx-analyzer"},
                ("osx-",),
                [],
                [Path("skills/osc-apply-change")],
            ),
            # Claude cases
            (
                "claude",
                _seed_claude_legacy,
                {"osx-phase0", "osx-phase1", "osx-concepts", "osx-workflow"},
                ("osx-",),
                [
                    Path("commands/osx/old-cmd.md"),
                    Path("commands/osx/phase99.md"),
                ],
                [
                    Path("commands/osx/phase0.md"),
                    Path("commands/osx/phase1.md"),
                ],
            ),
            (
                "claude",
                _seed_claude_legacy,
                {
                    "osc-apply-change",
                    "osc-archive-change",
                    "osx-concepts",
                    "osx-workflow",
                    "osx-phase0",
                },
                ("osc-",),
                [Path("commands/osc/old-osc-cmd.md")],
                [
                    Path("commands/osc/apply-change.md"),
                    Path("commands/osc/archive-change.md"),
                ],
            ),
            (
                "claude",
                _seed_claude_legacy,
                {"osx-phase0", "osx-concepts", "osx-workflow"},
                ("osx-",),
                [Path("commands/openspec-legacy-flat.md")],
                [],
            ),
            (
                "claude",
                _seed_claude_legacy,
                {"osx-phase0", "osx-concepts", "osx-workflow"},
                ("osx-",),
                [],
                [Path("commands/custom/my-command.md")],
            ),
        ],
    )
    def test_cleanup(
        self,
        tmp_path: Path,
        tool_id: str,
        seed_func,
        keep: set[str],
        prefixes: tuple[str, ...],
        must_be_gone: list[Path],
        must_remain: list[Path],
    ):
        target = tmp_path / f".{tool_id}"
        seed_func(target)
        purge_managed_resources(
            target, tool_id, keep_names=keep, prefixes=prefixes
        )
        for path in must_be_gone:
            assert not (target / path).exists(), (
                f"{path} should be gone after {tool_id} cleanup"
            )
        for path in must_remain:
            assert (target / path).exists() or (target / path).is_dir(), (
                f"{path} should remain after {tool_id} cleanup"
            )


class TestCleanupScopedToTargetTool:
    """``purge_managed_resources`` must not touch the other tool's tree."""

    def test_opencode_cleanup_leaves_claude_tree_alone(self, tmp_path: Path):
        opencode = tmp_path / ".opencode"
        claude = tmp_path / ".claude"
        _seed_opencode_legacy(opencode)
        _seed_claude_legacy(claude)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow"}

        purge_managed_resources(
            opencode, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        # Claude tree entirely untouched
        assert (claude / "skills" / "osx-old-skill").is_dir()
        assert (claude / "commands" / "osx" / "old-cmd.md").is_file()


# ---------------------------------------------------------------------------
# Prefix ownership / safety
# ---------------------------------------------------------------------------


class TestPrefixSafety:
    def test_does_not_remove_non_prefixed_names(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        # Custom resources with names that are NEAR but not exact matches
        _write(target / "skills" / "my-osx-tool" / "SKILL.md")
        _write(target / "skills" / "osx_custom" / "SKILL.md")
        _write(target / "skills" / "oscillator" / "SKILL.md")
        _write(target / "commands" / "oscillator.md")
        keep: set[str] = set()

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-", "osc-")
        )

        assert (target / "skills" / "my-osx-tool").is_dir()
        assert (target / "skills" / "osx_custom").is_dir()
        assert (target / "skills" / "oscillator").is_dir()
        assert (target / "commands" / "oscillator.md").is_file()

    def test_osc_only_purge_does_not_touch_osx(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        _write(target / "skills" / "osx-keep" / "SKILL.md")
        _write(target / "skills" / "osc-remove" / "SKILL.md")
        keep: set[str] = {"osx-keep"}

        purge_managed_resources(target, "opencode", keep_names=keep, prefixes=("osc-",))

        assert (target / "skills" / "osx-keep").is_dir()
        assert not (target / "skills" / "osc-remove").exists()

    def test_keeps_explicitly_named_resource(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        _write(target / "skills" / "osx-phase0" / "SKILL.md")
        keep = {"osx-phase0"}

        removed = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert removed == 0
        assert (target / "skills" / "osx-phase0").is_dir()


# ---------------------------------------------------------------------------
# Idempotency, symlinks, and edge cases
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_running_twice_is_a_noop(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow", "osx-analyzer"}

        first = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )
        second = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert first > 0
        assert second == 0

    def test_no_op_when_target_dir_missing(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        # intentionally not created
        removed = purge_managed_resources(
            target, "opencode", keep_names=set(), prefixes=("osx-",)
        )
        assert removed == 0

    def test_no_op_when_resources_dir_missing(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir()
        removed = purge_managed_resources(
            target, "opencode", keep_names=set(), prefixes=("osx-",)
        )
        assert removed == 0

    def test_unknown_tool_raises(self, tmp_path: Path):
        with pytest.raises(ValueError):
            purge_managed_resources(
                tmp_path, "bogus", keep_names=set(), prefixes=("osx-",)
            )


class TestSymlinkSafety:
    def test_symlinked_skill_dir_is_unlinked_not_followed(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel.md"
        sentinel.write_text("do-not-touch")

        skill_link = target / "skills" / "osx-orphan"
        skill_link.symlink_to(outside)

        removed = purge_managed_resources(
            target, "opencode", keep_names=set(), prefixes=("osx-",)
        )

        assert removed == 1
        assert not skill_link.exists()
        # The symlink target must remain intact
        assert sentinel.is_file()
        assert sentinel.read_text() == "do-not-touch"


# ---------------------------------------------------------------------------
# Helper-function tests
# ---------------------------------------------------------------------------


class TestExpectedExtensionNames:
    def test_returns_all_resources_when_autonomous_enabled(self):
        names = _expected_extension_names("opencode", with_orchestration=True)
        assert "osx-workflow" in names
        assert "osx-phase0" in names
        assert "osx-analyzer" in names

    def test_excludes_autonomous_resources_when_disabled(self):
        names = _expected_extension_names("opencode", with_orchestration=False)
        # osx-workflow is gated by --with-orchestration, so it's excluded
        assert "osx-workflow" not in names
        # Phase commands are gated by --with-orchestration
        assert "osx-phase0" not in names
        assert "osx-analyzer" not in names


class TestCoreKeepSet:
    def test_discovers_osc_skills(self, tmp_path: Path):
        skills = tmp_path / "skills"
        for name in ("osc-apply-change", "osc-archive-change", "osc-stale"):
            (skills / name).mkdir(parents=True)
            (skills / name / "SKILL.md").write_text(name)

        keep = _core_keep_set(tmp_path)

        assert keep == {"osc-apply-change", "osc-archive-change", "osc-stale"}

    def test_derives_osc_command_canonical_names_claude(self, tmp_path: Path):
        osc_dir = tmp_path / "commands" / "osc"
        osc_dir.mkdir(parents=True)
        for stem in ("apply-change", "archive-change"):
            (osc_dir / f"{stem}.md").write_text(stem)

        keep = _core_keep_set(tmp_path)

        assert "osc-apply-change" in keep
        assert "osc-archive-change" in keep

    def test_ignores_non_osc_skills(self, tmp_path: Path):
        skills = tmp_path / "skills"
        (skills / "osx-workflow").mkdir(parents=True)
        (skills / "osx-workflow" / "SKILL.md").write_text("x")
        (skills / "osc-apply-change").mkdir(parents=True)
        (skills / "osc-apply-change" / "SKILL.md").write_text("x")

        keep = _core_keep_set(tmp_path)

        assert "osx-workflow" not in keep
        assert "osc-apply-change" in keep


# ---------------------------------------------------------------------------
# Core rename: opsx-* → osc-* (flat) and opsx/ → osc/ (Claude nested)
# ---------------------------------------------------------------------------


CANONICAL_CORE_WORKFLOW_IDS = [
    "apply",
    "archive",
    "bulk-archive",
    "continue",
    "explore",
    "ff",
    "new",
    "onboard",
    "propose",
    "sync",
    "update",
    "verify",
]


class TestRenameCoreResources:
    """``rename_core_resources`` rewrites the artifacts produced by
    ``openspec init --profile custom`` (``opsx-<id>.md`` / ``opsx/<id>.md``)
    into the openspec-extended convention (``osc-<id>.md`` /
    ``osc/<id>.md``). Every canonical workflow ID must round-trip cleanly.
    """

    @pytest.mark.parametrize("wid", CANONICAL_CORE_WORKFLOW_IDS)
    def test_renames_opencode_flat_command(self, tmp_path: Path, monkeypatch, wid: str):
        target = tmp_path / ".opencode"
        (target / "commands").mkdir(parents=True)
        (target / "commands" / f"opsx-{wid}.md").write_text(
            f"---\ndescription: {wid}\n---\n"
        )

        monkeypatch.chdir(tmp_path)
        rename_core_resources("opencode")

        assert (target / "commands" / f"osc-{wid}.md").is_file()
        assert not (target / "commands" / f"opsx-{wid}.md").exists()

    @pytest.mark.parametrize("wid", CANONICAL_CORE_WORKFLOW_IDS)
    def test_renames_claude_nested_command(self, tmp_path: Path, monkeypatch, wid: str):
        target = tmp_path / ".claude"
        (target / "commands" / "opsx").mkdir(parents=True)
        (target / "commands" / "opsx" / f"{wid}.md").write_text(
            f"---\nname: {wid}\n---\n"
        )

        monkeypatch.chdir(tmp_path)
        rename_core_resources("claude")

        assert (target / "commands" / "osc" / f"{wid}.md").is_file()
        assert not (target / "commands" / "opsx" / f"{wid}.md").exists()

    def test_renames_skill_dirs(self, tmp_path: Path, monkeypatch):
        target = tmp_path / ".opencode"
        (target / "skills" / "openspec-apply-change").mkdir(parents=True)
        (target / "skills" / "openspec-apply-change" / "SKILL.md").write_text("x")

        monkeypatch.chdir(tmp_path)
        rename_core_resources("opencode")

        assert (target / "skills" / "osc-apply-change").is_dir()
        assert not (target / "skills" / "openspec-apply-change").exists()


# ---------------------------------------------------------------------------
# Body rewriter: /opsx-* and /opsx: → /osc-* / /osc:  (with fence guard)
# ---------------------------------------------------------------------------


class TestRewriteRenamedReferences:
    """``_rewrite_renamed_references`` rewrites the upstream
    ``openspec init --profile custom`` slash-command vocabulary so the
    installed tree consistently advertises the same ``/osc-*`` /
    ``/osc:*`` commands that the filename rename produces.

    Locks the contract:
      - inline prose, list items, table cells: rewrite
      - fenced code blocks: also rewrite (upstream places assistant
        output templates inside fences; leaving them intact propagates
        the stale upstream vocabulary into the installed tree)
      - line-start slash commands: still rewrite (regression guard)
      - frontmatter ``OPSX:`` labels: rewrite
      - rewriting an already-rewritten file: idempotent no-op
    """

    def test_inline_prose_rewrite(self):
        text = (
            "- Prompt: \"The artifacts are ready for review. "
            "When you are ready, run `/opsx-apply` or ask me to apply.\"\n"
        )
        out = _rewrite_renamed_references(text)
        assert "`/osc-apply`" in out
        assert "/opsx-apply" not in out

    def test_colon_form_rewrite(self):
        text = (
            "Use `/opsx:continue <name>` to resume artifact creation, "
            "or `/opsx:archive` when done.\n"
        )
        out = _rewrite_renamed_references(text)
        assert "`/osc:continue <name>`" in out
        assert "`/osc:archive`" in out
        assert "/opsx:" not in out

    def test_list_item_and_table_cell_rewrite(self):
        text = (
            "| `/opsx-propose` | Create a change and generate all artifacts |\n"
            "| `/opsx-explore` | Think through problems before/during work  |\n"
            "- `/opsx-verify` to wrap up\n"
        )
        out = _rewrite_renamed_references(text)
        assert "| `/osc-propose` |" in out
        assert "| `/osc-explore` |" in out
        assert "- `/osc-verify` to wrap up" in out
        assert "/opsx-" not in out

    def test_fenced_code_block_also_rewritten(self):
        text = (
            "Run `/opsx-archive` to finish.\n"
            "\n"
            "```bash\n"
            "/opsx-apply add-auth\n"
            "```\n"
            "\n"
            "Also see `/opsx-update`.\n"
        )
        out = _rewrite_renamed_references(text)
        assert "`/osc-archive`" in out
        assert "`/osc-update`" in out
        # Code-block contents are also rewritten — the upstream
        # ``/opsx-*`` vocabulary is stale the moment the wrapper
        # renames the files, regardless of where the reference lives:
        assert "/osc-apply add-auth" in out
        assert "/opsx-" not in out

    def test_tilde_fence_also_rewritten(self):
        text = (
            "Inline `/opsx-apply` should rewrite.\n"
            "\n"
            "~~~yaml\n"
            "/opsx-archive: keep-me\n"
            "~~~\n"
        )
        out = _rewrite_renamed_references(text)
        assert "`/osc-apply`" in out
        assert "/osc-archive: keep-me" in out
        assert "/opsx-" not in out

    def test_line_start_rewrite_still_works(self):
        text = "- /opsx-archive <name>\n- /opsx-verify <name>\n"
        out = _rewrite_renamed_references(text)
        assert "- /osc-archive <name>" in out
        assert "- /osc-verify <name>" in out
        assert "/opsx-" not in out

    def test_frontmatter_opsx_label_rewritten(self):
        text = (
            "---\n"
            "name: osc-propose\n"
            "OPSX: Propose a new change\n"
            "---\n"
            "Body with `/opsx-apply`.\n"
        )
        out = _rewrite_renamed_references(text)
        assert "OSC: Propose a new change" in out
        assert "OPSX:" not in out
        assert "`/osc-apply`" in out
        assert "/opsx-" not in out

    def test_roundtrip_against_previous_install_backup(self):
        """Previous-install backups (pre-v1.10.5) contain ``/osc-apply``
        already; running the rewriter must be idempotent — no further
        rewrites, no spurious replacement of the canonical form.
        """
        text = (
            "**Input**: Optionally specify a change name "
            "(e.g., `/osc-apply add-auth`).\n"
            "Always announce how to override (e.g., `/osc-archive <other>`).\n"
        )
        out = _rewrite_renamed_references(text)
        assert "`/osc-apply add-auth`" in out
        assert "`/osc-archive <other>`" in out
        assert "/opsx-" not in out

    def test_no_frontmatter_rewrite_still_works(self):
        text = (
            "Run `/opsx-apply` after the artifacts are ready.\n"
            "Then `/opsx-archive` to finish.\n"
        )
        out = _rewrite_renamed_references(text)
        assert "`/osc-apply`" in out
        assert "`/osc-archive`" in out
        assert "/opsx-" not in out


# ---------------------------------------------------------------------------
# Phase 1B: backup dedup + nested orphan purge on install
# ---------------------------------------------------------------------------


class TestBackupSkipOnIdenticalContent:
    """``_backup_existing`` short-circuits when the incoming bytes match
    the existing file's bytes — the wrapper is about to overwrite its own
    previous output with the same content, so there is nothing user-
    authored to preserve.
    """

    def test_returns_none_when_bytes_match(self, tmp_path: Path):
        target = tmp_path / "file.md"
        target.write_bytes(b"hello")
        assert _backup_existing(target, incoming_bytes=b"hello") is None
        # No backup file created:
        assert list(tmp_path.iterdir()) == [target]

    def test_creates_backup_when_bytes_differ(self, tmp_path: Path):
        target = tmp_path / "file.md"
        target.write_bytes(b"old")
        backup = _backup_existing(target, incoming_bytes=b"new")
        assert backup is not None
        assert backup.read_bytes() == b"old"
        # Backup path follows the naming convention:
        assert backup.name.startswith("file.md.user-backup-")

    def test_creates_backup_when_incoming_bytes_absent(self, tmp_path: Path):
        # Legacy callers that don't pass content get the existing behavior
        # (back up unconditionally when the destination exists).
        target = tmp_path / "file.md"
        target.write_bytes(b"x")
        backup = _backup_existing(target)
        assert backup is not None
        assert backup.read_bytes() == b"x"

    def test_returns_none_when_target_missing(self, tmp_path: Path):
        # No destination file: nothing to back up, regardless of bytes.
        target = tmp_path / "absent.md"
        assert _backup_existing(target, incoming_bytes=b"x") is None

    def test_dir_target_always_copied(self, tmp_path: Path):
        # The byte-equality short-circuit applies to files only; directory
        # targets always copy (rare path; commands/osc vs commands/opsx).
        d = tmp_path / "sub"
        d.mkdir()
        (d / "x.md").write_bytes(b"x")
        backup = _backup_existing(d, incoming_bytes=b"x")
        assert backup is not None
        assert backup.is_dir()
        assert (backup / "x.md").read_bytes() == b"x"


class TestPurgeIdenticalBackups:
    """``_purge_identical_backups`` removes ``*.user-backup-*`` files
    whose bytes match the corresponding non-backup sibling. User-
    authored backups (mismatched bytes) survive untouched.
    """

    def _seed_skill(
        self, root: Path, original: bytes, backup: bytes,
        backup_name: str = "SKILL.md.user-backup-1",
    ) -> Path:
        skill_dir = root / "skills" / "osc-apply-change"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_bytes(original)
        (skill_dir / backup_name).write_bytes(backup)
        return skill_dir

    def test_purges_matching_backup(self, tmp_path: Path):
        d = self._seed_skill(tmp_path, original=b"same", backup=b"same")
        assert _purge_identical_backups(tmp_path) == 1
        assert not (d / "SKILL.md.user-backup-1").exists()
        assert (d / "SKILL.md").exists()

    def test_keeps_mismatched_backup(self, tmp_path: Path):
        d = self._seed_skill(tmp_path, original=b"new", backup=b"user-edited")
        assert _purge_identical_backups(tmp_path) == 0
        assert (d / "SKILL.md.user-backup-1").exists()

    def test_handles_commands_dir(self, tmp_path: Path):
        cmd_dir = tmp_path / "commands"
        cmd_dir.mkdir()
        (cmd_dir / "osc-apply.md").write_bytes(b"x")
        (cmd_dir / "osc-apply.md.user-backup-1").write_bytes(b"x")
        assert _purge_identical_backups(tmp_path) == 1
        assert not (cmd_dir / "osc-apply.md.user-backup-1").exists()

    def test_idempotent_when_no_backups(self, tmp_path: Path):
        (tmp_path / "skills").mkdir()
        assert _purge_identical_backups(tmp_path) == 0
        assert _purge_identical_backups(tmp_path) == 0

    def test_keeps_backup_with_no_original(self, tmp_path: Path):
        # Orphan backup (no sibling): keep it. We only purge identical
        # backups whose original is on disk to compare against.
        skill_dir = tmp_path / "skills" / "osc-X"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md.user-backup-orphan").write_bytes(b"x")
        assert _purge_identical_backups(tmp_path) == 0
        assert (skill_dir / "SKILL.md.user-backup-orphan").exists()

    def test_recurses_into_nested_dirs(self, tmp_path: Path):
        # `skills/` walk uses rglob so the cleanup reaches nested orphans
        # too (e.g. `osc-X/openspec-X/SKILL.md.user-backup-*`).
        nested_dir = tmp_path / "skills" / "osc-X" / "openspec-X"
        nested_dir.mkdir(parents=True)
        (nested_dir / "SKILL.md").write_bytes(b"x")
        (nested_dir / "SKILL.md.user-backup-1").write_bytes(b"x")
        assert _purge_identical_backups(tmp_path) == 1


class TestNestedOrphanPurgeRunsOnInstall:
    """``_purge_nested_core_orphans`` is called from ``deploy_core`` so
    ``install --with-core`` cleans up ``osc-X/openspec-X/SKILL.md``
    nests in the same pass that creates them. The update path inherits
    this for free.
    """

    def test_removes_nested_orphan(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        skill_dir = target / "skills" / "osc-apply-change"
        orphan = skill_dir / "openspec-apply-change"
        orphan.mkdir(parents=True)
        (orphan / "SKILL.md").write_text("# orphan")
        # Real sibling so the tree is otherwise well-formed:
        (skill_dir / "SKILL.md").write_text("# real")

        removed = _purge_nested_core_orphans(target)

        assert not orphan.exists()
        assert (skill_dir / "SKILL.md").exists()
        assert removed >= 1

    def test_keeps_user_authored_nested_dirs(self, tmp_path: Path):
        # Only `openspec-*` / `opsx-*` named descendants are purged.
        target = tmp_path / ".opencode"
        skill_dir = target / "skills" / "osc-apply-change"
        user_subdir = skill_dir / "references"
        user_subdir.mkdir(parents=True)
        (user_subdir / "extra.md").write_text("# user-authored")

        _purge_nested_core_orphans(target)

        assert user_subdir.exists()
        assert (user_subdir / "extra.md").exists()


# ---------------------------------------------------------------------------
# Phase 1B: registry-driven dispatch in purge_managed_resources
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_id", ["opencode", "claude"])
class TestPurgeRoutesViaAdapterCommandsStyle:
    """Phase 1B wires ``purge_managed_resources`` dispatch through
    ``REGISTRY[tool].commands_style`` instead of literal ``tool ==
    "opencode"`` / ``tool != "claude"`` comparisons. These tests pin
    the same byte-output as the pre-1B literal-id branches."""

    def test_empty_target_returns_zero(self, tmp_path, tool_id):
        """Both shipped tools dispatch cleanly when there's nothing to remove.

        Regression net: pre-1B code reached the ``if tool == "opencode"``
        / ``else`` branch without raising; the same is true after 1B
        via ``adapter.commands_style == "flat"`` / ``elif ... ==
        "namespaced-with-skill-mirror"``."""
        target = tmp_path / f"fake-{tool_id}"
        target.mkdir()
        (target / "commands").mkdir()
        removed = purge_managed_resources(
            target, tool_id, keep_names=set(), prefixes=("osx-",)
        )
        assert removed == 0

    def test_commands_style_mapping_is_shipped_set(self, tool_id):
        """Sanity guard: every shipped tool's commands_style is one of
        the values the dispatch understands. If a v1.11.0 adapter
        lands with an unrecognised style and isn't accompanied by
        dispatch support in ``purge_managed_resources``, this test
        fails alongside the deploy itself."""
        adapter = REGISTRY[tool_id]
        assert adapter.commands_style in {
            "flat",
            "namespaced",
            "namespaced-with-skill-mirror",
            "skills-only",
        }


@pytest.mark.unit
class TestPurgeHandlesNamespacedStyleAsNoop:
    """Phase 2A: ``commands_style == "namespaced"`` is a real no-op
    branch in ``purge_managed_resources`` (was aspirational before).
    Confirm dispatch reaches the no-op branch without raising."""

    def test_purge_handles_namespaced_style_as_noop(self, tmp_path):
        from source.tools import ToolAdapter

        synthetic = ToolAdapter(
            tool_id="synthetic-namespaced",
            skills_dir=".synthetic",
            commands_dir="commands",
            commands_style="namespaced",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="synthetic",
            runner_kind="opencode_run",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix="osx-",
            docs_file="AGENTS.md",
            tool_name="Synthetic",
            detect_paths=(".synthetic",),
        )
        target = tmp_path / ".synthetic"
        target.mkdir()
        # No need to seed any commands/ content — the no-op branch
        # walks nothing.
        import pytest as _pytest
        with _pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "synthetic-namespaced", synthetic)
            removed = purge_managed_resources(
                target, "synthetic-namespaced", keep_names=set(), prefixes=("osx-",)
            )
        assert removed == 0


class TestPurgeRejectsUnknownTool:
    """``purge_managed_resources`` validation now reads from REGISTRY."""

    def test_unknown_tool_raises_value_error(self, tmp_path):
        target = tmp_path / "fake-target"
        target.mkdir()
        with pytest.raises(ValueError, match="Unknown tool"):
            purge_managed_resources(target, "bogus", keep_names=set(), prefixes=("osx-",))
