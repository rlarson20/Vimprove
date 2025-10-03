import requests
import time


class PluginDocFetcher:
    def __init__(self, github_token: str, rate_limit_delay: float = 0.1):
        self.headers = {"Authorization": f"token {github_token}"}
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_plugin_docs(self, owner: str, repo: str) -> dict[str, any]:
        """
        Fetch plugin help files or README.
        Returns: {
            'type': 'vimdoc' | 'markdown',
            'files': [{'name': str, 'content': str}, ...]
        }
        Raises exception if neither help files nor README found.
        """
        # Try help files first
        help_files = self._fetch_help_files(owner, repo)
        if help_files:
            return {"type": "vimdoc", "files": help_files}

        # Fallback to README
        readme = self._fetch_readme(owner, repo)
        if readme:
            return {"type": "markdown", "files": [readme]}

        raise Exception(f"No documentation found for {owner}/{repo}")

    def _fetch_help_files(self, owner: str, repo: str) -> list[dict[str, str]] | None:
        """Fetch .txt files from doc/ directory."""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/doc"
            resp = self.session.get(url)
            time.sleep(self.rate_limit_delay)

            if resp.status_code == 404:
                return None

            resp.raise_for_status()

            contents = resp.json()
            txt_files = [f for f in contents if f["name"].endswith(".txt")]

            if not txt_files:
                return None

            result = []
            for f in txt_files:
                file_resp = self.session.get(f["download_url"])
                time.sleep(self.rate_limit_delay)
                file_resp.raise_for_status()

                result.append({"name": f["name"], "content": file_resp.text})

            return result

        except requests.RequestException as e:
            print(f"  Warning: Error fetching help files for {owner}/{repo}: {e}")
            return None

    def _fetch_readme(self, owner: str, repo: str) -> dict[str, str] | None:
        """Fetch README via GitHub API."""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            resp = self.session.get(url)
            time.sleep(self.rate_limit_delay)

            if resp.status_code == 404:
                return None

            resp.raise_for_status()

            readme_data = resp.json()
            readme_resp = self.session.get(readme_data["download_url"])
            time.sleep(self.rate_limit_delay)
            readme_resp.raise_for_status()

            return {"name": readme_data["name"], "content": readme_resp.text}

        except requests.RequestException as e:
            print(f"  Warning: Error fetching README for {owner}/{repo}: {e}")
            return None


def process_plugin_docs(
    plugins: dict[str, str], github_token: str, release_tracker
) -> list[dict[str, any]]:
    """
    Fetch and process docs for all plugins.
    Only fetches if release has changed.
    Returns list of all chunks.
    """
    from .vim_doc_chunker import chunk_vimdoc
    from .readme_chunker import chunk_markdown

    fetcher = PluginDocFetcher(github_token)
    all_chunks = []

    for plugin_name, owner_repo in plugins.items():
        owner, repo = owner_repo.split("/")

        # Check if we need to update
        if not release_tracker.needs_update(owner, repo):
            print(f"  • {owner_repo} - skipping (no changes)")
            continue

        print(f"  ✓ {owner_repo} - fetching docs")

        try:
            docs = fetcher.fetch_plugin_docs(owner, repo)

            for file_info in docs["files"]:
                if docs["type"] == "vimdoc":
                    chunks = chunk_vimdoc(file_info["content"], owner_repo)
                else:  # markdown
                    chunks = chunk_markdown(file_info["content"], owner_repo)

                all_chunks.extend(chunks)
                print(f"    {file_info['name']}: {len(chunks)} chunks")

        except Exception as e:
            print(f"  ✗ {owner_repo} - error: {e}")
            continue

    return all_chunks
