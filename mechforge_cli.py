#!/usr/bin/env python3
"""
mechforge CLI — add or update mechforge in a project.

Usage:
    mechforge add <project-dir>     # install mechforge into a project (package mode)
    mechforge update <project-dir>  # refresh .claude/ assets from the installed package

Package mode vs copy mode
--------------------------
This CLI uses the *package* approach: the MCP server runs from the globally-
installed mechforge package, so no per-project .venv or Python code is needed.

To go back to the *copy* approach (code copied into the project, per-project
.venv), just run the original shell script instead:

    /path/to/.mechforge/mechforge-add.sh <project-dir>
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# The directory that contains this file is the mechforge repo root.
MECHFORGE_DIR = Path(__file__).resolve().parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_mechforge_mcp() -> Path:
    """Return the absolute path to the mechforge-mcp binary.

    Looks in the same bin directory as the running 'mechforge' command first,
    then falls back to PATH search.  This ensures we reference the same
    installation that is currently running.
    """
    # sys.argv[0] is the path to the running 'mechforge' script
    this_bin = Path(sys.argv[0]).resolve()
    candidate = this_bin.parent / "mechforge-mcp"
    if candidate.exists():
        return candidate

    # Fallback: search PATH
    found = shutil.which("mechforge-mcp")
    if found:
        return Path(found).resolve()

    raise SystemExit(
        "Error: mechforge-mcp not found.\n"
        "Make sure mechforge is installed:  pip install -e /path/to/.mechforge"
    )


def _write_settings_json(target_dir: Path, mechforge_mcp: Path) -> None:
    """Write .claude/settings.json with the package-based MCP server config."""
    settings = {
        "mcpServers": {
            "mechforge": {
                "command": str(mechforge_mcp),
                "cwd": str(target_dir),
                "env": {
                    "PROJECT_DIR": str(target_dir)
                }
            }
        }
    }
    settings_path = target_dir / ".claude" / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _copy_claude_assets(src_dir: Path, dst_dir: Path, overwrite: bool) -> list[str]:
    """Copy .claude/ subdirectories from src to dst.

    Returns a list of human-readable change lines.
    """
    changes = []
    subdirs = ["agents", "commands", "templates", "skills"]

    for subdir in subdirs:
        src = src_dir / subdir
        if not src.exists():
            continue

        dst_subdir = dst_dir / subdir
        dst_subdir.mkdir(parents=True, exist_ok=True)

        for src_file in src.iterdir():
            if src_file.is_dir():
                # Handle skill subdirectories
                dst_skill = dst_subdir / src_file.name
                if dst_skill.exists() and not overwrite:
                    changes.append(f"  skip  .claude/{subdir}/{src_file.name}/ (already exists)")
                else:
                    if dst_skill.exists():
                        shutil.rmtree(dst_skill)
                    shutil.copytree(src_file, dst_skill)
                    action = "update" if dst_skill.exists() else "add  "
                    changes.append(f"  {action} .claude/{subdir}/{src_file.name}/")
            else:
                dst_file = dst_subdir / src_file.name
                if dst_file.exists() and not overwrite:
                    changes.append(f"  skip  .claude/{subdir}/{src_file.name} (already exists)")
                else:
                    action = "update" if dst_file.exists() else "add  "
                    shutil.copy2(src_file, dst_file)
                    changes.append(f"  {action} .claude/{subdir}/{src_file.name}")

    return changes


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(target_dir_str: str) -> None:
    """Add mechforge to a project using the installed package (no code copying)."""
    target_dir = Path(target_dir_str).resolve()

    if not target_dir.exists():
        raise SystemExit(f"Error: '{target_dir}' does not exist")
    if not target_dir.is_dir():
        raise SystemExit(f"Error: '{target_dir}' is not a directory")
    if target_dir == MECHFORGE_DIR:
        raise SystemExit("Error: target cannot be the mechforge directory itself")

    mechforge_mcp = _find_mechforge_mcp()

    print(f"Adding mechforge to: {target_dir}")
    print(f"Using MCP binary:    {mechforge_mcp}")
    print()

    src_claude = MECHFORGE_DIR / ".claude"

    # ── .claude/ assets ──────────────────────────────────────────────────────

    if (target_dir / ".claude").exists():
        print("→ Merging .claude/ (existing config found)")
        changes = _copy_claude_assets(src_claude, target_dir / ".claude", overwrite=False)
        for line in changes:
            print(line)

        # settings.json — skip if exists, show manual instructions
        if (target_dir / ".claude" / "settings.json").exists():
            print("  skip  .claude/settings.json (already exists — see manual step below)")
            settings_skipped = True
        else:
            _write_settings_json(target_dir, mechforge_mcp)
            print("  add   .claude/settings.json")
            settings_skipped = False
    else:
        print("→ Copying .claude/ (fresh install)")
        shutil.copytree(src_claude, target_dir / ".claude")
        _write_settings_json(target_dir, mechforge_mcp)
        print("  added .claude/")
        settings_skipped = False

    # ── CLAUDE.md ─────────────────────────────────────────────────────────────

    src_claude_md = MECHFORGE_DIR / "CLAUDE.md"
    dst_claude_md = target_dir / "CLAUDE.md"

    if dst_claude_md.exists():
        print("→ Appending mechforge section to existing CLAUDE.md")
        existing = dst_claude_md.read_text()
        if src_claude_md.read_text().strip() not in existing:
            with dst_claude_md.open("a") as f:
                f.write("\n\n---\n\n")
                f.write(src_claude_md.read_text())
        else:
            print("  (mechforge section already present — skipped)")
    else:
        print("→ Copying CLAUDE.md")
        shutil.copy2(src_claude_md, dst_claude_md)

    # ── .mechforge/ dir (for database) ───────────────────────────────────────

    (target_dir / ".mechforge").mkdir(exist_ok=True)

    # ── .gitignore ────────────────────────────────────────────────────────────

    gitignore = target_dir / ".gitignore"
    ignore_entries = [".mechforge/features.db"]
    if gitignore.exists():
        existing_lines = gitignore.read_text().splitlines()
        added = []
        with gitignore.open("a") as f:
            for entry in ignore_entries:
                if entry not in existing_lines:
                    f.write(f"{entry}\n")
                    added.append(entry)
        if added:
            print(f"→ Added to .gitignore: {', '.join(added)}")
    else:
        gitignore.write_text("\n".join(ignore_entries) + "\n")
        print("→ Created .gitignore")

    # ── Done ──────────────────────────────────────────────────────────────────

    print()
    print(f"✓ mechforge added to {target_dir}")
    print()

    if settings_skipped:
        print("ACTION REQUIRED — add this to your .claude/settings.json mcpServers block:")
        print()
        print('  "mechforge": {')
        print(f'    "command": "{mechforge_mcp}",')
        print(f'    "cwd": "{target_dir}",')
        print(f'    "env": {{ "PROJECT_DIR": "{target_dir}" }}')
        print('  }')
        print()

    print("Next steps:")
    print(f"  1. Open Claude Code in {target_dir}")
    print("  2. Run /create-spec to generate app_spec.txt")
    print("  3. Tell Claude: 'implement this project' — it will read CLAUDE.md and start")
    print()
    print("To revert to the copy approach (code copied into project, per-project .venv):")
    print(f"  {MECHFORGE_DIR}/mechforge-add.sh {target_dir}")
    print()


def cmd_update(target_dir_str: str) -> None:
    """Update .claude/ assets in an existing project from the installed package.

    Overwrites agents/, commands/, templates/, skills/ with the latest versions.
    Never touches CLAUDE.md or settings.json.
    """
    target_dir = Path(target_dir_str).resolve()

    if not target_dir.exists() or not target_dir.is_dir():
        raise SystemExit(f"Error: '{target_dir}' is not a directory")

    if not (target_dir / ".claude").exists():
        raise SystemExit(
            f"Error: no .claude/ directory in '{target_dir}'.\n"
            "Run 'mechforge add' first."
        )

    print(f"Updating mechforge assets in: {target_dir}")
    print()

    src_claude = MECHFORGE_DIR / ".claude"
    changes = _copy_claude_assets(src_claude, target_dir / ".claude", overwrite=True)

    if changes:
        for line in changes:
            print(line)
    else:
        print("  (no changes)")

    print()
    print("✓ Done. CLAUDE.md and settings.json were not modified.")
    print()
    print("To also update the MCP binary path in settings.json, run:")
    print(f"  mechforge add {target_dir}  (re-add is idempotent for all but settings.json)")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mechforge",
        description="Add or update mechforge in a project (package mode).",
        epilog=(
            "To use the copy approach instead (code copied into project):\n"
            f"  {MECHFORGE_DIR}/mechforge-add.sh <project-dir>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add mechforge to a project")
    p_add.add_argument("project_dir", help="Path to the target project directory")

    p_update = sub.add_parser("update", help="Refresh .claude/ assets from the installed package")
    p_update.add_argument("project_dir", help="Path to the target project directory")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args.project_dir)
    elif args.command == "update":
        cmd_update(args.project_dir)


if __name__ == "__main__":
    main()
