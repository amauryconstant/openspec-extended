#!/usr/bin/env python3
"""Phase 1G regression guard: check-platform-hardcodes.sh must pass on
the current tree and detect injected hardcodes.

The script scans orchestrator/source/cli.py, orchestrator/source/orchestrator/,
and orchestrator/source/lib/ for hardcoded "opencode"/"claude" literals
in conditionals or direct dict access. Adding a new tool to
source.tools.REGISTRY should not require touching those files — this
test pins that invariant.
"""

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPT = REPO_ROOT / ".opencode" / "scripts" / "check-platform-hardcodes.sh"


pytestmark = pytest.mark.unit


class TestPlatformHardcodesCheck:
    def test_script_exists(self):
        assert SCRIPT.is_file(), f"{SCRIPT} missing"

    def test_script_is_executable(self):
        mode = SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, f"{SCRIPT} is not executable"

    def test_script_passes_on_current_tree(self):
        if not shutil.which("bash"):
            pytest.skip("bash not available")
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"check-platform-hardcodes.sh reported violations:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def test_grep_pattern_detects_opencode_literal(self, tmp_path):
        synthetic = tmp_path / "synthetic.py"
        synthetic.write_text('if platform == "opencode":\n    pass\n')
        result = subprocess.run(
            [
                "grep",
                "-nE",
                'if[[:space:]].*==[[:space:]]*["\'](opencode|claude)["\']',
                str(synthetic),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "opencode" in result.stdout

    def test_grep_pattern_detects_claude_literal(self, tmp_path):
        synthetic = tmp_path / "synthetic.py"
        synthetic.write_text('if tool == "claude":\n    pass\n')
        result = subprocess.run(
            [
                "grep",
                "-nE",
                'if[[:space:]].*==[[:space:]]*["\'](opencode|claude)["\']',
                str(synthetic),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "claude" in result.stdout

    def test_grep_pattern_ignores_clean_code(self, tmp_path):
        synthetic = tmp_path / "synthetic.py"
        synthetic.write_text("def clean(platform):\n    return REGISTRY[platform]\n")
        result = subprocess.run(
            [
                "grep",
                "-nE",
                'if[[:space:]].*==[[:space:]]*["\'](opencode|claude)["\']',
                str(synthetic),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        # grep returns 1 when no match found; that's the expected (clean) outcome.
        assert result.returncode != 0 or "opencode" not in result.stdout