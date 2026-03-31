#!/usr/bin/env python3
"""Bump detection for version tasks."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class DetectResult:
    bump_type: str
    reason: str
    confidence: str


def detect_bump(file_path: str) -> DetectResult:
    try:
        diff = subprocess.run(
            ["git", "diff", "--cached", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return DetectResult("patch", "git_diff_failed", "low")

    diff_text = diff.stdout.lower()

    if any(x in diff_text for x in ["break:", "breaking", "major:"]):
        return DetectResult("major", "breaking_change", "high")
    if any(x in diff_text for x in ["feat:", "add:", "new:"]):
        return DetectResult("minor", "new_feature", "high")
    if any(x in diff_text for x in ["fix:", "patch:", "bug:"]):
        return DetectResult("patch", "bug_fix", "high")

    added_lines = [
        l for l in diff.stdout.split("\n") if l.startswith("+") and len(l) > 1
    ]
    removed_lines = [
        l for l in diff.stdout.split("\n") if l.startswith("-") and len(l) > 1
    ]

    if len(removed_lines) > len(added_lines) * 2:
        return DetectResult("major", "significant_removal", "medium")
    if added_lines:
        return DetectResult("minor", "additions", "medium")

    return DetectResult("patch", "ambiguous", "low")


def detect_bump_for_resource(file_path: str) -> DetectResult:
    return detect_bump(file_path)


def detect_bump_for_script(file_path: str) -> DetectResult:
    return detect_bump(file_path)
