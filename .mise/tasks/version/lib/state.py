#!/usr/bin/env python3
"""State file handling for version tasks."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
VERSION_STATE_FILE = PROJECT_ROOT / ".mise" / "version-state.json"


def write_version_state(status: str, files_json: str) -> None:
    state = {
        "status": status,
        "files": json.loads(files_json),
    }
    VERSION_STATE_FILE.write_text(json.dumps(state, indent=2))


def get_state_status() -> str:
    if not VERSION_STATE_FILE.exists():
        return ""
    try:
        data = json.loads(VERSION_STATE_FILE.read_text())
        return data.get("status", "")
    except (json.JSONDecodeError, IOError):
        return ""


def get_state_files() -> str:
    if not VERSION_STATE_FILE.exists():
        return "[]"
    try:
        data = json.loads(VERSION_STATE_FILE.read_text())
        return json.dumps(data.get("files", []))
    except (json.JSONDecodeError, IOError):
        return "[]"
