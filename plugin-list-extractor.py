"""
TO FIX:
not getting lazy.nvim
not getting catppuccin
"""

import json
import re
from pathlib import Path


def extract_plugin_list(lazy_lock_path: Path, lazy_specs_dir: Path) -> dict[str, str]:
    """
    Returns: {plugin_name: 'owner/repo'}

    Example:
        {'which-key.nvim': 'folke/which-key.nvim',
         'telescope.nvim': 'nvim-telescope/telescope.nvim'}
    """
    # get plugs from lock
    with open(lazy_lock_path) as f:
        lock_data = json.load(f)

    plugin_names = set(lock_data.keys())

    # extract all owner/repo from specs
    owner_repos = []
    for lua_file in lazy_specs_dir.rglob("*.lua"):
        content = lua_file.read_text()
        # match 'owner/repo' regardless of quotes
        matches = re.findall(r"['\"]([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)['\"]", content)
        owner_repos.extend(matches)

    # match plug names to owner/repo
    result = {}
    for plugin_name in plugin_names:
        exact = [r for r in owner_repos if r.endswith(f"/{plugin_name}")]
        if exact:
            result[plugin_name] = exact[0]
            continue

        normalized = plugin_name.lower().replace(".nvim", "").replace("-", "")
        for repo in owner_repos:
            repo_part = repo.split("/")[-1].lower()
            if repo_part == normalized:
                result[plugin_name] = repo
                break
    unmatched = plugin_names - set(result.keys())
    if unmatched:
        print(f"Warning: Could not find owner/repo for: {unmatched}")
    return result


if __name__ == "__main__":
    plugins = extract_plugin_list(
        Path("~/.config/nvim/lazy-lock.json").expanduser(),
        Path("~/.config/nvim/lua/plugins").expanduser(),
    )
    print(json.dumps(plugins, indent=2))
