#!/usr/bin/env python3
"""
Re-organize repository file structure.

Moves misplaced files into their proper directories:
  - *.js files in root → wine_scripts/ (Wine/JavaScript database utilities)
  - *.py files in root → wine_scripts/ (Python utilities for Wine automation)
  - *.sh files in root → wine_scripts/ (Shell automation scripts)

This script can be run manually or as part of CI.
"""

import os
import shutil
import sys
from pathlib import Path

# Project root (adjust if running from different location)
REPO_ROOT = Path(__file__).parent.resolve()

# Directory mapping: source pattern → target directory
# Files matching patterns in root will be moved to target directory
FILE_CATALOG = [
    # Wine/JavaScript database utilities
    {"pattern": "*.js", "target": "wine_scripts", "desc": "Wine JavaScript database utilities"},

    # Wine/Python automation scripts
    {"pattern": "*.py", "target": "wine_scripts", "desc": "Wine Python automation scripts"},

    # Shell automation scripts
    {"pattern": "*.sh", "target": "wine_scripts", "desc": "Wine shell automation scripts"},
]

# Files to keep in root (exceptions)
ROOT_EXCEPTIONS = {
    "dla_tool.py",      # Core native Linux DLA export/import tool
    "build_all_floors.sh", # Master build script for all floors
    "execute_export_final.sh", # Wine GUI export automation
}

# Build lookup set for efficiency
ROOT_EXCEPTIONS_SET = ROOT_EXCEPTIONS


def should_keep_in_root(filename: str) -> bool:
    """Check if a file should remain in the repository root."""
    return filename in ROOT_EXCEPTIONS_SET


def find_misplaced_files() -> list:
    """Find all files in root that should be moved."""
    misplaced = []

    for entry in FILE_CATALOG:
        pattern = entry["pattern"]
        target_dir = entry["target"]

        for f in REPO_ROOT.glob(pattern):
            if f.is_file() and should_keep_in_root(f.name):
                continue
            misplaced.append({"source": f, "target": REPO_ROOT / target_dir / f.name, "entry": entry})

    return misplaced


def move_file(file_info: dict, dry_run: bool = False) -> bool:
    """Move a single file to its target location."""
    source = file_info["source"]
    target = file_info["target"]
    desc = file_info["entry"]["desc"]

    if dry_run:
        print(f"  [DRY RUN] Would move: {source.name}")
        print(f"             → {target}")
        print(f"             ({desc})")
        return True

    try:
        # Ensure target directory exists
        target.parent.mkdir(parents=True, exist_ok=True)

        # Handle potential name collision
        if target.exists():
            print(f"  ⚠ WARNING: Target exists: {target}")
            print(f"             Keeping original: {source}")
            return False

        # Move the file
        shutil.move(str(source), str(target))
        print(f"  ✓ Moved: {source.name} → {target}")
        return True

    except Exception as e:
        print(f"  ✗ ERROR moving {source}: {e}")
        return False


def print_summary(misplaced: list, moved_count: int):
    """Print summary of actions."""
    if not misplaced:
        print("\n✓ All files are in their correct locations.")
    else:
        print(f"\n{'=' * 60}")
        print(f"Summary:")
        print(f"  Total misplaced files found: {len(misplaced)}")
        print(f"  Successfully moved:          {moved_count}")
        print(f"  Remaining to move:           {len(misplaced) - moved_count}")

        if moved_count > 0:
            print(f"\nNext steps:")
            print(f"  1. Review the changes")
            print(f"  2. Commit: git add -A && git commit -m 'organize: move files to proper directories'")
            print(f"  3. Delete empty directories if needed")
        print(f"{'=' * 60}")


def main():
    dry_run = "--dry-run" in sys.argv

    print(f"Repository: {REPO_ROOT}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    # Show current root files
    print("Current files in repository root:")
    root_files = sorted([f.name for f in REPO_ROOT.glob("*") if f.is_file() and not f.name.startswith('.')])
    for f in root_files:
        print(f"  - {f}")

    print()
    misplaced = find_misplaced_files()

    if not misplaced:
        print_summary([], 0)
        return 0

    print(f"Found {len(misplaced)} files to organize:\n")
    for info in misplaced:
        print(f"  {info['source'].name} → {info['target']} ({info['entry']['desc']})")

    if not dry_run:
        response = input(f"\nProceed with moving {len(misplaced)} files? [y/N]: ")
        if response.lower() not in ('y', 'yes'):
            print("Aborted.")
            return 1

    # Perform moves
    moved = 0
    for info in misplaced:
        if move_file(info, dry_run):
            moved += 1

    print_summary(misplaced, moved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
