# Vimprove

RAG-powered Neovim configuration assistant. Query your plugin docs and Neovim core documentation using natural language.

## Features

- Indexes Neovim core docs + all your installed plugins
- Semantic search via local embeddings (no API costs for search, only model response)
- LLM-powered responses with code snippets
- CLI and Neovim plugin interfaces
- Incremental updates (only re-fetches changed plugin releases)

## Architecture

```
User Query
↓
Vector Search (Chroma + sentence-transformers)
↓
Top-K relevant doc chunks
↓
LLM (via OpenRouter)
↓
Formatted response (explanation + config + sources)
```

## Prerequisites

- Python 3.11+
- uv (Python package manager)
- Git 2.19+ (for partial clones)
- GitHub personal access token
- OpenRouter API key

## Installation

### 1. Clone and setup

```bash
git clone https://github.com/rlarson20/vimprove.git
cd Vimprove

# Install dependencies
uv sync
```

### 2. Configure environment

#### Create .env file

```bash
cat > .env << EOF
GITHUB_TOKEN=your_github_token_here
OPENROUTER_API_KEY=your_openrouter_key_here
EOF
```

#### Get tokens:

GitHub: https://github.com/settings/tokens (needs public_repo scope)
OpenRouter: https://openrouter.ai/keys

### 3. Initial ingestion

```bash
# Fetch and chunk all documentation (~2-5 minutes)
uv run ingestion_pipeline.py

# Embed chunks into vector DB (~2-5 minutes)
uv run src/embedding_pipeline.py
```

### 4. Start API server

```bash
# Terminal 1: Run API
uv run api.py

# Terminal 2: Test query
uv run cli.py "How do I add LSP keymaps?"
```

## Usage

### CLI

```bash
# Basic query
uv run cli.py "How do I configure telescope?"

# With context (provide config file)
uv run cli.py "Add fuzzy finder" --context ~/.config/nvim/init.lua

# Stream response
uv run cli.py "Setup treesitter" --stream

# Different model
uv run cli.py "LSP setup" --model anthropic/claude-3.5-sonnet
```

### Neovim plugin

Add to `lazy.nvim` config:

```lua
{
	"rlarson20/vimprove.nvim",
	dir = "/path/to/Vimprove/nvim-plugin", -- Local development
	config = function()
		require("vimprove").setup({
			cli_path = "uv run --directory /path/to/Vimprove/  /path/to/Vimprove/cli.py",
			api_url = "http://localhost:8000",
			model = "anthropic/claude-4.5-sonnet",
		})
	end,
	-- Lazy load on command
	cmd = { "Vimprove", "VimproveContext" },
}
```

#### Commands

- `:Vimprove <query>` - Query without context
- `:VimproveContext` - Query with current buffer as context
- `<leader>vq` - Keybinding for context query

### Configuration

#### Ignore plugins

Edit `vimprove-cache/plugins_config.json`:

```json
{
  "overrides": {
    "catppuccin": "catppuccin/nvim"
  },
  "ignore": ["tokyonight.nvim", "rose-pine"],
  "always_include": ["lazy.nvim"]
}
```

#### Update documentation

```bash
# Weekly cron job (only fetches changed plugins)
0 2 * * 0 cd <where-you-cloned-the-repo> && uv run ingestion_pipeline.py && uv run src/embedding_pipeline.py

# Force refresh everything
uv run ingestion_pipeline.py --force
uv run src/embedding_pipeline.py --force
```

## Directory structure

```bash
vimprove-cache/
├── chunks/              # Chunked documentation (JSON)
│   ├── neovim-core/
│   └── plugins/
├── vector_db/           # Chroma vector database
├── neovim/              # Cloned neovim repo
├── releases.json        # Plugin version tracking
├── plugins_config.json  # Plugin overrides/ignores
└── errors.json          # Ingestion errors (if any)
```

## Troubleshooting

### API Server won't start

- Check `OPENROUTER_API_KEY` is set
- Verify vector DB exists: `ls vimprove-cache/vector_db/`
- Re-run embedding if needed: `uv run src/embedding_pipeline.py`

### No results for query

- Check vector DB has chunks: run health check `curl http://localhost:8000/health`
- Try broader query terms
- Verify plugin docs were fetched: `ls vimprove-cache/chunks/plugins/`

### Plugin not found

- Add to `plugins_config.json` overrides
- Check `lazy-lock.json` has the plugin
- Verify spec files contain `owner/repo` string

### Rate limit errors

- GitHub allows 5000 req/hour with token
- Add delay between requests in `plugin_doc_fetcher.py` (increase rate_limit_delay)

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/
```

## License

MIT
