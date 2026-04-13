# Mechforge

Autonomous development system for Claude Code. Builds applications feature-by-feature using Claude subagents, tracking progress in a SQLite database that survives interruptions and credit resets.

## How it works

1. You describe what to build in `app_spec.txt`
2. An initializer agent breaks the spec into hundreds of testable features stored in a database
3. Coding agents claim features, implement them, verify with browser automation, and mark them passing
4. Sessions can be interrupted at any time — the next session picks up exactly where the last left off
5. Multiple agents can run in parallel on independent features

## Installation

### Prerequisites

- Python 3.11+
- pip
- Claude Code CLI

### One-time setup

```bash
git clone https://github.com/tpiupiu/mechforge ~/.mechforge
pip install -e ~/.mechforge
```

This installs two commands globally:
- `mechforge` — CLI for adding/updating projects
- `mechforge-mcp` — MCP server that Claude Code connects to

### Add mechforge to a project

```bash
mechforge add ~/path/to/your/project
```

This copies the `.claude/` agents, commands, and templates into your project and writes a `settings.json` pointing at the installed `mechforge-mcp` binary. No per-project Python environment needed.

### Open the project in Claude Code

```bash
cd ~/path/to/your/project
claude
```

Then tell Claude: **"implement this project"** — it reads `CLAUDE.md` and starts autonomously.

## Updating

To pull in the latest agents, templates, and commands:

```bash
cd ~/.mechforge
git pull
mechforge update ~/path/to/your/project
```

`mechforge update` overwrites the `.claude/` assets from the package but never touches your `CLAUDE.md` or `settings.json`.

## Project workflow

### Starting a new project

```
1. mechforge add ~/myproject
2. cd ~/myproject && claude
3. /create-spec          # interactive spec builder
4. "implement this project"
```

The initializer agent reads `app_spec.txt`, populates the feature database, scaffolds the project, and exits. Subsequent sessions pick up coding.

### Resuming work

Just open Claude Code in the project directory and say **"implement this project"**. The session startup protocol in `CLAUDE.md` handles recovery automatically:

- Checks overall progress
- Detects and recovers any features stuck `in_progress` from a previous session
- Claims the next ready feature and starts implementing

### Checking progress

Ask Claude: `feature_get_stats` — or run it directly via any MCP client.

## MCP tools reference

| Tool | Description |
|------|-------------|
| `feature_get_stats` | Passing / in-progress / total counts |
| `feature_get_ready` | Features whose dependencies are all passing |
| `feature_get_in_progress` | Features currently claimed |
| `feature_get_blocked` | Features waiting on unmet dependencies |
| `feature_get_graph` | Full dependency graph |
| `feature_claim_and_get(id)` | Atomically claim + return feature details |
| `feature_mark_passing(id)` | Mark complete after verification |
| `feature_mark_failing(id)` | Mark as regression |
| `feature_clear_in_progress(id)` | Release a stuck claim |
| `feature_skip(id)` | Move to end of queue |
| `feature_create_bulk(features)` | Create the full feature list (initializer only) |
| `feature_request_human_input(id, ...)` | Pause a feature for human response |

## Reverting to the copy approach

The original install method copies the Python source directly into each project and creates a per-project `.venv`. This is still supported and works identically:

```bash
~/.mechforge/mechforge-add.sh ~/path/to/your/project
```

Use this if the package-based approach isn't working in your environment (e.g. the `mechforge-mcp` binary isn't on `PATH` when Claude Code spawns the MCP server).

To switch an existing project back:
1. Run `mechforge-add.sh` — it will copy the code and create `.venv`
2. Update `.claude/settings.json` to use `.venv/bin/python3 -m mcp_server.feature_mcp`

## Database

The feature database lives at `.mechforge/features.db` inside each project. It is gitignored by default. The schema migrates automatically on startup — older databases are upgraded in place.

## Publishing to PyPI

Not currently published. The clone + editable install model is intentional: `git pull` in `~/.mechforge` immediately updates all projects without cutting a release. If the API stabilises and wider distribution is needed, publishing to PyPI requires moving the `.claude/` assets into a proper `importlib.resources`-accessible package.
