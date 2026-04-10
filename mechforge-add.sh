#!/usr/bin/env bash
# mechforge-add.sh — add mechforge to an existing project
#
# Usage:
#   ./mechforge-add.sh /path/to/your/project
#   ./mechforge-add.sh .   (add to current directory)

set -euo pipefail

MECHFORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-}"

# ── Validation ────────────────────────────────────────────────────────────────

if [[ -z "$TARGET_DIR" ]]; then
    echo "Usage: $0 <target-project-directory>"
    exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: '$TARGET_DIR' is not a directory"
    exit 1
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

if [[ "$TARGET_DIR" == "$MECHFORGE_DIR" ]]; then
    echo "Error: target cannot be the mechforge directory itself"
    exit 1
fi

echo "Adding mechforge to: $TARGET_DIR"
echo ""

# ── Copy core files ───────────────────────────────────────────────────────────

echo "→ Copying api/ (database, dependency resolver, migration)"
cp -r "$MECHFORGE_DIR/api" "$TARGET_DIR/"

echo "→ Copying mcp_server/ (feature MCP tools)"
cp -r "$MECHFORGE_DIR/mcp_server" "$TARGET_DIR/"

echo "→ Copying requirements.txt"
cp "$MECHFORGE_DIR/requirements.txt" "$TARGET_DIR/"

# ── Copy .claude/ config ──────────────────────────────────────────────────────

if [[ -d "$TARGET_DIR/.claude" ]]; then
    echo "→ Merging .claude/ (existing config found — merging carefully)"

    # Agents
    mkdir -p "$TARGET_DIR/.claude/agents"
    for f in "$MECHFORGE_DIR/.claude/agents/"*.md; do
        name="$(basename "$f")"
        if [[ -f "$TARGET_DIR/.claude/agents/$name" ]]; then
            echo "  skip .claude/agents/$name (already exists)"
        else
            cp "$f" "$TARGET_DIR/.claude/agents/$name"
            echo "  added .claude/agents/$name"
        fi
    done

    # Commands
    mkdir -p "$TARGET_DIR/.claude/commands"
    for f in "$MECHFORGE_DIR/.claude/commands/"*.md; do
        name="$(basename "$f")"
        if [[ -f "$TARGET_DIR/.claude/commands/$name" ]]; then
            echo "  skip .claude/commands/$name (already exists)"
        else
            cp "$f" "$TARGET_DIR/.claude/commands/$name"
            echo "  added .claude/commands/$name"
        fi
    done

    # Templates
    mkdir -p "$TARGET_DIR/.claude/templates"
    for f in "$MECHFORGE_DIR/.claude/templates/"*; do
        name="$(basename "$f")"
        if [[ -f "$TARGET_DIR/.claude/templates/$name" ]]; then
            echo "  skip .claude/templates/$name (already exists)"
        else
            cp "$f" "$TARGET_DIR/.claude/templates/$name"
            echo "  added .claude/templates/$name"
        fi
    done

    # settings.json — merge mcpServers block if file exists
    if [[ -f "$TARGET_DIR/.claude/settings.json" ]]; then
        echo "  skip .claude/settings.json (already exists — add MCP server manually, see below)"
        SETTINGS_SKIPPED=true
    else
        cp "$MECHFORGE_DIR/.claude/settings.json" "$TARGET_DIR/.claude/settings.json"
        echo "  added .claude/settings.json"
        SETTINGS_SKIPPED=false
    fi
else
    echo "→ Copying .claude/ (fresh install)"
    cp -r "$MECHFORGE_DIR/.claude" "$TARGET_DIR/"
    SETTINGS_SKIPPED=false
fi

# ── Copy CLAUDE.md ────────────────────────────────────────────────────────────

if [[ -f "$TARGET_DIR/CLAUDE.md" ]]; then
    echo "→ Appending mechforge section to existing CLAUDE.md"
    echo "" >> "$TARGET_DIR/CLAUDE.md"
    echo "---" >> "$TARGET_DIR/CLAUDE.md"
    echo "" >> "$TARGET_DIR/CLAUDE.md"
    cat "$MECHFORGE_DIR/CLAUDE.md" >> "$TARGET_DIR/CLAUDE.md"
else
    echo "→ Copying CLAUDE.md"
    cp "$MECHFORGE_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
fi

# ── Python dependencies ───────────────────────────────────────────────────────

echo ""
echo "→ Installing Python dependencies"
if command -v pip3 &>/dev/null; then
    pip3 install -q -r "$TARGET_DIR/requirements.txt"
    echo "  installed: mcp, pydantic, sqlalchemy"
elif command -v pip &>/dev/null; then
    pip install -q -r "$TARGET_DIR/requirements.txt"
    echo "  installed: mcp, pydantic, sqlalchemy"
else
    echo "  WARNING: pip not found — install manually: pip install -r requirements.txt"
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "✓ mechforge added to $TARGET_DIR"
echo ""

if [[ "${SETTINGS_SKIPPED:-false}" == "true" ]]; then
    echo "ACTION REQUIRED — add this to your .claude/settings.json mcpServers block:"
    echo ""
    echo '  "mechforge": {'
    echo '    "command": "python",'
    echo '    "args": ["-m", "mcp_server.feature_mcp"],'
    echo '    "env": { "PROJECT_DIR": "." }'
    echo '  }'
    echo ""
fi

echo "Next steps:"
echo "  1. Open Claude Code in $TARGET_DIR"
echo "  2. Run /create-spec to generate app_spec.txt"
echo "  3. Tell Claude: 'implement this project' — it will read CLAUDE.md and start"
echo ""
