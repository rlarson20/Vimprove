`uv run cli.py "How do I add a keymap for telescope find_files?"`

Response:

Explanation: To add a keymap for Telescope's find_files functionality, you'll need to create a mapping that calls the
telescope.builtin.find_files() function. This can be done using Neovim's vim.keymap.set() function. A common mapping is
"ff" (where leader is typically the space key).

Configuration:

-- Make sure you have telescope required at the top of your config
local telescope = require('telescope.builtin')

-- Add the keymap
vim.keymap.set('n', '<leader>ff', telescope.find_files, { desc = 'Find files' })

-- Alternative with options:
-- vim.keymap.set('n', '<leader>ff', function()
-- telescope.find_files({
-- hidden = true, -- Optional: include hidden files
-- no_ignore = false -- Optional: respect gitignore
-- })
-- end, { desc = 'Find files' })

                                                      References:

1 telescope.builtin.find_files() - Core function for file searching, respects .gitignore (Source: telescope.builtin
documentation)
2 telescope.builtin.fd() - An alias for find_files if you prefer that name (Source: telescope.builtin documentation)
3 For additional options and customization, see :h telescope.builtin.find_files()

Note: The documentation doesn't specify default keymaps for invoking find_files, as this is typically left to user
configuration. The example provided follows common community conventions.

Sources consulted:
• nvim-telescope/telescope.nvim (vimdoc)
• nvim-telescope/telescope.nvim (vimdoc)
• nvim-telescope/telescope.nvim (vimdoc)
• nvim-telescope/telescope.nvim (vimdoc)
• nvim-telescope/telescope.nvim (vimdoc)
