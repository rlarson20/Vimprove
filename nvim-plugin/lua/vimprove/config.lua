local M = {}

M.defaults = {
	-- CLI executable path
	cli_path = "uv run cli.py",

	-- API server URL
	api_url = "http://localhost:8000",

	-- Model to use
	model = "anthropic/claude-4.5-sonnet",

	-- Window config for results
	window = {
		width = 80,
		height = 30,
		border = "rounded",
	},

	-- Keybindings
	keybindings = {
		query_with_context = "<leader>vq",
		query_prompt = "<leader>vp",
	},
}

M.options = {}

function M.setup(opts)
	M.options = vim.tbl_deep_extend("force", M.defaults, opts or {})
end

return M
