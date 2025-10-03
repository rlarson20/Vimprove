" Only load once
if exists('g:loaded_vimprove')
  finish
endif
let g:loaded_vimprove = 1

" Main command
command! -nargs=1 Vimprove lua require('vimprove').query(<q-args>)
command! -nargs=0 VimproveContext lua require('vimprove').query_with_context()

" Optional: Default keybinding
nnoremap <leader>vq :lua require('vimprove').query_with_context()<CR>
