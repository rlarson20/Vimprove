return {
	"your-username/vimprove.nvim",
	dir = "~/path/to/Vimprove/nvim-plugin", -- Local development
	config = function()
		require("vimprove").setup({
			cli_path = "uv run ~/path/to/Vimprove/cli.py",
			api_url = "http://localhost:8000",
			model = "anthropic/claude-4.5-sonnet",
		})
	end,
	-- Lazy load on command
	cmd = { "Vimprove", "VimproveContext" },
}
