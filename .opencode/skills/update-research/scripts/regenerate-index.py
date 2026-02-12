#!/usr/bin/env python3
"""
Regenerate the research documentation index in AGENTS.md

This script extracts H2 sections from claude-code-docs.md and opencode-docs.md,
generates a compressed pipe-delimited index, and updates AGENTS.md.

Usage: python scripts/regenerate-index.py
"""

import re
import sys
from pathlib import Path


def extract_sections(file_path):
    """
    Extract H2 sections with their line numbers from a markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of tuples: (section_name, start_line, end_line)
    """
    sections = []
    lines = file_path.read_text(encoding="utf-8").splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        # Match H2 headings (## at start of line)
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            section_name = match.group(1).strip()
            start_line = i + 1  # 1-based line number

            # Find next H2 or end of file
            j = i + 1
            while j < len(lines) and not re.match(r"^##\s+", lines[j]):
                j += 1

            end_line = j  # Line number before next H2

            sections.append((section_name, start_line, end_line))
            i = j
        else:
            i += 1

    return sections


def generate_index_entry(file_name, sections):
    """
    Generate a compressed index entry for a single file.

    Args:
        file_name: Name of the file (e.g., "claude-code-docs.md")
        sections: List of (section_name, start_line, end_line) tuples

    Returns:
        String: Pipe-delimited index entry
    """
    section_parts = []
    for name, start, end in sections:
        section_parts.append(f"{name}:{start}-{end}")

    return f"|{file_name}:{{{','.join(section_parts)}}}"


def update_agents_md(index_content):
    """
    Update AGENTS.md with the new research documentation index.

    The index is inserted after the "Field Mapping Reference" section
    and before the "# Pre-commit Hooks" section.

    Args:
        index_content: The full index content to insert
    """
    agents_path = Path("AGENTS.md")
    content = agents_path.read_text(encoding="utf-8")

    # Find the insertion point: after "Field Mapping Reference" section
    marker = "# Field Mapping Reference"
    marker_idx = content.find(marker)

    if marker_idx == -1:
        print(f"Error: Could not find '{marker}' section in AGENTS.md", file=sys.stderr)
        return False

    # Find the next H1 section after the marker
    after_marker = content[marker_idx:]
    next_h1_match = re.search(r"\n# [A-Z]", after_marker)

    if next_h1_match:
        insert_pos = marker_idx + next_h1_match.start()
    else:
        # If no next H1, insert at the end
        insert_pos = len(content)

    # Check if index already exists
    index_header = "# Research Documentation Index"
    if index_header in content:
        # Find and replace existing index
        existing_start = content.find(index_header)
        # Find the next H1 section after the index (must start on its own line)
        # Pattern: newline + # + space + capital letter
        next_h1_pattern = r"\n# [A-Z][^\n]*\n"
        next_h1_match = re.search(next_h1_pattern, content[existing_start:])
        if next_h1_match:
            # Calculate end position: start of existing index + match start
            existing_end = existing_start + next_h1_match.start()
            new_content = (
                content[:existing_start] + index_content + content[existing_end:]
            )
        else:
            # No next H1, replace until end of file
            new_content = content[:existing_start] + index_content
    else:
        # Insert new index
        new_content = content[:insert_pos] + index_content + content[insert_pos:]

    # Write back
    agents_path.write_text(new_content, encoding="utf-8")
    return True


def main():
    """Main execution function."""
    # Paths
    # Script is at: .opencode/skills/update-research/scripts/regenerate-index.py
    # Project root is 4 levels up
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent.parent.parent  # Go up to project root
    research_dir = base_dir / "openspec" / "research"

    claude_doc = research_dir / "claude-code-docs.md"
    opencode_doc = research_dir / "opencode-docs.md"

    # Verify files exist
    if not claude_doc.exists():
        print(f"Error: {claude_doc} not found", file=sys.stderr)
        sys.exit(1)
    if not opencode_doc.exists():
        print(f"Error: {opencode_doc} not found", file=sys.stderr)
        sys.exit(1)

    # Extract sections
    claude_sections = extract_sections(claude_doc)
    opencode_sections = extract_sections(opencode_doc)

    print(f"Extracted {len(claude_sections)} sections from {claude_doc.name}")
    print(f"Extracted {len(opencode_sections)} sections from {opencode_doc.name}")

    # Generate index
    index_lines = [
        "",
        "# Research Documentation Index",
        "",
        "[Platform Research Docs Index]|root: ./openspec/research",
        "|IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any tasks.",
        "",
    ]

    index_lines.append(generate_index_entry("claude-code-docs.md", claude_sections))
    index_lines.append(generate_index_entry("opencode-docs.md", opencode_sections))

    index_lines.extend(
        [
            "",
            "For detailed documentation maintenance tasks, invoke the update-research skill.",
            "",
            "---",
            "",
        ]
    )

    index_content = "\n".join(index_lines)

    # Update AGENTS.md
    if update_agents_md(index_content):
        print("✓ Successfully updated AGENTS.md with research documentation index")
        print(f"✓ Index size: {len(index_content)} bytes")
        return 0
    else:
        print("✗ Failed to update AGENTS.md", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
