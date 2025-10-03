import json
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


def chunk_markdown(text: str, source: str) -> list[dict[str, any]]:
    """
    Parse markdown using markdown-it-py, chunk on heading boundaries.
    Preserve heading hierarchy and all content types (code, lists, etc).
    """
    md = MarkdownIt()
    tokens = md.parse(text)
    tree = SyntaxTreeNode(tokens)

    chunks = []
    heading_stack = []
    current_text_parts = []

    def extract_text_from_token(token: SyntaxTreeNode) -> str:
        """Recursively extract text content from a token."""
        if token.type == "text":
            return token.content
        elif token.type == "code_inline":
            return f"`{token.content}`"
        elif token.type == "code_block" or token.type == "fence":
            lang = getattr(token, "info", "")
            return f"\n```{lang}\n{token.content}```\n"
        elif hasattr(token, "children") and token.children:
            return "".join(extract_text_from_token(child) for child in token.children)
        return ""

    def process_node(node: SyntaxTreeNode):
        nonlocal heading_stack, current_text_parts

        # Handle heading nodes
        if node.type == "heading":
            # Save previous chunk if it has content
            if current_text_parts:
                text = "\n".join(current_text_parts).strip()
                if text:
                    chunks.append(
                        {
                            "type": "markdown",
                            "source": source,
                            "headings": heading_stack.copy(),
                            "text": text,
                        }
                    )
                current_text_parts = []

            # Update heading stack
            level = int(node.tag[1])  # h1 -> 1, h2 -> 2, etc.
            heading_text = extract_text_from_token(node)
            heading_stack = heading_stack[: level - 1] + [heading_text]

        # Handle content nodes
        elif node.type in ["paragraph", "blockquote", "list_item"]:
            content = extract_text_from_token(node)
            if content.strip():
                current_text_parts.append(content)

        elif node.type in ["fence", "code_block"]:
            content = extract_text_from_token(node)
            current_text_parts.append(content)

        elif node.type == "bullet_list" or node.type == "ordered_list":
            # Lists are handled via their items, but add spacing
            if current_text_parts and current_text_parts[-1] != "":
                current_text_parts.append("")

        # Recurse into children
        for child in node.children:
            process_node(child)

    # Walk the tree
    for child in tree.children:
        process_node(child)

    # Save final chunk
    if current_text_parts:
        text = "\n".join(current_text_parts).strip()
        if text:
            chunks.append(
                {
                    "type": "markdown",
                    "source": source,
                    "headings": heading_stack,
                    "text": text,
                }
            )

    return chunks


if __name__ == "__main__":
    with open("./sample-readme.md") as f:
        chunks = chunk_markdown(f.read(), "telescope.nvim")
        __import__("pprint").pprint(chunks)

        sample = """# telescope.nvim
                    Fuzzy finder for neovim.

                    ## Installation

                    Using lazy.nvim:
                    ```lua
                    { 'nvim-telescope/telescope.nvim' }
                    Usage
                    Finding files
                    Use :Telescope find_files.
                    Live grep
                    Search contents with :Telescope live_grep.
                    """
        chunks = chunk_markdown(sample, "telescope.nvim")
        for chunk in chunks:
            print(json.dumps(chunk, indent=2))
