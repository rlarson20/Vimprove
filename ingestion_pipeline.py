#!/usr/bin/env python3
"""
Vimprove ingestion pipeline.
Fetches and chunks documentation for Neovim core + plugins.

Usage:
    uv run ingest.py [--force]
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict

from src.plugin_list_extractor import extract_plugin_list
from src.github_release_tracker import ReleaseTracker
from src.vim_doc_chunker import chunk_vimdoc
from src.readme_chunker import chunk_markdown
from src.core_doc_fetcher import fetch_neovim_docs
from src.plugin_doc_fetcher import PluginDocFetcher
from src.chunk import save_chunks
from src.error_logger import ErrorLogger


class VimproveIngestion:
    def __init__(
        self, config_dir: Path, cache_dir: Path, github_token: str, force: bool = False
    ):
        self.config_dir = config_dir
        self.cache_dir = cache_dir
        self.github_token = github_token
        self.force = force

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir = self.cache_dir / "chunks"

        self.error_logger = ErrorLogger(self.cache_dir / "errors.json")
        self.release_tracker = ReleaseTracker(
            cache_file=self.cache_dir / "releases.json", github_token=github_token
        )

    def run(self):
        """Execute full ingestion pipeline."""
        print("=" * 60)
        print("Vimprove Documentation Ingestion")
        print("=" * 60)

        # Step 1: Extract plugin list
        print("\n[1/4] Extracting plugin list...")
        plugins = self._extract_plugins()
        print(f"  Found {len(plugins)} plugins to process")

        # Step 2: Process Neovim core docs
        print("\n[2/4] Processing Neovim core documentation...")
        self._process_neovim_core()

        # Step 3: Process plugin docs
        print("\n[3/4] Processing plugin documentation...")
        self._process_plugins(plugins)

        # Step 4: Save errors
        print("\n[4/4] Finalizing...")
        self.error_logger.save()

        print("\n" + "=" * 60)
        print("✓ Ingestion complete")
        print(f"  Chunks stored in: {self.chunks_dir}")
        if self.error_logger.has_errors():
            print(f"  Errors logged to: {self.cache_dir / 'errors.json'}")
        print("=" * 60)

    def _extract_plugins(self) -> Dict[str, str]:
        """Extract plugin list from lazy-lock and specs."""
        lazy_lock_path = self.config_dir / "lazy-lock.json"
        lazy_specs_dir = self.config_dir / "lua" / "plugins"
        plugins_config_path = self.cache_dir / "plugins_config.json"

        # Create default config if needed
        if not plugins_config_path.exists():
            default_config = {
                "overrides": {},
                "ignore": [],
                "always_include": ["lazy.nvim"],
            }
            with open(plugins_config_path, "w") as f:
                json.dump(default_config, f, indent=2)
            print(f"  Created default config: {plugins_config_path}")

        try:
            plugins = extract_plugin_list(
                lazy_lock_path, lazy_specs_dir, plugins_config_path
            )
            return plugins
        except Exception as e:
            self.error_logger.log_error(
                source="plugin-extraction",
                error_type="extraction_failed",
                message=str(e),
            )
            raise

    def _process_neovim_core(self):
        """Fetch and chunk Neovim core documentation."""
        output_dir = self.chunks_dir / "neovim-core"

        # Check if we should skip (unless force flag)
        if not self.force and output_dir.exists():
            existing_files = list(output_dir.glob("*.json"))
            if existing_files:
                print("  ℹ  Using cached neovim-core docs (use --force to refresh)")
                return

        try:
            # Fetch docs
            doc_path = fetch_neovim_docs(self.cache_dir / "neovim")

            # Process each doc file
            txt_files = list(doc_path.glob("*.txt"))
            print(f"  Processing {len(txt_files)} doc files...")

            for txt_file in txt_files:
                try:
                    content = txt_file.read_text(encoding="utf-8")
                    chunks = chunk_vimdoc(content, "neovim-core")

                    if chunks:
                        output_path = output_dir / f"{txt_file.stem}.json"
                        save_chunks(chunks, f"neovim-core/{txt_file.stem}", output_path)
                        print(f"    ✓ {txt_file.name}: {len(chunks)} chunks")

                except Exception as e:
                    self.error_logger.log_error(
                        source=f"neovim-core/{txt_file.name}",
                        error_type="processing_failed",
                        message=str(e),
                    )
                    print(f"    ✗ {txt_file.name}: {e}")

        except Exception as e:
            self.error_logger.log_error(
                source="neovim-core", error_type="fetch_failed", message=str(e)
            )
            raise

    def _process_plugins(self, plugins: Dict[str, str]):
        """Fetch and chunk plugin documentation."""
        output_dir = self.chunks_dir / "plugins"
        fetcher = PluginDocFetcher(self.github_token)

        processed = 0
        skipped = 0
        failed = 0

        for plugin_name, owner_repo in plugins.items():
            owner, repo = owner_repo.split("/")
            output_path = output_dir / f"{repo}.json"

            # Check if we need to update
            needs_update = self.force or self.release_tracker.needs_update(owner, repo)

            if not needs_update:
                # Keep existing chunks
                if output_path.exists():
                    print(f"  • {owner_repo} - no changes")
                    skipped += 1
                    continue

            print(f"  ⟳ {owner_repo} - fetching...")

            try:
                # Fetch docs
                docs = fetcher.fetch_plugin_docs(owner, repo)

                # Process all files
                all_chunks = []
                for file_info in docs["files"]:
                    if docs["type"] == "vimdoc":
                        chunks = chunk_vimdoc(file_info["content"], owner_repo)
                    else:  # markdown
                        chunks = chunk_markdown(file_info["content"], owner_repo)

                    all_chunks.extend(chunks)

                # Save chunks
                if all_chunks:
                    save_chunks(all_chunks, owner_repo, output_path)
                    print(
                        f"    ✓ {len(all_chunks)} chunks from {len(docs['files'])} file(s)"
                    )
                    processed += 1
                else:
                    print("    ⚠  No chunks generated")

            except Exception as e:
                failed += 1
                self.error_logger.log_error(
                    source=owner_repo,
                    error_type="plugin_processing_failed",
                    message=str(e),
                    details={"owner": owner, "repo": repo},
                )
                print(f"    ✗ Error: {e}")

                # Keep old chunks if they exist
                if output_path.exists():
                    print("    ℹ  Keeping cached chunks")

        print(f"\n  Summary: {processed} processed, {skipped} skipped, {failed} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Neovim and plugin documentation"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("~/.config/nvim").expanduser(),
        help="Neovim config directory (default: ~/.config/nvim)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("./vimprove-cache").resolve(),
        help="Cache directory (default: ./vimprove-cache)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force refresh all documentation"
    )

    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()

    # Check for GitHub token
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("  Get a token at: https://github.com/settings/tokens")
        return 1

    # Run ingestion
    ingestion = VimproveIngestion(
        config_dir=args.config_dir,
        cache_dir=args.cache_dir,
        github_token=github_token,
        force=args.force,
    )

    try:
        ingestion.run()
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
