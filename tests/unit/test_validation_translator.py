#!/usr/bin/env python3
"""
Unit tests for the validate_* functions and _translate_validate_payload helper
in source.lib.osx.

Subprocess is mocked so tests do not depend on a real `openspec` binary.
"""

import json
from unittest.mock import MagicMock

import pytest

from source.lib import osx


def make_run(stdout="", returncode=0, stderr="", exc=None):
    """Build a fake subprocess.run callable."""

    def _run(*args, **kwargs):
        if exc is not None:
            raise exc
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    return _run


@pytest.mark.unit
class TestTranslateValidatePayload:
    def test_translates_validation_failure(self):
        payload = {
            "items": [
                {
                    "id": "add-auth",
                    "type": "change",
                    "valid": False,
                    "issues": [
                        {
                            "level": "ERROR",
                            "path": "specs.auth/foo.md",
                            "message": "missing SHALL",
                        },
                    ],
                    "durationMs": 5,
                }
            ],
            "summary": {
                "totals": {"items": 1, "passed": 0, "failed": 1},
                "byType": {"change": {"items": 1, "passed": 0, "failed": 1}},
            },
            "version": "1.0",
            "root": {"path": "/tmp/proj", "source": "nearest"},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["message"] == "missing SHALL"
        assert result["errors"][0]["target"] == "add-auth"
        assert result["warnings"] == []
        assert result["info"] == []

    def test_translates_warning(self):
        payload = {
            "items": [
                {
                    "id": "spec-x",
                    "type": "spec",
                    "valid": True,
                    "issues": [
                        {
                            "level": "WARNING",
                            "path": "overview",
                            "message": "too brief",
                        },
                    ],
                    "durationMs": 3,
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is True
        assert result["errors"] == []
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["message"] == "too brief"

    def test_translates_info_level(self):
        payload = {
            "items": [
                {
                    "id": "spec-y",
                    "type": "spec",
                    "valid": True,
                    "issues": [
                        {
                            "level": "INFO",
                            "path": "requirements[0].text",
                            "message": "too long",
                        }
                    ],
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert len(result["info"]) == 1
        assert result["info"][0]["message"] == "too long"

    def test_translates_prevalidation_error(self):
        payload = {
            "status": [
                {
                    "severity": "error",
                    "code": "no_openspec_root",
                    "message": "No openspec/ directory found",
                    "fix": "Run openspec init",
                }
            ]
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is False
        assert result["diagnostics"][0]["code"] == "no_openspec_root"
        assert result["diagnostics"][0]["fix"] == "Run openspec init"
        assert result["errors"][0]["check"] == "no_openspec_root"

    def test_translates_ambiguous_item_error(self):
        payload = {
            "status": [
                {
                    "severity": "error",
                    "code": "ambiguous_item",
                    "message": "Ambiguous item 'foo'",
                    "fix": "Pass --type change|spec.",
                }
            ]
        }
        result = osx._translate_validate_payload(payload)
        assert result["diagnostics"][0]["code"] == "ambiguous_item"

    def test_preserves_line_numbers(self):
        payload = {
            "items": [
                {
                    "id": "spec-z",
                    "type": "spec",
                    "valid": False,
                    "issues": [
                        {
                            "level": "ERROR",
                            "path": "file",
                            "message": "structure issue",
                            "line": 42,
                        },
                    ],
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 0, "failed": 1}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["errors"][0]["line"] == 42

    def test_preserves_root_info(self):
        payload = {
            "items": [{"id": "a", "type": "spec", "valid": True, "issues": []}],
            "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
            "version": "1.0",
            "root": {"path": "/x", "source": "store", "store_id": "my-store"},
        }
        result = osx._translate_validate_payload(payload)
        assert result["root"]["source"] == "store"
        assert result["root"]["store_id"] == "my-store"

    def test_empty_items_list(self):
        payload = {
            "items": [],
            "summary": {"totals": {"items": 0, "passed": 0, "failed": 0}},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_failed_returns_unverifiable(self):
        """A success envelope without summary.totals.failed is unverifiable.

        Returns valid=None (unknown) and emits a warning diagnostic so callers
        downstream do not silently treat a malformed upstream payload as a
        pass. Any pre-existing per-item warnings are preserved alongside the
        new diagnostic.
        """
        payload = {
            "items": [
                {
                    "id": "spec-w",
                    "type": "spec",
                    "valid": True,
                    "issues": [
                        {
                            "level": "WARNING",
                            "path": "overview",
                            "message": "too brief",
                        },
                    ],
                }
            ],
            "summary": {"totals": {"items": 1, "passed": 1}},
            "version": "1.0",
            "root": {"path": "/tmp/proj", "source": "nearest"},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is None
        codes = [w.get("code") for w in result["warnings"]]
        assert "unverifiable_envelope" in codes
        envelope_warning = next(
            w for w in result["warnings"] if w.get("code") == "unverifiable_envelope"
        )
        assert envelope_warning["severity"] == "warning"
        assert "summary.totals.failed" in envelope_warning["message"]
        assert result["root"]["source"] == "nearest"
        assert any(w.get("message") == "too brief" for w in result["warnings"])

    def test_missing_totals_returns_unverifiable(self):
        """summary present but totals absent is also unverifiable."""
        payload = {
            "items": [],
            "summary": {},
            "version": "1.0",
            "root": {},
        }
        result = osx._translate_validate_payload(payload)
        assert result["valid"] is None
        assert any(w.get("code") == "unverifiable_envelope" for w in result["warnings"])


@pytest.mark.unit
class TestValidateChange:
    def test_includes_change_id_in_args(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [
                            {
                                "id": "my-change",
                                "type": "change",
                                "valid": True,
                                "issues": [],
                            }
                        ],
                        "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        result = osx.validate_change("my-change")
        assert "validate" in captured["cmd"]
        assert "my-change" in captured["cmd"]
        assert "--json" in captured["cmd"]
        assert "--no-interactive" in captured["cmd"]
        assert result["valid"] is True

    def test_appends_store_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_change("c", store="my-store")
        assert "--store" in captured["cmd"]
        assert "my-store" in captured["cmd"]

    def test_appends_strict_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_change("c", strict=True)
        assert "--strict" in captured["cmd"]


@pytest.mark.unit
class TestValidateSpec:
    def test_includes_type_spec(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_spec("authentication")
        assert "--type" in captured["cmd"]
        idx = captured["cmd"].index("--type")
        assert captured["cmd"][idx + 1] == "spec"


@pytest.mark.unit
class TestValidateAll:
    def test_includes_concurrency(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_all(concurrency=12)
        assert "--concurrency" in captured["cmd"]
        idx = captured["cmd"].index("--concurrency")
        assert captured["cmd"][idx + 1] == "12"

    def test_uses_extended_timeout(self, monkeypatch):
        captured_kwargs = {}

        def _run(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_all()
        assert captured_kwargs.get("timeout") == 60


@pytest.mark.unit
class TestConcurrencyEnv:
    """A.7: ``OPENSPEC_CONCURRENCY`` env var propagates to ``openspec validate --all``.

    Precedence: explicit ``concurrency`` arg > env var > default 6. Invalid env
    values (non-int, <=0, empty) fall back to 6 silently.
    """

    @staticmethod
    def _captured_run(captured):
        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        return _run

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        """OPENSPEC_CONCURRENCY=12 + concurrency=None -> subprocess gets --concurrency 12."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "12")
        captured = {}
        monkeypatch.setattr(
            osx.subprocess, "run", self._captured_run(captured)
        )
        osx.validate_all()
        assert "--concurrency" in captured["cmd"]
        idx = captured["cmd"].index("--concurrency")
        assert captured["cmd"][idx + 1] == "12"

    def test_explicit_wins_over_env_var(self, monkeypatch):
        """explicit concurrency=8 beats OPENSPEC_CONCURRENCY=12."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "12")
        captured = {}
        monkeypatch.setattr(
            osx.subprocess, "run", self._captured_run(captured)
        )
        osx.validate_all(concurrency=8)
        assert "--concurrency" in captured["cmd"]
        idx = captured["cmd"].index("--concurrency")
        assert captured["cmd"][idx + 1] == "8"

    def test_invalid_env_falls_back_to_default(self, monkeypatch):
        """Non-int env values fall back to 6."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "invalid")
        captured = {}
        monkeypatch.setattr(
            osx.subprocess, "run", self._captured_run(captured)
        )
        osx.validate_all()
        assert "--concurrency" in captured["cmd"]
        idx = captured["cmd"].index("--concurrency")
        assert captured["cmd"][idx + 1] == "6"

    def test_zero_env_falls_back_to_default(self, monkeypatch):
        """Env value of 0 falls back to 6 (must be > 0)."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "0")
        captured = {}
        monkeypatch.setattr(
            osx.subprocess, "run", self._captured_run(captured)
        )
        osx.validate_all()
        assert "--concurrency" in captured["cmd"]
        idx = captured["cmd"].index("--concurrency")
        assert captured["cmd"][idx + 1] == "6"


@pytest.mark.unit
class TestValidateChangesOnly:
    def test_uses_changes_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_changes_only()
        assert "--changes" in captured["cmd"]
        assert "--all" not in captured["cmd"]


@pytest.mark.unit
class TestValidateSpecsOnly:
    def test_uses_specs_flag(self, monkeypatch):
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.validate_specs_only()
        assert "--specs" in captured["cmd"]
        assert "--all" not in captured["cmd"]


@pytest.mark.unit
class TestValidateArchived:
    """v1.9.0+ `validate --archived` exposed as a first-class validate action."""

    def _make_run(self, captured):
        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            captured["timeout"] = kwargs.get("timeout")
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [],
                        "summary": {"totals": {"failed": 0}},
                        "version": "1.0",
                        "root": {},
                    }
                ),
                stderr="",
            )

        return _run

    def test_archived_all_changes_no_positional(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(osx.subprocess, "run", self._make_run(captured))
        result = osx.validate_archived()
        assert "--archived" in captured["cmd"]
        assert "--no-interactive" in captured["cmd"]
        # Layout: [openspec, validate, --archived, --no-interactive, --json]
        assert captured["cmd"][1] == "validate"
        assert captured["cmd"][2] == "--archived"
        assert result["valid"] is True

    def test_archived_specific_change(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(osx.subprocess, "run", self._make_run(captured))
        osx.validate_archived("my-change")
        # Layout: [openspec, validate, my-change, --archived, --no-interactive, --json]
        assert captured["cmd"][1] == "validate"
        assert captured["cmd"][2] == "my-change"
        assert captured["cmd"][3] == "--archived"

    def test_archived_strict_propagates(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(osx.subprocess, "run", self._make_run(captured))
        osx.validate_archived(strict=True)
        assert "--strict" in captured["cmd"]

    def test_archived_store_propagates(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(osx.subprocess, "run", self._make_run(captured))
        osx.validate_archived(store="my-store")
        assert "--store" in captured["cmd"]
        assert "my-store" in captured["cmd"]

    def test_archived_uses_extended_timeout(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(osx.subprocess, "run", self._make_run(captured))
        osx.validate_archived()
        assert captured["timeout"] == 60


@pytest.mark.unit
class TestValidateManifestCrossCheck:
    """M23: ``validate_skills`` and ``validate_commands`` cross-check the
    deployed ``manifest.toml`` so a manifest that omits a required skill
    or command is caught at preflight."""

    @staticmethod
    def _write_skill_dirs(project_root, skill_names, platform="opencode"):
        if platform == "opencode":
            base = project_root / ".opencode" / "skills"
        else:
            base = project_root / ".claude" / "skills"
        base.mkdir(parents=True, exist_ok=True)
        for skill in skill_names:
            (base / skill).mkdir(parents=True, exist_ok=True)
            (base / skill / "SKILL.md").write_text("# x")

    @staticmethod
    def _write_command_files(project_root, cmd_names, platform="opencode"):
        if platform == "opencode":
            base = project_root / ".opencode" / "commands"
        else:
            base = project_root / ".claude" / "commands" / "osx"
        base.mkdir(parents=True, exist_ok=True)
        for cmd in cmd_names:
            (base / f"{cmd}.md").write_text("# x")

    @staticmethod
    def _write_manifest(project_root, skills, commands, platform="opencode"):
        if platform == "opencode":
            manifest_path = project_root / ".opencode" / "manifest.toml"
        else:
            manifest_path = project_root / ".claude" / "manifest.toml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        content = "[resources]\n"
        if skills:
            content += "[resources.skills]\n"
            for s in skills:
                content += f'"{s}" = {{ version = "0.1.0" }}\n'
        if commands:
            content += "[resources.commands]\n"
            for c in commands:
                content += f'"{c}" = {{ version = "0.1.0" }}\n'
        manifest_path.write_text(content)

    def test_validate_skills_manifest_missing_skill_is_invalid(
        self, tmp_path, monkeypatch
    ):
        """A required skill present on disk but missing from manifest fails."""
        monkeypatch.chdir(tmp_path)
        from source.lib import osx as osx_lib

        all_skills = list(osx_lib.REQUIRED_SKILLS + osx_lib.REQUIRED_CORE_SKILLS)
        self._write_skill_dirs(tmp_path, all_skills, platform="opencode")
        # Omit one skill from the manifest
        self._write_manifest(
            tmp_path,
            skills=[s for s in all_skills if s != "osx-commit"],
            commands=[],
            platform="opencode",
        )

        result = osx_lib.validate_skills(project_root=tmp_path)
        assert result["valid"] is False
        assert any(
            e["check"] == "skills-manifest" and "osx-commit" in e["message"]
            for e in result["errors"]
        )

    def test_validate_skills_manifest_complete_is_valid(self, tmp_path, monkeypatch):
        """All required skills declared in manifest + on disk = valid."""
        monkeypatch.chdir(tmp_path)
        from source.lib import osx as osx_lib

        all_skills = list(osx_lib.REQUIRED_SKILLS + osx_lib.REQUIRED_CORE_SKILLS)
        self._write_skill_dirs(tmp_path, all_skills, platform="opencode")
        self._write_manifest(
            tmp_path, skills=all_skills, commands=[], platform="opencode"
        )

        result = osx_lib.validate_skills(project_root=tmp_path)
        assert result["valid"] is True

    def test_validate_skills_no_manifest_skips_cross_check(self, tmp_path, monkeypatch):
        """If no manifest is deployed, the cross-check is silently skipped."""
        monkeypatch.chdir(tmp_path)
        from source.lib import osx as osx_lib

        all_skills = list(osx_lib.REQUIRED_SKILLS + osx_lib.REQUIRED_CORE_SKILLS)
        self._write_skill_dirs(tmp_path, all_skills, platform="opencode")
        # No manifest written

        result = osx_lib.validate_skills(project_root=tmp_path)
        assert result["valid"] is True

    def test_validate_commands_manifest_missing_command_is_invalid(
        self, tmp_path, monkeypatch
    ):
        """A phase command present on disk but missing from manifest fails."""
        monkeypatch.chdir(tmp_path)
        from source.lib import osx as osx_lib
        from source.orchestrator.engine import PHASE_COMMANDS

        cmd_names = list(set(PHASE_COMMANDS.values()))
        self._write_command_files(tmp_path, cmd_names, platform="opencode")
        omitted = next(iter(cmd_names))
        self._write_manifest(
            tmp_path,
            skills=[],
            commands=[c for c in cmd_names if c != omitted],
            platform="opencode",
        )

        result = osx_lib.validate_commands(project_root=tmp_path)
        assert result["valid"] is False
        assert any(
            e["check"] == "commands-manifest" and omitted in e["message"]
            for e in result["errors"]
        )

    def test_validate_commands_agents_opencode_missing_agent_is_invalid(
        self, tmp_path, monkeypatch
    ):
        """PHASE_AGENTS entries must exist as files under agents/ (opencode)."""
        monkeypatch.chdir(tmp_path)
        from source.lib import osx as osx_lib
        from source.orchestrator.engine import PHASE_AGENTS, PHASE_COMMANDS

        cmd_names = list(set(PHASE_COMMANDS.values()))
        self._write_command_files(tmp_path, cmd_names, platform="opencode")
        all_skills = list(osx_lib.REQUIRED_SKILLS + osx_lib.REQUIRED_CORE_SKILLS)
        self._write_skill_dirs(tmp_path, all_skills, platform="opencode")
        self._write_manifest(
            tmp_path,
            skills=all_skills,
            commands=cmd_names,
            platform="opencode",
        )
        # Drop one of the agent files
        agents_dir = tmp_path / ".opencode" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for agent in set(PHASE_AGENTS.values()):
            (agents_dir / f"{agent}.md").write_text("# x")
        # Pick one and remove it
        omitted_agent = next(iter(PHASE_AGENTS.values()))
        (agents_dir / f"{omitted_agent}.md").unlink()

        result = osx_lib.validate_commands(project_root=tmp_path)
        assert result["valid"] is False
        assert any(
            e["check"] == "agents" and omitted_agent in e["message"]
            for e in result["errors"]
        )


@pytest.mark.unit
class TestReadChangeMetadata:
    """A.3: ``read_change_metadata`` parses ``.openspec.yaml`` and exposes the
    orchestration-relevant markers (schema, skip_specs, retire_capabilities).

    Never raises — missing or malformed files return ``{}`` with a stderr
    warning, mirroring ``resolve_schema``'s tolerance.
    """

    @staticmethod
    def _write_metadata(change_root, body: str) -> None:
        change_root.mkdir(parents=True, exist_ok=True)
        (change_root / ".openspec.yaml").write_text(body)

    def test_read_metadata_minimal(self, tmp_path):
        """Only `schema:` set returns just that key."""
        change = tmp_path / "openspec" / "changes" / "minimal"
        self._write_metadata(change, "schema: spec-driven\n")
        result = osx.read_change_metadata(change)
        assert result == {"schema": "spec-driven"}

    def test_read_metadata_retire_capabilities_true(self, tmp_path):
        """`retire_capabilities: true` is exposed as a Python bool."""
        change = tmp_path / "openspec" / "changes" / "retire"
        self._write_metadata(
            change,
            "schema: spec-driven\nretire_capabilities: true\n",
        )
        result = osx.read_change_metadata(change)
        assert result["schema"] == "spec-driven"
        assert result["retire_capabilities"] is True

    def test_read_metadata_skip_specs(self, tmp_path):
        """`skip_specs: true` round-trips."""
        change = tmp_path / "openspec" / "changes" / "skip"
        self._write_metadata(change, "schema: spec-driven\nskip_specs: true\n")
        result = osx.read_change_metadata(change)
        assert result["skip_specs"] is True

    def test_read_metadata_string_bool_tolerated(self, tmp_path):
        """Quoted "true"/"false" strings are coerced to Python booleans."""
        change = tmp_path / "openspec" / "changes" / "string-bool"
        self._write_metadata(
            change,
            "schema: spec-driven\nretire_capabilities: \"true\"\n",
        )
        result = osx.read_change_metadata(change)
        assert result["retire_capabilities"] is True

    def test_read_metadata_string_bool_false(self, tmp_path):
        """Quoted "false" coerces to False."""
        change = tmp_path / "openspec" / "changes" / "string-bool-false"
        self._write_metadata(
            change,
            "schema: spec-driven\nretire_capabilities: \"false\"\n",
        )
        result = osx.read_change_metadata(change)
        assert result["retire_capabilities"] is False

    def test_read_metadata_missing_file(self, tmp_path):
        """No .openspec.yaml returns {} (no exception)."""
        change = tmp_path / "openspec" / "changes" / "none"
        change.mkdir(parents=True)
        result = osx.read_change_metadata(change)
        assert result == {}

    def test_read_metadata_none_change_dir(self):
        """None change_dir returns {} (no exception)."""
        assert osx.read_change_metadata(None) == {}

    def test_read_metadata_malformed_yaml(self, tmp_path, capsys):
        """Invalid YAML returns {} and emits a warning, no exception."""
        change = tmp_path / "openspec" / "changes" / "broken"
        self._write_metadata(change, "schema: : invalid\n")
        result = osx.read_change_metadata(change)
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning: Could not load change metadata" in captured.err
        assert str(change / ".openspec.yaml") in captured.err

    def test_read_metadata_non_bool_field_ignored(self, tmp_path):
        """Non-bool/non-string values for boolean markers are ignored."""
        change = tmp_path / "openspec" / "changes" / "weird"
        self._write_metadata(
            change, "schema: spec-driven\nretire_capabilities: 42\n"
        )
        result = osx.read_change_metadata(change)
        assert "retire_capabilities" not in result

    def test_read_metadata_top_level_not_dict(self, tmp_path):
        """YAML root that is not a mapping returns {} (no fields)."""
        change = tmp_path / "openspec" / "changes" / "scalar"
        self._write_metadata(change, "just-a-string\n")
        result = osx.read_change_metadata(change)
        assert result == {}


@pytest.mark.unit
class TestValidateChangeDirPlanning:
    """A.1: ``validate_change_dir`` consults core's ``isPlanningComplete``
    signal (v1.8.0+) before falling back to a local file-existence check.

    All tests mock ``_fetch_planning_status`` so they don't require a real
    ``openspec`` binary on PATH. The helper returns ``None`` to simulate the
    CLI being unavailable.
    """

    @staticmethod
    def _write_minimal_change(change_root) -> None:
        change_root.mkdir(parents=True, exist_ok=True)
        (change_root / "proposal.md").write_text("# p")
        (change_root / "design.md").write_text("# d")
        (change_root / "tasks.md").write_text("- [ ] one\n- [ ] two\n")
        specs = change_root / "specs"
        specs.mkdir()
        (specs / "auth.md").write_text("# auth")

    def test_planning_complete_true(self, tmp_path, monkeypatch):
        """Core says planning is complete and lists no pending artifacts."""
        change_root = tmp_path / "openspec" / "changes" / "c1"
        self._write_minimal_change(change_root)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            osx,
            "_fetch_planning_status",
            lambda change_id, *, store=None: {
                "isPlanningComplete": True,
                "artifacts": [],
            },
        )

        result = osx.validate_change_dir("c1")

        assert result["valid"] is True
        assert result["planning_complete"] is True
        assert result["missing_artifacts"] == []

    def test_planning_complete_false_lists_artifacts(self, tmp_path, monkeypatch):
        """Core says planning is incomplete; pending artifacts are listed."""
        change_root = tmp_path / "openspec" / "changes" / "c2"
        change_root.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            osx,
            "_fetch_planning_status",
            lambda change_id, *, store=None: {
                "isPlanningComplete": False,
                "artifacts": [
                    {"id": "tasks", "status": "ready"},
                    {"id": "design", "status": "done"},
                ],
            },
        )

        result = osx.validate_change_dir("c2")

        assert result["valid"] is False
        assert result["planning_complete"] is False
        assert "tasks" in result["missing_artifacts"]
        assert "design" not in result["missing_artifacts"]
        assert any(
            e["check"] == "change-dir" and "tasks" in e["message"]
            for e in result["errors"]
        )
        assert not any(
            e["check"] == "change-dir" and "design" in e["message"]
            for e in result["errors"]
        )

    def test_cli_unavailable_falls_back_to_local(self, tmp_path, monkeypatch, capsys):
        """When the CLI helper returns ``None``, the local fallback runs."""
        change_root = tmp_path / "openspec" / "changes" / "c3"
        self._write_minimal_change(change_root)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            osx, "_fetch_planning_status", lambda change_id, *, store=None: None
        )

        result = osx.validate_change_dir("c3")

        assert result["valid"] is True
        assert result["planning_complete"] is None
        # Fallback warning is emitted exactly once on stderr.
        captured = capsys.readouterr()
        assert "falling back to local check" in captured.err

    def test_planning_complete_true_but_tasks_missing(
        self, tmp_path, monkeypatch
    ):
        """Core says complete but ``tasks.md`` is empty/absent — fail."""
        change_root = tmp_path / "openspec" / "changes" / "c4"
        change_root.mkdir(parents=True, exist_ok=True)
        (change_root / "proposal.md").write_text("# p")
        (change_root / "design.md").write_text("# d")
        # Deliberately do NOT create tasks.md.
        specs = change_root / "specs"
        specs.mkdir()
        (specs / "auth.md").write_text("# auth")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(
            osx,
            "_fetch_planning_status",
            lambda change_id, *, store=None: {
                "isPlanningComplete": True,
                "artifacts": [],
            },
        )

        result = osx.validate_change_dir("c4")

        assert result["valid"] is False
        assert result["planning_complete"] is True
        assert "tasks.md" in result["missing_artifacts"]
        assert any(
            "tasks.md" in e["message"] for e in result["errors"]
        )

    def test_env_escape_hatch_skips_core(self, tmp_path, monkeypatch):
        """``OPENSPEC_EXTENDED_NO_PLANNING_CORE=1`` forces the local path."""
        change_root = tmp_path / "openspec" / "changes" / "c5"
        self._write_minimal_change(change_root)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OPENSPEC_EXTENDED_NO_PLANNING_CORE", "1")

        calls = {"n": 0}

        def _spy(change_id, *, store=None):
            calls["n"] += 1
            return {"isPlanningComplete": True, "artifacts": []}

        monkeypatch.setattr(osx, "_fetch_planning_status", _spy)

        result = osx.validate_change_dir("c5")

        # Helper is never reached when the env var is set.
        assert calls["n"] == 0
        assert result["valid"] is True
        assert result["planning_complete"] is None
