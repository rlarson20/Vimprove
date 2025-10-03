from markdown_it import MarkdownIt
import pathlib


def chunk_markdown(text: str, source: str) -> list[dict[str, any]]:
    """
    Parse markdown with markdown-it-py, chunk on heading boundaries.

    Improvements:
    - Deduplicate list processing
    - Skip HTML and image references
    - Proper heading hierarchy tracking
    - Better code block handling
    """
    md = MarkdownIt()
    tokens = md.parse(text)

    chunks = []
    heading_stack = []
    current_text_parts = []

    # Track which tokens we've already processed to avoid duplication
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Heading: save previous chunk, update stack
        if token.type == "heading_open":
            # Save accumulated text
            if current_text_parts:
                text_content = "\n".join(current_text_parts).strip()
                if text_content:
                    chunks.append(
                        {
                            "type": "markdown",
                            "source": source,
                            "headings": heading_stack.copy(),
                            "text": text_content,
                        }
                    )
                current_text_parts = []

            # Extract heading level and text
            level = int(token.tag[1])
            i += 1
            heading_text = ""
            if i < len(tokens) and tokens[i].type == "inline":
                heading_text = extract_inline_text(tokens[i])

            # Update heading stack (truncate to current level - 1, then append)
            heading_stack = heading_stack[: level - 1] + [heading_text]

            # Skip heading_close
            i += 2
            continue

        # Paragraph
        elif token.type == "paragraph_open":
            i += 1
            if i < len(tokens) and tokens[i].type == "inline":
                text = extract_inline_text(tokens[i])
                if text.strip():
                    current_text_parts.append(text)
            i += 2  # Skip inline and paragraph_close
            continue

        # Code block / fence
        elif token.type == "fence" or token.type == "code_block":
            lang = getattr(token, "info", "") or ""
            code = token.content.rstrip("\n")
            current_text_parts.append(f"```{lang}\n{code}\n```")
            i += 1
            continue

        # Lists - process the list items, not the container
        elif token.type == "bullet_list_open" or token.type == "ordered_list_open":
            i += 1
            list_text = []

            # Process list items
            while i < len(tokens) and tokens[i].type == "list_item_open":
                i += 1
                item_parts = []

                # Collect all content in this list item
                while i < len(tokens) and tokens[i].type != "list_item_close":
                    if tokens[i].type == "paragraph_open":
                        i += 1
                        if tokens[i].type == "inline":
                            item_text = extract_inline_text(tokens[i])
                            item_parts.append(item_text)
                        i += 2  # Skip inline and paragraph_close
                    else:
                        i += 1

                if item_parts:
                    list_text.append(" ".join(item_parts))

                i += 1  # Skip list_item_close

            if list_text:
                current_text_parts.append("\n".join(list_text))

            i += 1  # Skip list_close
            continue

        # HTML blocks and inline HTML - skip
        elif token.type in ["html_block", "html_inline"]:
            i += 1
            continue

        # Everything else
        else:
            i += 1

    # Save final chunk
    if current_text_parts:
        text_content = "\n".join(current_text_parts).strip()
        if text_content:
            chunks.append(
                {
                    "type": "markdown",
                    "source": source,
                    "headings": heading_stack,
                    "text": text_content,
                }
            )

    return chunks


def extract_inline_text(token) -> str:
    """
    Extract plain text from inline token, skipping images and complex formatting.
    """
    if not token.children:
        return token.content

    parts = []
    for child in token.children:
        if child.type == "text":
            parts.append(child.content)
        elif child.type == "code_inline":
            parts.append(f"`{child.content}`")
        elif child.type == "softbreak" or child.type == "hardbreak":
            parts.append("\n")
        elif child.type == "link_open":
            # We'll capture the link text from subsequent tokens
            continue
        elif child.type == "link_close":
            continue
        elif child.type == "image":
            # Skip images entirely
            continue
        # Recursively handle nested inlines
        elif hasattr(child, "children") and child.children:
            parts.append(extract_inline_text(child))

    return "".join(parts)


if __name__ == "__main__":
    readme_path = pathlib.Path("../sample-lazy-readme.md")  # Your sample file
    readme_text = readme_path.read_text()

    chunks = chunk_markdown(readme_text, "folke/lazy.nvim")

    import json

    for chunk in chunks:
        print(json.dumps(chunk, indent=2))
        print()
