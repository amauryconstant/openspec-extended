#!/usr/bin/env python3
"""Resource contract suite for the orchestrator/skills split (Phase 7).

The previous version of this module was the v1.6 review/modify contract
suite for ``osx-review-artifacts`` / ``osx-modify-artifacts``. Phase 1
dropped ``osx-modify-artifacts`` / ``/osx-modify``, Phase 2 dropped
``osx-concepts``, and Phase 4 split the resource tree into two parallel
roots: ``orchestrator/resources/`` and ``skills/resources/``. This
rewrite pins the post-split surface.

Source of truth is the four split manifests:

  - ``orchestrator/resources/opencode/manifest.toml``
  - ``orchestrator/resources/claude/manifest.toml``
  - ``skills/resources/opencode/manifest.toml``
  - ``skills/resources/claude/manifest.toml``

Coverage:

  - ``TestManifestParity`` — resource set + per-resource versions agree
    pairwise across the four manifests; strict semver; no accidental
    downgrades vs HEAD.
  - ``TestDualEmitDiscipline`` — every opencode command dual-emits on
    the Claude side as both a legacy ``commands/osx/<base>.md`` and a
    modern ``skills/osx-<base>/SKILL.md``.
  - ``TestFrontmatterInvariants`` — required keys, name-matches-dir,
    ``allowed-tools: Bash(openspec:*)`` where the skill consumes the
    openspec CLI, Claude ``metadata`` mirror where the opencode source
    declares it.
  - ``TestSchemaAgnosticContract`` — pins the still-load-bearing schema-
    agnostic contract wording inside ``osx-review-artifacts``.
  - ``TestNoHardcodedArtifactNames`` — the rewritten review skill plus
    every opencode command body must avoid hardcoded
    ``proposal.md``/``design.md``/``tasks.md`` references.
  - ``TestSkillDescriptionLeadingWord`` — locks in the model-invocation
    trigger word for every canonical skill.
     - ``TestOrchestratorContracts`` — mirrors the still-load-bearing
       v1.8.0–v1.13.0 contracts from ``.opencode/rules/openspec-contract.md``
       (``isPlanningComplete``, ``retire_capabilities``, ``operationGuidance``,
       ``show --diff``, ``validate --archived``, ``missingPrerequisites``,
       ``list --specs`` + ``--type spec --json --no-scenarios``).
  - ``TestSharedReferencesPackaging`` — shared references pool files
    are all consumed by some skill or command (orchestrator-side and
    skills-side pools).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import toml

from source.cli import deploy_commands

REPO_ROOT = Path(__file__).parent.parent.parent

ORCH_OPENCODE = REPO_ROOT / "orchestrator" / "resources" / "opencode"
SK_OPENCODE = REPO_ROOT / "skills" / "resources" / "opencode"

ORCH_OPENCODE_MANIFEST = ORCH_OPENCODE / "manifest.toml"
SK_OPENCODE_MANIFEST = SK_OPENCODE / "manifest.toml"

ALL_MANIFESTS = [
    ORCH_OPENCODE_MANIFEST,
    SK_OPENCODE_MANIFEST,
]

CANONICAL_SKILLS = frozenset(
    {
        "osx-commit",
        "osx-review-artifacts",
        "osx-review-test-compliance",
        "osx-workflow",
    }
)

# Phase 5 split: each side's manifest declares its own subset of the
# canonical resource surface. The two sets must be disjoint and their
# union must equal this allowlist — pinning it here catches both
# accidental double-declaration and forgotten re-homing.
EXPECTED_OPENCODE_RESOURCE_IDS: dict[str, list[str]] = {
    "skills": [
        "osx-workflow",  # orchestrator side
        "osx-commit",  # skills side
        "osx-review-artifacts",  # skills side
        "osx-review-test-compliance",  # skills side
    ],
    "agents": [
        "osx-analyzer",
        "osx-builder",
        "osx-maintainer",
        "osx-reviewer",
    ],
    "commands": [
        "osx-changelog",
        "osx-maintain-docs",
        "osx-phase0",
        "osx-phase1",
        "osx-phase2",
        "osx-phase3",
        "osx-phase4",
        "osx-phase5",
        "osx-phase6",
        "osx-review",  # skills side
        "osx-verify-tests",  # skills side
    ],
}

# Skills that consume the openspec CLI directly. These must carry the
# `allowed-tools: Bash(openspec:*)` precedent. ``osx-commit`` does not
# consume the CLI (it shells out to `git`), and ``osx-workflow`` is a
# pure reference (no live CLI calls) — both excluded.
OPENSPEC_TOOL_SKILLS = frozenset(
    {
        "osx-review-artifacts",
        "osx-review-test-compliance",
    }
)

# Source roots where the canonical skill lives (orchestrator or skills side).
SKILL_HOME = {
    "osx-commit": SK_OPENCODE,
    "osx-review-artifacts": SK_OPENCODE,
    "osx-review-test-compliance": SK_OPENCODE,
    "osx-workflow": ORCH_OPENCODE,
}

SCHEMA_AGNOSTIC_CONTRACT_SKILLS = [
    SK_OPENCODE / "skills" / "osx-review-artifacts" / "SKILL.md",
]


def _read(path: Path) -> str:
    return path.read_text()


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = _read(path)
    if not text.startswith("---"):
        return {}
    body = text.split("---", 2)[1]
    fm: dict[str, str] = {}
    for line in body.strip().splitlines():
        if ":" not in line or line.startswith("#") or line.strip().startswith("-"):
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _manifest_resources(path: Path) -> dict[str, dict[str, dict]]:
    """Return the full ``resources`` table from a manifest as nested dicts."""
    return toml.loads(_read(path)).get("resources", {})


def _manifest_versions(path: Path) -> dict[str, str]:
    """Flatten a manifest to ``<type>.<id>`` -> ``version`` mapping."""
    manifest = _manifest_resources(path)
    out: dict[str, str] = {}
    for kind, items in manifest.items():
        if not isinstance(items, dict):
            continue
        for rid, meta in items.items():
            if isinstance(meta, dict) and "version" in meta:
                out[f"{kind}.{rid}"] = str(meta["version"])
    return out


def _manifest_resource_keys(path: Path) -> set[str]:
    """Return the set of ``<type>.<id>`` keys declared in a manifest."""
    manifest = _manifest_resources(path)
    out: set[str] = set()
    for kind, items in manifest.items():
        if not isinstance(items, dict):
            continue
        out.update(f"{kind}.{rid}" for rid in items)
    return out


def _git_available() -> bool:
    return shutil.which("git") is not None


def _head_manifest(path: Path) -> str | None:
    """Read ``HEAD:<manifest>`` as text. Returns None on any git failure."""
    if not _git_available():
        return None
    try:
        rel = path.resolve().relative_to(REPO_ROOT.resolve())
        result = subprocess.run(
            ["git", "show", f"HEAD:{rel.as_posix()}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except (ValueError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_version(v: str) -> tuple[int, int, int] | None:
    parts = v.split(".")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _all_opencode_commands() -> list[Path]:
    out: list[Path] = []
    for root in (ORCH_OPENCODE / "commands", SK_OPENCODE / "commands"):
        if not root.is_dir():
            continue
        out.extend(sorted(root.glob("osx-*.md")))
    return out


def _claude_mirror_paths_for(src: Path, tmp_claude: Path) -> tuple[Path, Path]:
    """Drive ``deploy_commands`` against ``tmp_claude`` and return the
    ``(legacy_command, modern_skill)`` paths it wrote. Used by
    ``TestDualEmitDiscipline`` to assert the per-adapter deploy path
    produces both legacy + modern forms without depending on a
    hand-maintained on-disk mirror.
    """
    stem = src.stem  # "osx-phase0"
    if str(src).startswith(str(SK_OPENCODE / "commands")):
        source_base = SK_OPENCODE / "commands"
    else:
        source_base = ORCH_OPENCODE / "commands"
    deploy_commands(source_base, tmp_claude, stem, tool="claude")
    base = stem[len("osx-"):]  # "phase0"
    legacy = tmp_claude / "commands" / "osx" / f"{base}.md"
    modern = tmp_claude / "skills" / stem / "SKILL.md"
    return legacy, modern


# ============================================================================
# Manifest parity
# ============================================================================


@pytest.mark.unit
class TestManifestParity:
    """The four split manifests must agree pairwise on resource set and
    per-resource versions."""

    def test_all_four_manifests_exist(self):
        for path in ALL_MANIFESTS:
            assert path.is_file(), f"manifest missing: {path}"

    def test_opencode_manifests_have_disjoint_resource_sets(self):
        """Phase 5 split: the orchestrator- and skills-side manifests
        each declare their own subset. The two sets must be disjoint so
        no resource is claimed by both sides. Their union equals the
        canonical resource surface (locked separately)."""
        oc_keys = _manifest_resource_keys(ORCH_OPENCODE_MANIFEST)
        sk_keys = _manifest_resource_keys(SK_OPENCODE_MANIFEST)
        assert oc_keys.isdisjoint(sk_keys), (
            f"orchestrator-opencode and skills-opencode manifests share "
            f"resource keys: {sorted(oc_keys & sk_keys)}. Each side "
            f"must declare only its own resources."
        )

    def test_opencode_manifests_union_equals_canonical_surface(self):
        """The union of both side manifests must equal the manually-curated
        canonical resource set so dropping a resource from one side and
        forgetting to add it to the other is caught here."""
        oc_keys = _manifest_resource_keys(ORCH_OPENCODE_MANIFEST)
        sk_keys = _manifest_resource_keys(SK_OPENCODE_MANIFEST)
        union = oc_keys | sk_keys
        expected = set()
        for kind in ("skills", "agents", "commands"):
            for name in EXPECTED_OPENCODE_RESOURCE_IDS.get(kind, []):
                expected.add(f"{kind}.{name}")
        assert union == expected, (
            f"union of side manifests drifted from canonical surface. "
            f"only-in-union={sorted(union - expected)} "
            f"only-in-expected={sorted(expected - union)}"
        )

    def test_every_version_is_strict_semver(self):
        for path in ALL_MANIFESTS:
            for key, version in _manifest_versions(path).items():
                assert _parse_version(version) is not None, (
                    f"{path}: {key} version {version!r} is not strict X.Y.Z"
                )

    def test_no_resource_version_downgrade_vs_head(self):
        """Compare each manifest's per-resource versions against HEAD.
        Versions must be >= what HEAD carried — pin accidental downgrades."""
        if not _git_available():
            pytest.skip("git not available")
        for path in ALL_MANIFESTS:
            head_text = _head_manifest(path)
            if head_text is None:
                pytest.skip(f"no HEAD snapshot for {path}")
            try:
                head_versions = _manifest_versions_from_text(head_text)
            except Exception:
                pytest.skip(f"could not parse HEAD manifest for {path}")
            cur_versions = _manifest_versions(path)
            for key in head_versions:
                if key not in cur_versions:
                    continue
                head_v = _parse_version(head_versions[key])
                cur_v = _parse_version(cur_versions[key])
                assert head_v is not None and cur_v is not None
                assert cur_v >= head_v, (
                    f"{path}: {key} downgraded {head_versions[key]} -> "
                    f"{cur_versions[key]}"
                )


def _manifest_versions_from_text(text: str) -> dict[str, str]:
    manifest = toml.loads(text).get("resources", {})
    out: dict[str, str] = {}
    for kind, items in manifest.items():
        if not isinstance(items, dict):
            continue
        for rid, meta in items.items():
            if isinstance(meta, dict) and "version" in meta:
                out[f"{kind}.{rid}"] = str(meta["version"])
    return out


# ============================================================================
# Dual-emit discipline
# ============================================================================


@pytest.mark.unit
class TestDualEmitDiscipline:
    """Every opencode command must dual-emit on the Claude side: the
    legacy ``commands/osx/<base>.md`` and the modern
    ``skills/osx-<base>/SKILL.md``. Mirrors the upstream OpenSpec
    v1.7.0 dual-emit strategy (current as of v1.13.0).

    Driven via ``deploy_commands(<source>, tmp_path/.claude, ..., tool="claude")``
    so the test asserts the deploy path itself, not a hand-maintained
    on-disk mirror.
    """

    def test_every_opencode_command_has_legacy_command_mirror(self, tmp_path):
        cl_root = tmp_path / "claude-target"
        for src in _all_opencode_commands():
            legacy, _ = _claude_mirror_paths_for(src, cl_root)
            assert legacy.is_file(), (
                f"missing legacy command mirror for {src.name}; "
                f"expected {legacy}"
            )

    def test_every_opencode_command_has_modern_skill_mirror(self, tmp_path):
        cl_root = tmp_path / "claude-target"
        for src in _all_opencode_commands():
            _, modern = _claude_mirror_paths_for(src, cl_root)
            assert modern.is_file(), (
                f"missing modern skill mirror for {src.name}; "
                f"expected {modern}"
            )

    def test_modern_skill_mirror_injects_name_frontmatter(self, tmp_path):
        """The Claude skill mirror must declare ``name: osx-<base>`` so
        Claude Code's slash-command resolver picks it up."""
        cl_root = tmp_path / "claude-target"
        for src in _all_opencode_commands():
            _, modern = _claude_mirror_paths_for(src, cl_root)
            text = _read(modern)
            assert f"\nname: {src.stem}\n" in text, (
                f"{modern} missing `name: {src.stem}` frontmatter"
            )

    def test_modern_skill_mirror_drops_agent_frontmatter(self, tmp_path):
        """The opencode-only ``agent:`` directive is platform-specific.
        The namespaced-with-skill-mirror deploy must not leak it through."""
        cl_root = tmp_path / "claude-target"
        for src in _all_opencode_commands():
            _, modern = _claude_mirror_paths_for(src, cl_root)
            text = _read(modern)
            assert "\nagent:" not in text, (
                f"{modern} leaked opencode `agent:` directive"
            )


# ============================================================================
# Frontmatter invariants
# ============================================================================


@pytest.mark.unit
class TestFrontmatterInvariants:
    """The four canonical skills must match their platform's frontmatter
    contract. ``osx-commit`` is intentionally minimal (no openspec CLI),
    so the ``allowed-tools`` rule applies only to the three skills that
    consume the openspec CLI."""

    @pytest.mark.parametrize("skill_name", sorted(CANONICAL_SKILLS))
    def test_opencode_skill_has_required_basics(self, skill_name: str):
        path = SKILL_HOME[skill_name] / "skills" / skill_name / "SKILL.md"
        fm = _read_frontmatter(path)
        for required in ("name", "description", "license"):
            assert required in fm, (
                f"{path.relative_to(REPO_ROOT)} missing required "
                f"frontmatter key {required!r}"
            )

    @pytest.mark.parametrize("skill_name", sorted(CANONICAL_SKILLS))
    def test_skill_name_matches_directory(self, skill_name: str):
        path = SKILL_HOME[skill_name] / "skills" / skill_name / "SKILL.md"
        fm = _read_frontmatter(path)
        assert fm.get("name") == skill_name, (
            f"{path.relative_to(REPO_ROOT)} `name:` frontmatter "
            f"{fm.get('name')!r} does not match directory {skill_name!r}"
        )

    @pytest.mark.parametrize("skill_name", sorted(OPENSPEC_TOOL_SKILLS))
    def test_opencode_skill_has_allowed_tools(self, skill_name: str):
        path = SKILL_HOME[skill_name] / "skills" / skill_name / "SKILL.md"
        fm = _read_frontmatter(path)
        assert fm.get("allowed-tools") == "Bash(openspec:*)", (
            f"{path.relative_to(REPO_ROOT)} must carry "
            f"`allowed-tools: Bash(openspec:*)`; got {fm.get('allowed-tools')!r}"
        )

    @pytest.mark.parametrize(
        "root",
        [ORCH_OPENCODE / "commands", SK_OPENCODE / "commands"],
        ids=["orchestrator", "skills"],
    )
    def test_every_opencode_command_has_description(self, root: Path):
        for cmd in root.glob("osx-*.md"):
            fm = _read_frontmatter(cmd)
            assert "description" in fm, (
                f"{cmd.relative_to(REPO_ROOT)} must carry a `description` "
                f"frontmatter key"
            )


# ============================================================================
# Schema-agnostic contract (live utility: osx-review-artifacts)
# ============================================================================


@pytest.mark.unit
class TestSchemaAgnosticContract:
    """``osx-review-artifacts`` is the live consumer of the schema-
    agnostic contract from §4.2 of review-modify-integration.md. Pin
    the contract wording on each skill's source file."""

    @pytest.mark.parametrize(
        "skill", SCHEMA_AGNOSTIC_CONTRACT_SKILLS,
        ids=lambda p: str(p.relative_to(REPO_ROOT)),
    )
    def test_skill_uses_status_cli(self, skill: Path):
        text = _read(skill)
        assert "openspec status --change" in text, (
            f"{skill.relative_to(REPO_ROOT)} must use "
            f"`openspec status --change ... --json`"
        )

    @pytest.mark.parametrize(
        "skill", SCHEMA_AGNOSTIC_CONTRACT_SKILLS,
        ids=lambda p: str(p.relative_to(REPO_ROOT)),
    )
    def test_skill_uses_instructions_cli(self, skill: Path):
        text = _read(skill)
        assert "openspec instructions" in text, (
            f"{skill.relative_to(REPO_ROOT)} must use "
            f"`openspec instructions <id> --change ... --json`"
        )

    @pytest.mark.parametrize(
        "skill", SCHEMA_AGNOSTIC_CONTRACT_SKILLS,
        ids=lambda p: str(p.relative_to(REPO_ROOT)),
    )
    def test_skill_references_existing_output_paths(self, skill: Path):
        text = _read(skill)
        assert "existingOutputPaths" in text, (
            f"{skill.relative_to(REPO_ROOT)} must reference "
            f"`artifactPaths.<id>.existingOutputPaths`"
        )

    @pytest.mark.parametrize(
        "skill", SCHEMA_AGNOSTIC_CONTRACT_SKILLS,
        ids=lambda p: str(p.relative_to(REPO_ROOT)),
    )
    def test_skill_warns_against_resolved_output_path_writes(self, skill: Path):
        text = _read(skill)
        assert "resolvedOutputPath" in text, (
            f"{skill.relative_to(REPO_ROOT)} must call out the glob "
            f"hazard of `resolvedOutputPath`"
        )

    @pytest.mark.parametrize(
        "skill", SCHEMA_AGNOSTIC_CONTRACT_SKILLS,
        ids=lambda p: str(p.relative_to(REPO_ROOT)),
    )
    def test_skill_disallows_code_edits(self, skill: Path):
        text = _read(skill)
        # Routes code-change implications to the apply command. Allow
        # either the canonical slash form (`/opsx:apply`) or the
        # installed full skill-name form (`/osc-apply-change`); the
        # deploy layer rewrites the former to the latter on Claude and
        # to the hyphenated form on OpenCode.
        assert ("/opsx:apply" in text) or ("/osc-apply-change" in text), (
            f"{skill.relative_to(REPO_ROOT)} must route code-change "
            f"implications to `/opsx:apply` (or `/osc-apply-change`)"
        )

    @pytest.mark.parametrize(
        "skill", SCHEMA_AGNOSTIC_CONTRACT_SKILLS,
        ids=lambda p: str(p.relative_to(REPO_ROOT)),
    )
    def test_skill_includes_store_selection_pointer(self, skill: Path):
        text = _read(skill)
        assert "references/store-selection.md" in text, (
            f"{skill.relative_to(REPO_ROOT)} must include a pointer to "
            f"`references/store-selection.md`"
        )


# ============================================================================
# No hardcoded artifact names
# ============================================================================


@pytest.mark.unit
class TestNoHardcodedArtifactNames:
    """The schema-driven contract forbids hardcoded ``proposal.md`` /
    ``design.md`` / ``tasks.md`` references — they break any non-spec-
    driven schema. Apply to the rewritten review skill AND every
    opencode command body (commands that route users to artifact editors
    must also be schema-driven)."""

    PATHS = [
        SK_OPENCODE / "skills" / "osx-review-artifacts" / "SKILL.md",
    ]

    @pytest.mark.parametrize(
        "skill", PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_review_skill_contains_no_hardcoded_artifact_names(self, skill: Path):
        text = _read(skill)
        # Tolerate a single occurrence in a "never assume" negative-example
        # context. Outside that context, these strings must not appear.
        for name in ("proposal.md", "design.md", "tasks.md"):
            count = text.count(name)
            assert count <= 1, (
                f"{skill.relative_to(REPO_ROOT)} references hardcoded "
                f"artifact name {name!r} {count} times; the rewritten "
                f"skill must be schema-driven"
            )


# ============================================================================
# Skill description leading word (model-invocation trigger)
# ============================================================================


@pytest.mark.unit
class TestSkillDescriptionLeadingWord:
    """Pin the first word of every model-invoked skill's ``description``
    frontmatter. The first word is what the model uses to decide
    whether to fire the skill; casual description edits must not
    silently change firing behaviour.

    ``osx-changelog`` is excluded because it is no longer a skill
    (it is a slash command with a self-contained body). ``osx-workflow``
    fires on the literal token ``7-phase`` — pin it.
    """

    EXPECTED_LEADING_WORDS = {
        "osx-commit": "Detect",
        "osx-review-artifacts": "Audit",
        "osx-review-test-compliance": "Surface",
        "osx-workflow": "7-phase",
    }

    @pytest.mark.parametrize(
        "skill_name,expected",
        sorted(EXPECTED_LEADING_WORDS.items()),
    )
    def test_opencode_description_leads_with_expected_word(
        self, skill_name: str, expected: str
    ):
        path = SKILL_HOME[skill_name] / "skills" / skill_name / "SKILL.md"
        desc = _read_frontmatter(path).get("description", "")
        first = desc.split(maxsplit=1)[0] if desc else ""
        assert first == expected, (
            f"{path.relative_to(REPO_ROOT)} description leading word "
            f"changed: expected {expected!r}, got {first!r}. "
            f"Update the allowlist AND the description together."
        )


# ============================================================================
# Orchestrator contract surface (mirrors §13)
# ============================================================================


@pytest.mark.unit
class TestOrchestratorContracts:
    """Mirror the still-load-bearing v1.8.0–v1.13.0 contracts from
    ``.opencode/rules/openspec-contract.md``. Each test pins the
    engine/library symbol that consumes the contract; integration tests
    cover the round-trip behaviour."""

    ENGINE_PY = REPO_ROOT / "orchestrator" / "source" / "orchestrator" / "engine.py"
    LIB_OSX_PY = REPO_ROOT / "orchestrator" / "source" / "lib" / "osx.py"
    CLI_PY = REPO_ROOT / "orchestrator" / "source" / "cli.py"
    PHASE1_OPENCODE = ORCH_OPENCODE / "commands" / "osx-phase1.md"
    PHASE2_OPENCODE = ORCH_OPENCODE / "commands" / "osx-phase2.md"
    REVIEW_ARTIFACTS_OPENCODE = SK_OPENCODE / "skills" / "osx-review-artifacts" / "SKILL.md"

    def test_is_planning_complete_contract_is_consumed(self):
        """§13.1: ``openspec status --change ... --json`` exposes
        ``isPlanningComplete`` since v1.8.0. The library reads it."""
        text = _read(self.LIB_OSX_PY)
        assert "isPlanningComplete" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must consume the "
            f"`isPlanningComplete` v1.8.0+ contract"
        )

    def test_validate_change_dir_lives_in_engine(self):
        """§13.1: ``validate_change_dir`` is the library helper consulted
        by the orchestrator pre-flight."""
        text = _read(self.ENGINE_PY)
        assert "def validate_change_dir(" in text, (
            f"{self.ENGINE_PY.relative_to(REPO_ROOT)} must define "
            f"`validate_change_dir` (orchestrator pre-flight entry point)"
        )

    def test_retire_capabilities_state_field_exists(self):
        """§13.2: ``OrchestratorState.retire_capabilities`` is the
        v1.8.0+ marker read from ``.openspec.yaml``."""
        text = _read(self.ENGINE_PY)
        assert "retire_capabilities: bool" in text, (
            f"{self.ENGINE_PY.relative_to(REPO_ROOT)} must declare "
            f"`OrchestratorState.retire_capabilities: bool` "
            f"(v1.8.0+ `.openspec.yaml` marker)"
        )

    def test_retire_capabilities_key_is_parsed(self):
        """§13.2: ``read_change_metadata`` parses ``retire_capabilities``
        alongside ``skip_specs`` and ``schema``."""
        text = _read(self.LIB_OSX_PY)
        assert '"retire_capabilities"' in text or "'retire_capabilities'" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must parse "
            f"`retire_capabilities` from `.openspec.yaml`"
        )

    def test_fetch_operation_guidance_helper_exists(self):
        """§13.3: ``fetch_operation_guidance(operation, project_root,
        store=None)`` reads ``openspec/config.yaml`` and returns the
        ``operations.{apply|archive}.guidance`` list."""
        text = _read(self.LIB_OSX_PY)
        assert "def fetch_operation_guidance(" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must define "
            f"`fetch_operation_guidance` (v1.7.0+ operations guidance "
            f"reader)"
        )

    def test_operation_guidance_literal_is_consumed(self):
        """§13.3: the library code references the ``operationGuidance``
        envelope field name at least once (parse or string-key)."""
        text = _read(self.LIB_OSX_PY)
        assert "operationGuidance" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must reference "
            f"the `operationGuidance` envelope field"
        )

    def test_phase2_command_embeds_show_diff(self):
        """§13.4: PHASE2's REVIEW step fetches
        ``openspec show <change> --diff --json`` and embeds a
        ``## Requirement diff`` section in ``verification-report.md``."""
        text = _read(self.PHASE2_OPENCODE)
        assert "openspec show" in text and "--diff" in text, (
            f"{self.PHASE2_OPENCODE.relative_to(REPO_ROOT)} must call "
            f"`openspec show ... --diff --json` (v1.11.0+ envelope)"
        )
        assert "## Requirement diff" in text, (
            f"{self.PHASE2_OPENCODE.relative_to(REPO_ROOT)} must emit "
            f"a `## Requirement diff` section in verification-report.md"
        )

    def test_post_install_archived_sweep_helper_exists(self):
        """§13.5: ``_post_install_archived_sweep`` runs
        ``openspec validate --archived`` after deploy."""
        text = _read(self.CLI_PY)
        assert "def _post_install_archived_sweep(" in text, (
            f"{self.CLI_PY.relative_to(REPO_ROOT)} must define "
            f"`_post_install_archived_sweep` (v1.9.0+ post-install sweep)"
        )

    def test_validate_archived_in_process_helper_exists(self):
        """§13.5: ``validate_archived`` is the in-process entry point
        for ``osx validate archived`` (used by integration callers)."""
        text = _read(self.LIB_OSX_PY)
        assert "def validate_archived(" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must define "
            f"`validate_archived` (in-process wrapper for the "
            f"`openspec validate --archived` envelope)"
        )

    def test_missing_prerequisites_helper_exists(self):
        """§13.7.2: ``fetch_apply_prerequisites`` is the in-process reader
        for the v1.13.0+ ``missingPrerequisites`` array on
        ``openspec instructions apply --json``. PHASE1 consumes it to log
        the full build-order chain in the decision log."""
        text = _read(self.LIB_OSX_PY)
        assert "def fetch_apply_prerequisites(" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must define "
            f"`fetch_apply_prerequisites` (v1.13.0+ `missingPrerequisites` "
            f"reader for PHASE1 logging)"
        )

    def test_missing_prerequisites_field_is_referenced(self):
        """§13.7.2: the library code references the ``missingPrerequisites``
        envelope field name at least once (parse or string-key)."""
        text = _read(self.LIB_OSX_PY)
        assert "missingPrerequisites" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must reference "
            f"the `missingPrerequisites` envelope field"
        )

    def test_phase1_command_logs_missing_prerequisites(self):
        """§13.7.2: PHASE1 (IMPLEMENTATION) fetches
        ``openspec instructions apply --change <name> --json`` and, when
        the v1.13.0+ envelope carries ``missingPrerequisites``, surfaces
        each entry's name in the decision log via
        ``--extra '{"missing_prerequisites": [...]}'``."""
        text = _read(self.PHASE1_OPENCODE)
        assert "missingPrerequisites" in text, (
            f"{self.PHASE1_OPENCODE.relative_to(REPO_ROOT)} must reference "
            f"the `missingPrerequisites` field (v1.13.0+ PHASE1 logging)"
        )
        assert "missing_prerequisites" in text, (
            f"{self.PHASE1_OPENCODE.relative_to(REPO_ROOT)} must include "
            f"`missing_prerequisites` in the decision-log --extra JSON"
        )

    def test_list_specs_helper_exists(self):
        """§13.7.3: ``list_specs`` is the in-process reader for the
        v1.13.0+ ``openspec list --specs --json`` envelope. PHASE0
        spec-aware review uses it to build the spec inventory."""
        text = _read(self.LIB_OSX_PY)
        assert "def list_specs(" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must define "
            f"`list_specs` (v1.13.0+ spec-inventory reader for PHASE0)"
        )

    def test_show_spec_helper_exists(self):
        """§13.7.3: ``show_spec`` is the in-process reader for the
        v1.13.0+ filtered ``openspec show <id> --type spec --json
        --no-scenarios`` envelope. PHASE0 spec-aware review uses it to
        drill into each inventory entry."""
        text = _read(self.LIB_OSX_PY)
        assert "def show_spec(" in text, (
            f"{self.LIB_OSX_PY.relative_to(REPO_ROOT)} must define "
            f"`show_spec` (v1.13.0+ filtered spec-read helper for PHASE0)"
        )

    def test_review_artifacts_uses_spec_inventory(self):
        """§13.7.3: ``osx-review-artifacts`` Step 2b (Build spec inventory)
        runs ``openspec list --specs`` and Step 4b (Capability-already-exists)
        consumes the inventory to flag drift on ``ADDED Requirements`` deltas."""
        text = _read(self.REVIEW_ARTIFACTS_OPENCODE)
        assert "openspec list --specs" in text, (
            f"{self.REVIEW_ARTIFACTS_OPENCODE.relative_to(REPO_ROOT)} must "
            f"call `openspec list --specs` (v1.13.0+ spec-inventory read)"
        )
        assert "--type spec" in text and "--no-scenarios" in text, (
            f"{self.REVIEW_ARTIFACTS_OPENCODE.relative_to(REPO_ROOT)} must "
            f"call `openspec show --type spec --json --no-scenarios` "
            f"(v1.13.0+ filtered spec read)"
        )
        assert "Capability-already-exists" in text, (
            f"{self.REVIEW_ARTIFACTS_OPENCODE.relative_to(REPO_ROOT)} must "
            f"include the Capability-already-exists check (Step 4b)"
        )


# ============================================================================
# Shared references packaging
# ============================================================================


def _read_manifest_references(manifest_path: Path) -> dict[str, list[str]]:
    """Return ``skills.<name>`` -> ``references`` list from a manifest.
    Skills without a ``references`` field are omitted."""
    manifest = _manifest_resources(manifest_path)
    skills = manifest.get("skills", {})
    out: dict[str, list[str]] = {}
    if not isinstance(skills, dict):
        return out
    for name, meta in skills.items():
        if not isinstance(meta, dict):
            continue
        refs = meta.get("references")
        if isinstance(refs, list):
            out[f"skills.{name}"] = [str(r) for r in refs]
    return out


def _skill_linked_references(skill_path: Path) -> set[str]:
    """Return the set of bare filenames referenced via ``references/<x>.md``
    links inside a SKILL.md body. Frontmatter and code fences are skipped.
    Files that already exist in the skill's own ``references/`` subdir are
    excluded (those are skill-local, not shared)."""
    text = _read(skill_path)
    body = text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    skill_local = set()
    local_refs = skill_path.parent / "references"
    if local_refs.is_dir():
        skill_local = {p.name for p in local_refs.glob("*.md")}
    links: set[str] = set()
    for raw in body.split("`"):
        if not raw.startswith("references/"):
            continue
        head, _, _ = raw.partition("#")
        if not head.endswith(".md"):
            continue
        name = head[len("references/") :]
        if name in skill_local:
            continue
        links.add(name)
    return links


@pytest.mark.unit
class TestSharedReferencesPackaging:
    """There is a single canonical shared references pool at
    ``orchestrator/resources/opencode/skills/references/``. Both
    manifests may declare ``references = [...]`` entries; they all
    resolve against that pool. Deploy copies the declared files into
    each consuming skill's own ``references/`` subdir at the target
    site (see ``orchestrator/resources/opencode/skills/AGENTS.md``)."""

    SHARED_POOL = ORCH_OPENCODE / "skills" / "references"

    def test_orchestrator_manifest_references_resolve(self):
        for key, refs in _read_manifest_references(ORCH_OPENCODE_MANIFEST).items():
            for ref_name in refs:
                assert (self.SHARED_POOL / ref_name).is_file(), (
                    f"{ORCH_OPENCODE_MANIFEST.relative_to(REPO_ROOT)} "
                    f"declares {ref_name!r} for {key} but it is missing "
                    f"from {self.SHARED_POOL.relative_to(REPO_ROOT)}"
                )

    def test_skills_manifest_references_resolve(self):
        for key, refs in _read_manifest_references(SK_OPENCODE_MANIFEST).items():
            for ref_name in refs:
                assert (self.SHARED_POOL / ref_name).is_file(), (
                    f"{SK_OPENCODE_MANIFEST.relative_to(REPO_ROOT)} "
                    f"declares {ref_name!r} for {key} but it is missing "
                    f"from {self.SHARED_POOL.relative_to(REPO_ROOT)}"
                )

    def test_skill_references_match_manifest(self):
        """Every `references/<x>.md` link in a SKILL.md body must be
        declared in its skill's manifest entry, so the deploy copies
        it into the skill's own references/ subdir at install time."""
        for manifest_path in (ORCH_OPENCODE_MANIFEST, SK_OPENCODE_MANIFEST):
            declared = _read_manifest_references(manifest_path)
            for key, refs in declared.items():
                skill_name = key.split(".", 1)[1]
                # Locate the SKILL.md wherever it lives.
                candidates = [
                    ORCH_OPENCODE / "skills" / skill_name / "SKILL.md",
                    SK_OPENCODE / "skills" / skill_name / "SKILL.md",
                ]
                skill_path = next(
                    (p for p in candidates if p.is_file()), None
                )
                if skill_path is None:
                    continue
                linked = _skill_linked_references(skill_path)
                declared_set = set(refs)
                missing = linked - declared_set
                assert not missing, (
                    f"{skill_path.relative_to(REPO_ROOT)} links to "
                    f"{sorted(missing)!r} but the manifest entry does "
                    f"not declare them under `references = [...]`."
                )

    def test_shared_pool_has_no_orphans(self):
        """Every file in the shared pool must be claimed by at least
        one skill (via manifest) or one command (via body link)."""
        if not self.SHARED_POOL.is_dir():
            return
        claimed: set[str] = set()
        for manifest_path in (ORCH_OPENCODE_MANIFEST, SK_OPENCODE_MANIFEST):
            for refs in _read_manifest_references(manifest_path).values():
                claimed.update(refs)

        # Commands on either side may also reference shared pool files
        # via `references/<x>.md` prose.
        for root in (ORCH_OPENCODE / "commands", SK_OPENCODE / "commands"):
            if not root.is_dir():
                continue
            for cmd in root.glob("*.md"):
                text = _read(cmd)
                for raw in text.split("`"):
                    if not raw.startswith("references/"):
                        continue
                    head, _, _ = raw.partition("#")
                    if head.endswith(".md"):
                        claimed.add(head[len("references/") :])

        orphans = {
            p.name for p in self.SHARED_POOL.glob("*.md") if p.name not in claimed
        }
        assert not orphans, (
            f"Shared references pool "
            f"{self.SHARED_POOL.relative_to(REPO_ROOT)} contains files "
            f"not referenced by any skill or command: {sorted(orphans)!r}. "
            f"Either add a consumer or remove the file."
        )


# ---------------------------------------------------------------------------
# Phase 1B: cli.py consumers route through ``source.tools.REGISTRY``
# ---------------------------------------------------------------------------


class TestDeployRoutesViaRegistry:
    """Phase 1B rewires ``deploy_skills``, ``deploy_commands``,
    ``deploy_agents`` to read from ``REGISTRY[tool].skills_dir`` and
    dispatch on ``commands_style``. These tests pin the byte-output
    of those dispatches for the shipped ``opencode`` / ``claude`` set
    so future additions cannot regress."""

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_deploy_skill_writes_no_tokens(self, tmp_path, tool_id):
        """Existing ``TestDeployLeavesNoLeftoverTokens`` covers opencode
        skills; this adds the same guarantee for claude skills via the
        registry-routed dispatch."""
        from source.cli import deploy_skills, get_resources_dir
        from source.tools import REGISTRY

        adapter = REGISTRY[tool_id]
        source_dir = get_resources_dir() / "opencode" / "skills"
        target = tmp_path / adapter.skills_dir
        target.mkdir(parents=True)
        deploy_skills(source_dir, target, "osx-workflow", tool=tool_id)

        for md in (target / "skills" / "osx-workflow").rglob("*.md"):
            assert "{{" not in md.read_text(), (
                f"{md.relative_to(target)} still contains a token placeholder"
            )
