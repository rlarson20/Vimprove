import subprocess
from pathlib import Path


def fetch_neovim_docs(cache_dir: Path) -> Path:
    """
    Clone/update neovim repo (sparse checkout for runtime/doc only).
    Returns path to doc directory.
    """
    repo_path = cache_dir / "neovim"
    doc_path = repo_path / "runtime" / "doc"

    if repo_path.exists():
        print("Updating neovim repo...")
        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "pull"],
                check=True,
                capture_output=True,
                text=True,
            )
            print("✓ Updated neovim docs")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to update neovim repo: {e.stderr}")
            print("  Using cached version")
    else:
        print("Cloning neovim repo (sparse checkout)...")
        try:
            # Clone with sparse checkout
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--filter=blob:none",
                    "--sparse",
                    "https://github.com/neovim/neovim.git",
                    str(repo_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            # Configure sparse checkout for runtime/doc only
            subprocess.run(
                ["git", "-C", str(repo_path), "sparse-checkout", "set", "runtime/doc"],
                check=True,
                capture_output=True,
                text=True,
            )

            print("✓ Cloned neovim docs")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone neovim repo: {e.stderr}")

    if not doc_path.exists():
        raise RuntimeError(f"Doc directory not found at {doc_path}")

    return doc_path


def process_neovim_docs(doc_path: Path) -> list[dict[str, any]]:
    """
    Process all .txt files in neovim doc directory.
    Returns list of vimdoc chunks.
    """
    from .vim_doc_chunker import chunk_vimdoc  # Assuming previous stub

    all_chunks = []
    txt_files = list(doc_path.glob("*.txt"))

    print(f"Processing {len(txt_files)} neovim doc files...")

    for txt_file in txt_files:
        try:
            content = txt_file.read_text(encoding="utf-8")
            chunks = chunk_vimdoc(content, "neovim-core")
            all_chunks.extend(chunks)
            print(f"  ✓ {txt_file.name}: {len(chunks)} chunks")
        except Exception as e:
            print(f"  ✗ {txt_file.name}: {e}")

    return all_chunks
