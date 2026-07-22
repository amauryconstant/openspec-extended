import json
import os
import tempfile
from pathlib import Path


def read_state(change_dir: Path) -> dict | None:
    state_file = change_dir / "state.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text())
    except json.JSONDecodeError:
        return None


def write_state(change_dir: Path, state: dict) -> None:
    state_file = change_dir / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=state_file.parent, suffix=".json"
        ) as temp_file:
            json.dump(state, temp_file, indent=2)
            temp_file.flush()
            temp_path = Path(temp_file.name)
        os.replace(temp_path, state_file)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def clear_phase_complete(change_dir: Path) -> None:
    state = read_state(change_dir)
    if state is None:
        return
    state["phase_complete"] = False
    write_state(change_dir, state)
