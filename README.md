# OpenSpec-extended

A minimal extension system for [OpenSpec](https://github.com/Fission-AI/OpenSpec) that installs additional skills and commands for AI coding assistants.

## Overview

OpenSpec-extended is a simple shell script utility to install custom AI skills for:

- **Claude Code** (`.claude/skills/`)
- **OpenCode** (`.opencode/skills/`)

## Installation

```bash
# Clone repository
git clone <repo-url>
cd OpenSpec-extended

# Run installation script
./install.sh

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

```bash
# Install skills to Claude Code (add missing only)
openspecx install claude

# Install skills to OpenCode (add missing only)
openspecx install opencode

# Force update all skills (overwrite existing)
openspecx update claude
openspecx update opencode
```

## Project Structure

```
OpenSpec-extended/
├── bin/
│   └── openspecx              # Main executable
├── resources/                    # Skills and commands to distribute
│   ├── skills/                # Custom skills
│   │   ├── openspec-modify-artifact/
│   │   └── example-skill/
│   └── commands/              # Custom commands (optional)
├── install.sh              # Installation script
├── README.md
└── LICENSE
```

## Adding Skills

To add new skills, create a directory in `resources/skills/` with a `SKILL.md` file:

```bash
mkdir -p resources/skills/my-custom-skill
cat > resources/skills/my-custom-skill/SKILL.md << 'EOF'
---
name: openspec-my-custom-skill
description: Brief description of what this skill does
license: MIT
---

# Your Skill Instructions
EOF
```

Then run:
```bash
openspecx install claude  # or opencode
```

## Skills Format

Skills must follow the Agent Skills specification:

- **YAML Frontmatter**: Enclosed in `---` delimiters
- **Required Fields**:
  - `name`: Unique skill identifier
  - `description`: Brief description
  - `license`: License identifier
- **Optional Fields**:
  - `metadata`: Additional info (author, version, category, etc.)

## Requirements

- Bash 4.0 or higher
- Linux, macOS, or Windows with WSL

## License

MIT License - see [LICENSE](LICENSE) file

## See Also

- [OpenSpec](https://github.com/Fission-AI/OpenSpec)
- [OpenSpec Documentation](https://github.com/Fission-AI/OpenSpec/blob/main/README.md)
- [Agent Skills Format](https://docs.anthropic.com/en/docs/build-with-claude/skills)
