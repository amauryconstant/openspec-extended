from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    "skill",
    ["osx-maintain-ai-docs", "osx-modify-artifacts"],
)
@pytest.mark.parametrize("platform", ["opencode", "claude"])
def test_skill_autonomous_gates_precede_questions(skill: str, platform: str) -> None:
    path = Path(__file__).parents[2] / "resources" / platform / "skills" / skill / "SKILL.md"
    lines = path.read_text().splitlines()
    question_lines = [
        index
        for index, line in enumerate(lines)
        if "AskUserQuestion" in line or "Ask tool" in line or "the **`Ask`** tool" in line
    ]
    assert question_lines
    for index in question_lines:
        preceding = "\n".join(lines[max(0, index - 4) : index + 1])
        assert "OSX_AUTONOMOUS=1" in preceding
        assert "skip" in preceding.lower()
