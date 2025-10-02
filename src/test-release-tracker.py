#!/usr/bin/env python3
"""
Test harness for plugin list extraction + release tracking.
Usage: python test_release_tracker.py
"""

from pathlib import Path
import os

# Assuming you saved the stubs as separate files
from lazy_lock_parser import extract_plugin_list
from release_tracker import ReleaseTracker


def main():
    # Paths (adjust to your setup)
    lazy_lock_path = Path("~/.config/nvim/lazy-lock.json").expanduser()
    lazy_specs_dir = Path("~/.config/nvim/lua/plugins").expanduser()
    cache_dir = Path("~/.cache/nvim-rag").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: Set GITHUB_TOKEN environment variable")
        return

    # Extract plugin list
    print("Extracting plugin list...")
    plugins = extract_plugin_list(lazy_lock_path, lazy_specs_dir)
    print(f"Found {len(plugins)} plugins\n")

    # Initialize release tracker
    tracker = ReleaseTracker(
        cache_file=cache_dir / "releases.json", github_token=github_token
    )

    # Check each plugin for updates
    print("Checking for updates...")
    needs_update = []
    up_to_date = []

    for plugin_name, owner_repo in plugins.items():
        owner, repo = owner_repo.split("/")
        if tracker.needs_update(owner, repo):
            needs_update.append(owner_repo)
            print(f"  ✓ {owner_repo} - needs update")
        else:
            up_to_date.append(owner_repo)
            print(f"  • {owner_repo} - up to date")

    print("\nSummary:")
    print(f"  Needs update: {len(needs_update)}")
    print(f"  Up to date: {len(up_to_date)}")

    # Show which plugins would be fetched
    if needs_update:
        print("\nWould fetch docs for:")
        for repo in needs_update:
            print(f"  - {repo}")


if __name__ == "__main__":
    main()
