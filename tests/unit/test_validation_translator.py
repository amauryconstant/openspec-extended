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
