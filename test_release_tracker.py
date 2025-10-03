#!/usr/bin/env python3
"""
Test harness for plugin list extraction + release tracking.
Usage: python test_release_tracker.py
"""

from pathlib import Path
import json
import os
from dotenv import load_dotenv

from src.plugin_list_extractor import extract_plugin_list
from src.github_release_tracker import ReleaseTracker


def main():
    load_dotenv()
    # Paths
    config_dir = Path("~/.config/nvim").expanduser()
    cache_dir = Path("./vimprove-cache").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    lazy_lock_path = config_dir / "lazy-lock.json"
    lazy_specs_dir = config_dir / "lua" / "plugins"
    plugins_config_path = cache_dir / "plugins_config.json"

    # Create default config if it doesn't exist
    if not plugins_config_path.exists():
        default_config = {
            "overrides": {},
            "ignore": [],
            "always_include": ["lazy.nvim"],
        }
        with open(plugins_config_path, "w") as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default config at {plugins_config_path}")

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: Set GITHUB_TOKEN environment variable")
        return

    # Extract plugin list
    print("Extracting plugin list...")
    plugins = extract_plugin_list(lazy_lock_path, lazy_specs_dir, plugins_config_path)
    print(f"Found {len(plugins)} plugins (after ignores)\n")

    # Show plugin list
    print("Plugins to track:")
    for name, repo in sorted(plugins.items()):
        print(f"  {name:30} -> {repo}")
    print()

    # Initialize release tracker
    tracker = ReleaseTracker(
        cache_file=cache_dir / "releases.json", github_token=github_token
    )

    # Check each plugin for updates
    print("Checking for updates...")
    needs_update = []
    up_to_date = []
    errors = []

    for plugin_name, owner_repo in plugins.items():
        try:
            owner, repo = owner_repo.split("/")
            if tracker.needs_update(owner, repo):
                needs_update.append(owner_repo)
                print(f"  ✓ {owner_repo} - needs update")
            else:
                up_to_date.append(owner_repo)
                print(f"  • {owner_repo} - up to date")
        except Exception as e:
            errors.append((owner_repo, str(e)))
            print(f"  ✗ {owner_repo} - error: {e}")

    print("\nSummary:")
    print(f"  Needs update: {len(needs_update)}")
    print(f"  Up to date: {len(up_to_date)}")
    if errors:
        print(f"  Errors: {len(errors)}")

    if needs_update:
        print("\nWould fetch docs for:")
        for repo in needs_update:
            print(f"  - {repo}")


if __name__ == "__main__":
    main()
