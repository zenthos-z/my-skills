# my-skills

Claude Code skills monorepo — AI-powered productivity tools.

## Skills

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| [mermaid-pro](./mermaid-pro/) | Professional Mermaid diagram generation with syntax validation | Node.js, npm |
| [systems-thinking](./systems-thinking/) | Structured systems thinking interviews with session persistence | None |
| [qunribao](./qunribao/) | WeChat group daily/weekly report generation | Python 3.8+, WeFlow |
| [quick-img](./quick-img/) | Quick image generation via DMX API | Python 3.8+ |

## Cross-skill Dependencies

- `qunribao` optionally uses `quick-img` for daily report image generation (gracefully degrades if not installed)

## Standalone Installation

Each skill is independently usable. Copy any subdirectory to your skills folder:

```bash
# Example: install mermaid-pro only
cp -r mermaid-pro ~/.claude/skills/

# Example: install all skills
cp -r */ ~/.claude/skills/
```

Or install from GitHub:
```bash
npx skills add zenthos-z/my-skills/mermaid-pro
npx skills add zenthos-z/my-skills/systems-thinking
npx skills add zenthos-z/my-skills/qunribao
npx skills add zenthos-z/my-skills/quick-img
```

## Setup

```bash
# Install Node.js dependencies (mermaid-pro)
cd mermaid-pro/scripts && npm install
```

See each skill's README for specific configuration instructions.
