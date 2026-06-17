#!/usr/bin/env python3
"""
Integration tests for orchestration logging.
"""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with git repo."""
    env_dir = tmp_path / "test_env"
    env_dir.mkdir()

    (env_dir / "openspec" / "changes").mkdir(parents=True)

    subprocess.run(["git", "init", "-q"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=env_dir, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=env_dir, check=True)

    readme = env_dir / "README.md"
    readme.write_text("# Test repo")
    subprocess.run(["git", "add", "README.md"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=env_dir, check=True
    )

    return env_dir


class TestOrchestrationLogging:
    """Tests for agent output capture in orchestration logging."""

    def test_agent_session_markers_captured(self, test_env):
        """Agent session markers are captured."""
        log_file = test_env / "test.log"
        log_file.write_text(
            "2024-01-15T10:00:00Z [INFO] Agent invocation #1 for PHASE1\n"
            "> osx-builder · glm-5\n"
            "I'll start implementing the change...\n"
            "→ Read proposal.md\n"
            "→ Read design.md\n"
        )

        content = log_file.read_text()
        assert "> osx-builder" in content
        assert "I'll start" in content
        assert "→ Read proposal.md" in content

    def test_tool_calls_captured_with_arrow_prefix(self, test_env):
        """Tool calls are captured with arrow prefix."""
        log_file = test_env / "test.log"
        log_file.write_text(
            "Agent session:\n"
            "→ Read proposal.md\n"
            "→ Glob specs/*.md\n"
            "→ Write design.md\n"
            "→ Bash command executed\n"
        )

        content = log_file.read_text()
        assert content.count("→ Read") == 1
        assert "→ Glob" in content
        assert "→ Write" in content

    def test_multiple_agent_sessions_captured(self, test_env):
        """Multiple agent sessions are captured."""
        log_file = test_env / "test.log"
        log_file.write_text("")

        with open(log_file, "w") as f:
            for i in range(1, 4):
                f.write(f"Agent invocation #{i}\n")
                f.write(f"> osx-analyzer · glm-5\n")
                f.write(f"Processing phase {i}...\n")
                f.write("---\n")

        content = log_file.read_text()
        session_count = content.count("> osx-")
        assert session_count == 3

    def test_orchestrator_messages_interleave_with_agent_output(self, test_env):
        """Orchestrator messages interleave with agent output."""
        log_file = test_env / "test.log"
        log_file.write_text(
            "2024-01-15T10:00:00Z [INFO] Agent invocation #1 for PHASE1\n"
            "> osx-builder · glm-5\n"
            "I'll start implementing...\n"
            "→ Read proposal.md\n"
            "2024-01-15T10:00:30Z [VERBOSE] State updated: PHASE2\n"
            "> osx-analyzer · glm-5\n"
            "I'll review artifacts...\n"
        )

        content = log_file.read_text()
        assert "Agent invocation #1" in content

        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("> osx-builder"):
                assert i > 0
                break
