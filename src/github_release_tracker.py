import json
import requests
from pathlib import Path


class ReleaseTracker:
    def __init__(self, cache_file: Path, github_token: str) -> None:
        self.cache_file = cache_file
        self.headers = {"Authorization": f"token {github_token}"}
        self.cache = self._load_cache()

    def _load_cache(self) -> dict[str, str]:
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def get_latest_release(self, owner: str, repo: str) -> str | None:
        """Fetch latest release tag, return None if no releleases"""
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        resp = requests.get(url, headers=self.headers)

        if resp.status_code == 404:
            # No releases, fall back to latest commit SHA
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/HEAD"
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()["sha"][:7]  # Short SHA
            return None
        if resp.status_code == 200:
            return resp.json()["tag_name"]

        return None

    def needs_update(self, owner: str, repo: str) -> bool:
        key = f"{owner}/{repo}"
        latest = self.get_latest_release(owner, repo)

        if latest is None:
            return False  # Skip if can't determine version

        cached = self.cache.get(key)

        if cached != latest:
            self.cache[key] = latest
            self._save_cache()
            return True

        return False
