# telescope.nvim

Highly extendable fuzzy finder over lists.

## Installation

Using lazy.nvim:

```lua
{ 'nvim-telescope/telescope.nvim', dependencies = { 'nvim-lua/plenary.nvim' } }
```

## Usage

### Finding files

Use `:Telescope find_files` to search for files in your project.

### Live grep

Use `:Telescope live_grep` to search file contents.
