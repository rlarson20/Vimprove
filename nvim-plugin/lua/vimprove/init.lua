local M = {}
local config = require("vimprove.config")

-- Get current buffer context (selected text or entire buffer)
local function get_context()
	local mode = vim.fn.mode()

	-- If in visual mode, get selected text
	if mode == "v" or mode == "V" or mode == "" then
		local start_pos = vim.fn.getpos("'<")
		local end_pos = vim.fn.getpos("'>")
		local lines = vim.fn.getline(start_pos[2], end_pos[2])
		return table.concat(lines, "\n")
	end

	-- Otherwise, get entire buffer
	local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
	return table.concat(lines, "\n")
end

-- Execute CLI command and capture output
local function execute_query(query, context)
	-- Strip quotes from query if present
	query = query:gsub('^"(.*)"$', "%1"):gsub("^'(.*)'$", "%1")

	-- Expand cli_path
	local cli_cmd = vim.fn.expand(config.options.cli_path)

	-- Build command string with proper escaping
	local cmd_parts = {
		cli_cmd,
		vim.fn.shellescape(query),
		"--api-url",
		vim.fn.shellescape(config.options.api_url),
		"--model",
		vim.fn.shellescape(config.options.model),
	}

	-- Add context as temp file if provided
	local context_file = nil
	if context and context ~= "" then
		context_file = vim.fn.tempname() .. ".lua"
		local file = io.open(context_file, "w")
		if file then
			file:write(context)
			file:close()
			table.insert(cmd_parts, "--context")
			table.insert(cmd_parts, vim.fn.shellescape(context_file))
		else
			vim.notify("Failed to create temp file for context", vim.log.levels.WARN)
		end
	end

	local full_cmd = table.concat(cmd_parts, " ")

	-- Debug: print the command
	vim.notify("Executing: " .. full_cmd, vim.log.levels.DEBUG)

	-- Execute and capture output
	local output = vim.fn.system(full_cmd)
	local exit_code = vim.v.shell_error

	-- Clean up temp file
	if context_file then
		os.remove(context_file)
	end

	if exit_code ~= 0 then
		return nil, "Error: " .. output
	end

	return output, nil
end

-- Display results in floating window
local function show_results(content)
	local buf = vim.api.nvim_create_buf(false, true)

	-- Set buffer content (split by newlines)
	local lines = vim.split(content, "\n")
	vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)

	-- Set buffer options
	vim.api.nvim_buf_set_option(buf, "bufhidden", "wipe")
	vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
	vim.api.nvim_buf_set_option(buf, "modifiable", false)

	-- Calculate window size
	local width = config.options.window.width
	local height = config.options.window.height
	local ui = vim.api.nvim_list_uis()[1]

	local win_opts = {
		relative = "editor",
		width = width,
		height = height,
		col = math.floor((ui.width - width) / 2),
		row = math.floor((ui.height - height) / 2),
		style = "minimal",
		border = config.options.window.border,
	}

	local win = vim.api.nvim_open_win(buf, true, win_opts)

	-- Set window options
	vim.api.nvim_win_set_option(win, "wrap", true)
	vim.api.nvim_win_set_option(win, "linebreak", true)

	-- Key mapping to close window
	vim.api.nvim_buf_set_keymap(buf, "n", "q", ":close<CR>", { noremap = true, silent = true })
	vim.api.nvim_buf_set_keymap(buf, "n", "<Esc>", ":close<CR>", { noremap = true, silent = true })
end

-- Main query function
function M.query(query_text)
	if not query_text or query_text == "" then
		vim.notify("Error: Empty query", vim.log.levels.ERROR)
		return
	end

	vim.notify("Querying Vimprove...", vim.log.levels.INFO)

	local output, err = execute_query(query_text, nil)

	if err then
		vim.notify(err, vim.log.levels.ERROR)
		return
	end

	show_results(output)
end

-- Query with current buffer/selection as context
function M.query_with_context()
	-- Prompt for query
	local query = vim.fn.input("Vimprove query: ")

	if query == "" then
		return
	end

	-- Get context
	local context = get_context()

	vim.notify("Querying Vimprove with context...", vim.log.levels.INFO)

	local output, err = execute_query(query, context)

	if err then
		vim.notify(err, vim.log.levels.ERROR)
		return
	end

	show_results(output)
end

-- Setup function for user configuration
function M.setup(opts)
	config.setup(opts)

	-- Apply keybindings
	if config.options.keybindings.query_with_context then
		vim.keymap.set("n", config.options.keybindings.query_with_context, function()
			M.query_with_context()
		end, { desc = "Vimprove: Query with context" })
	end

	if config.options.keybindings.query_prompt then
		vim.keymap.set("n", config.options.keybindings.query_prompt, function()
			local query = vim.fn.input("Vimprove query: ")
			if query ~= "" then
				M.query(query)
			end
		end, { desc = "Vimprove: Query (no context)" })
	end
end

return M
