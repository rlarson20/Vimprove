"""Tests for plugin list extraction."""

import json
import tempfile
from pathlib import Path
from src.plugin_list_extractor import extract_plugin_list


def test_plugin_extraction_basic():
    """Test basic plugin extraction."""
    # Create temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create lock file
        lock_file = tmpdir / "lazy-lock.json"
        lock_file.write_text(
            json.dumps(
                {
                    "telescope.nvim": {"version": "abc123"},
                    "which-key.nvim": {"version": "def456"},
                }
            )
        )

        # Create spec file
        specs_dir = tmpdir / "lua" / "plugins"
        specs_dir.mkdir(parents=True)

        spec_file = specs_dir / "telescope.lua"
        spec_file.write_text("""
return {
  'nvim-telescope/telescope.nvim',
  dependencies = { 'nvim-lua/plenary.nvim' }
}
""")

        spec_file2 = specs_dir / "which-key.lua"
        spec_file2.write_text("""
return { 'folke/which-key.nvim' }
""")

        # Create config
        config_file = tmpdir / "config.json"
        config_file.write_text(
            json.dumps({"overrides": {}, "ignore": [], "always_include": []})
        )

        # Extract
        plugins = extract_plugin_list(lock_file, specs_dir, config_file)

        assert len(plugins) == 2
        assert plugins["telescope.nvim"] == "nvim-telescope/telescope.nvim"
        assert plugins["which-key.nvim"] == "folke/which-key.nvim"


def test_plugin_extraction_with_ignore():
    """Test plugin extraction respects ignore list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        lock_file = tmpdir / "lazy-lock.json"
        lock_file.write_text(
            json.dumps(
                {
                    "telescope.nvim": {"version": "abc123"},
                    "tokyonight.nvim": {"version": "def456"},
                }
            )
        )

        specs_dir = tmpdir / "lua" / "plugins"
        specs_dir.mkdir(parents=True)

        spec_file = specs_dir / "plugins.lua"
        spec_file.write_text("""
return {
  { 'nvim-telescope/telescope.nvim' },
  { 'folke/tokyonight.nvim' }
}
""")

        config_file = tmpdir / "config.json"
        config_file.write_text(
            json.dumps(
                {"overrides": {}, "ignore": ["tokyonight.nvim"], "always_include": []}
            )
        )

        plugins = extract_plugin_list(lock_file, specs_dir, config_file)

        assert len(plugins) == 1
        assert "telescope.nvim" in plugins
        assert "tokyonight.nvim" not in plugins
