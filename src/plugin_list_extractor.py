"""
TO FIX:
not getting lazy.nvim
not getting catppuccin
"""

import json
import re
from pathlib import Path


def extract_plugin_list(
    lazy_lock_path: Path, lazy_specs_dir: Path, config_path: Path
) -> dict[str, str]:
    """
    Returns: {plugin_name: 'owner/repo'}

    Example:
        {'which-key.nvim': 'folke/which-key.nvim',
         'telescope.nvim': 'nvim-telescope/telescope.nvim'}

    Respects plugins_config.json:
    - overrides: manual mapping for edge cases
    - ignore: plugins to skip
    - always_include: plugins to add even if not in lock file
    """
    # step 0: Load config
    config = {"overrides": {}, "ignore": [], "always_include": []}
    if config_path.exists():
        with open(config_path) as f:
            config.update(json.load(f))

    # step 1: get plugs from lock
    with open(lazy_lock_path) as f:
        lock_data = json.load(f)

    plugin_names = set(lock_data.keys())

    plugin_names = plugin_names - set(config["ignore"])

    # step 2: extract all owner/repo from specs
    owner_repos = []
    for lua_file in lazy_specs_dir.rglob("*.lua"):
        content = lua_file.read_text()
        # match 'owner/repo' regardless of quotes
        matches = re.findall(r"['\"]([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)['\"]", content)
        owner_repos.extend(matches)

    # step 3: match plug names to owner/repo
    result = {}

    for plugin_name in plugin_names:
        # Check overrides first
        if plugin_name in config["overrides"]:
            result[plugin_name] = config["overrides"][plugin_name]
            continue

        exact = [r for r in owner_repos if r.endswith(f"/{plugin_name}")]
        if exact:
            result[plugin_name] = exact[0]
            continue

        normalized = (
            plugin_name.lower().replace(".nvim", "").replace("-", "").replace("_", "")
        )
        for repo in owner_repos:
            repo_part = (
                repo.split("/")[-1]
                .lower()
                .replace(".nvim", "")
                .replace("-", "")
                .replace("_", "")
            )
            if repo_part == normalized:
                result[plugin_name] = repo
                break

    # Step 4: Add always_include plugins
    for plugin_name in config["always_include"]:
        # Check if we have an override for it
        if plugin_name in config["overrides"]:
            result[plugin_name] = config["overrides"][plugin_name]
        else:
            # Try to find in specs (special case for lazy.nvim)
            if plugin_name == "lazy.nvim":
                result[plugin_name] = "folke/lazy.nvim"
            else:
                # Try to find in owner_repos
                matches = [r for r in owner_repos if r.endswith(f"/{plugin_name}")]
                if matches:
                    result[plugin_name] = matches[0]

    unmatched = plugin_names - set(result.keys())
    if unmatched:
        print(f"Warning: Could not find owner/repo for: {unmatched}")
        print(f"  Add to 'overrides' in {config_path} if needed")
    return result


if __name__ == "__main__":
    plugins = extract_plugin_list(
        Path("~/.config/nvim/lazy-lock.json").expanduser(),
        Path("~/.config/nvim/lua/plugins").expanduser(),
        Path("../plugin-schema.json"),
    )
    print(json.dumps(plugins, indent=2))
