#!/usr/bin/env python3
"""TOML manifest handling for version tasks."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class Manifest:
    path: Path
    data: dict = field(default_factory=dict)

    @classmethod
    def load(cls, platform: str) -> Manifest:
        manifest_path = PROJECT_ROOT / "resources" / platform / "manifest.toml"
        data = tomllib.loads(manifest_path.read_text())
        return cls(path=manifest_path, data=data)

    def get_version(self) -> str:
        return self.data.get("version", {}).get("version", "")

    def get_resource_version(
        self, resource_type: str, resource_name: str
    ) -> Optional[str]:
        resources = self.data.get("resources", {})
        type_resources = resources.get(resource_type, {})
        resource = type_resources.get(resource_name, {})
        return resource.get("version")

    def set_resource_version(
        self, resource_type: str, resource_name: str, version: str
    ) -> None:
        if "resources" not in self.data:
            self.data["resources"] = {}
        if resource_type not in self.data["resources"]:
            self.data["resources"][resource_type] = {}
        if resource_name not in self.data["resources"][resource_type]:
            self.data["resources"][resource_type][resource_name] = {}
        self.data["resources"][resource_type][resource_name]["version"] = version

    def set_version(self, version: str) -> None:
        if "version" not in self.data:
            self.data["version"] = {}
        self.data["version"]["version"] = version

    def save(self) -> None:
        content = self.path.read_text()
        for resource_type, resources in self.data.get("resources", {}).items():
            for resource_name, values in resources.items():
                if isinstance(values, dict) and "version" in values:
                    pattern = rf'(\[resources\.{resource_type}\.{resource_name}\]\s+version\s*=\s*)"[^"]*"'
                    replacement = rf'\1"{values["version"]}"'
                    import re

                    content = re.sub(pattern, replacement, content)
        self.path.write_text(content)


def get_resource_info_from_path(file_path: str) -> Optional[str]:
    parts = Path(file_path).parts
    if "resources" in parts:
        idx = parts.index("resources")
        if len(parts) > idx + 3:
            resource_type = parts[idx + 2]
            resource_name = Path(parts[idx + 3]).stem
            return f"{resource_type}:{resource_name}"
    return None


def get_platform_for_path(file_path: str) -> Optional[str]:
    parts = Path(file_path).parts
    if "resources" in parts:
        idx = parts.index("resources")
        if len(parts) > idx + 1:
            platform = parts[idx + 1]
            if platform in ("opencode", "claude"):
                return platform
    return None


def validate_semver(version: str) -> bool:
    parts = version.split(".")
    if len(parts) != 3:
        return False
    for part in parts:
        if not part.isdigit():
            return False
    return True


def bump_semver(version: str, bump_type: str) -> str:
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def highest_bump_type(*bump_types: str) -> str:
    order = {"major": 3, "minor": 2, "patch": 1}
    return max(bump_types, key=lambda x: order.get(x, 0))
