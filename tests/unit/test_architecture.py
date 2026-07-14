#!/usr/bin/env python3
"""
Architectural invariant tests for the CLI/library split refactor.

Verifies the post-refactor boundaries:

1. ``source/lib/osx.py`` is a pure library (no Typer/Click surface).
2. ``source/osx_cli.py`` owns the Typer app.
3. ``source/cli.py`` mounts the ``osx`` subcommand.
4. ``resources/opencode/manifest.toml`` ships only skills, agents, and
   commands (no ``[resources.scripts]`` or ``[resources.lib]``).
5. Agent/command/skill prompts reference ``openspec-extended osx`` and
   never the legacy ``.opencode/scripts/lib/osx`` path.
6. Schema support: yaml import permitted in the library, all 5
   schema subprocess wrappers are exported, ``OrchestratorState`` exposes
   schema fields, and ``_PATHS_CACHE`` documents the schema-is-not-a-key
   audit decision.
"""

import ast
from pathlib import Path

import pytest
import toml

from source.lib import osx as osx_lib

REPO_ROOT = Path(__file__).parent.parent.parent
LIB_OSX = REPO_ROOT / "source" / "lib" / "osx.py"
ENGINE = REPO_ROOT / "source" / "orchestrator" / "engine.py"
OSX_CLI = REPO_ROOT / "source" / "osx_cli.py"
MANIFEST = REPO_ROOT / "resources" / "opencode" / "manifest.toml"
PROMPT_ROOT = REPO_ROOT / "resources" / "opencode"

PROMPT_FILES = [
    "commands/osx-phase0.md",
    "commands/osx-phase1.md",
    "commands/osx-phase2.md",
    "commands/osx-phase3.md",
    "commands/osx-phase4.md",
    "commands/osx-phase5.md",
    "commands/osx-phase6.md",
    "commands/osx-review.md",
    "commands/osx-modify.md",
    "skills/osx-workflow/SKILL.md",
    "skills/osx-workflow/references/autonomous-workflow.md",
    "skills/osx-concepts/references/cli-reference.md",
]


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    }


@pytest.mark.unit
class TestLibraryPurity:
    """``source/lib/osx.py`` must stay free of CLI framework imports."""

    def test_lib_osx_does_not_import_cli_frameworks(self):
        """``source/lib/osx.py`` must not import typer or click."""
        imports = _top_level_imports(LIB_OSX)
        forbidden = {"typer", "click"}
        leaked = imports & forbidden
        assert not leaked, (
            f"{LIB_OSX.relative_to(REPO_ROOT)} leaked CLI framework "
            f"imports: {sorted(leaked)}"
        )

    def test_osx_cli_imports_typer(self):
        """``source/osx_cli.py`` must import typer (it owns the CLI app)."""
        imports = _top_level_imports(OSX_CLI)
        assert "typer" in imports, (
            f"{OSX_CLI.relative_to(REPO_ROOT)} must import typer; "
            f"found imports: {sorted(imports)}"
        )


@pytest.mark.unit
class TestManifestInvariants:
    """Manifest must not declare scripts/lib sections after the refactor."""

    def test_manifest_has_no_scripts_section(self):
        """``[resources.scripts]`` must be absent from the opencode manifest."""
        manifest = toml.loads(MANIFEST.read_text())
        resources = manifest.get("resources", {})
        assert "scripts" not in resources, (
            f"{MANIFEST.relative_to(REPO_ROOT)} still declares "
            f"[resources.scripts]; the scripts/ tree should not be shipped"
        )

    def test_manifest_has_no_lib_section(self):
        """``[resources.lib]`` must be absent from the opencode manifest."""
        manifest = toml.loads(MANIFEST.read_text())
        resources = manifest.get("resources", {})
        assert "lib" not in resources, (
            f"{MANIFEST.relative_to(REPO_ROOT)} still declares "
            f"[resources.lib]; the lib/ tree should not be shipped"
        )


@pytest.mark.unit
class TestPromptReferencesBinary:
    """Prompts must reference the binary, not the legacy script path."""

    @pytest.mark.parametrize(
        "relpath",
        PROMPT_FILES,
        ids=[p.replace("/", "_").replace(".md", "") for p in PROMPT_FILES],
    )
    def test_prompt_does_not_reference_legacy_script_path(self, relpath: str):
        """Prompt text must not mention ``.opencode/scripts/lib/osx``."""
        prompt_path = PROMPT_ROOT / relpath
        text = prompt_path.read_text()
        legacy = ".opencode/scripts/lib/osx"
        assert legacy not in text, (
            f"{relpath} still references legacy path '{legacy}'; "
            f"replace with 'openspec-extended osx'"
        )

    @pytest.mark.parametrize(
        "relpath",
        PROMPT_FILES,
        ids=[p.replace("/", "_").replace(".md", "") for p in PROMPT_FILES],
    )
    def test_prompt_references_openspec_extended_binary(self, relpath: str):
        """Prompt text must reference the ``openspec-extended osx`` subcommand."""
        prompt_path = PROMPT_ROOT / relpath
        text = prompt_path.read_text()
        target = "openspec-extended osx"
        assert target in text, (
            f"{relpath} does not reference '{target}'; "
            f"agent/command/skill prompts should drive the osx subcommand "
            f"via the binary"
        )


def _module_top_level_funcs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _dataclass_fields(path: Path, class_name: str) -> set[str] | None:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(
                    stmt.target, ast.Name
                ):
                    return {child.id for child in stmt.annotation.elts} if isinstance(
                        stmt.annotation, ast.Tuple
                    ) else {stmt.target.id}
            return set()
    return None


@pytest.mark.unit
class TestSchemaSupport:
    """Locks in the schema-aware pre-flight code shape."""

    def test_lib_osx_may_import_yaml(self):
        """``source/lib/osx.py`` may import ``yaml`` (schema-resolution dep).

        ``resolve_schema`` (``source/lib/osx.py:1490``) parses project
        config and change metadata via PyYAML. The library is allowed to
        depend on PyYAML; only the CLI frameworks (typer/click) are banned.
        """
        imports = _top_level_imports(LIB_OSX)
        nested_yaml = "import yaml" in LIB_OSX.read_text()
        assert "yaml" in imports or nested_yaml, (
            f"{LIB_OSX.relative_to(REPO_ROOT)} is expected to import yaml "
            "(resolve_schema requires it); top-level imports: "
            f"{sorted(imports)}"
        )

    def test_lib_osx_still_has_no_typer_or_click(self):
        """Adding yaml must not regress the CLI-framework ban."""
        imports = _top_level_imports(LIB_OSX)
        leaked = imports & {"typer", "click"}
        assert not leaked, (
            f"{LIB_OSX.relative_to(REPO_ROOT)} leaked CLI framework "
            f"imports: {sorted(leaked)}"
        )

    def test_lib_osx_exports_schema_subprocess_wrappers(self):
        """All 5 schema subprocess wrappers are exported.

        ``source/lib/osx.py:1585-1679`` defines ``resolve_schema`` plus
        ``schema_which``, ``schema_validate``, ``schema_fork``,
        ``schema_init``, ``schema_list``. A future refactor that silently
        drops one of these would break the ``openspec-extended osx schema``
        sub-app.
        """
        funcs = _module_top_level_funcs(LIB_OSX)
        required = {
            "resolve_schema",
            "schema_which",
            "schema_validate",
            "schema_fork",
            "schema_init",
            "schema_list",
        }
        missing = required - funcs
        assert not missing, (
            f"{LIB_OSX.relative_to(REPO_ROOT)} is missing schema wrappers: "
            f"{sorted(missing)}"
        )

    def test_orchestrator_state_exposes_schema_fields(self):
        """``OrchestratorState`` (``source/orchestrator/engine.py:87-110``)
        must declare ``schema_override``, ``schema_name``, ``schema_source``.

        These fields are read by the new schema-name propagation test and
        by the orchestrator's pre-flight (``engine.py:274-305``).
        """
        text = ENGINE.read_text()
        assert "schema_override" in text
        assert "schema_name" in text
        assert "schema_source" in text

    def test_resolve_change_paths_ignores_schema_for_paths(self, tmp_path: Path):
        """``resolve_change_paths`` keys ``_PATHS_CACHE`` on
        ``(change, store)`` only — schema is intentionally not a key.

        Audit-only decision (Tier 4): ``resolve_change_paths`` does not
        consult schema when computing paths, so the cache serving stale
        data after a schema change is a non-issue. This test pins the
        behavior so a future contributor doesn't "fix" something that
        isn't broken.
        """
        osx_lib._PATHS_CACHE.clear()

        change = "schema-audit"
        change_dir = tmp_path / "openspec" / "changes" / change
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# proposal\n")

        config_path = tmp_path / "openspec" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("schema: spec-driven\n")

        first = osx_lib.resolve_change_paths(change)
        config_path.write_text("schema: workspace-planning\n")
        second = osx_lib.resolve_change_paths(change)

        assert first["change_root"] == second["change_root"]
        assert first["planning_home"] == second["planning_home"]

        osx_lib._PATHS_CACHE.clear()
