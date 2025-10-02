# FIX: doesn't chunk completely, may need to just replace with markdown parser
import re


def chunk_markdown(text: str, source: str) -> list[dict[str, any]]:
    """
    Split markdown on ## headers (h2).
    Preserve h1 context and nested h3 structure.
    Keep code blocks inline with surrounding text.
    """
    chunks = []

    # Extract h1 (plugin name/title)
    h1_match = re.match(r"^#\s+(.+)$", text, re.MULTILINE)
    h1 = h1_match.group(1) if h1_match else ""

    # Split on h2 headers
    sections = re.split(r"^##\s+(.+)$", text, flags=re.MULTILINE)

    # sections[0] is text before first h2 (intro/description)
    intro = sections[0].strip()

    if intro and h1_match:
        intro = intro[h1_match.end() :].strip()  # Remove h1 from intro text

    if intro:
        chunks.append(
            {"type": "markdown", "source": source, "h1": h1, "h2": None, "text": intro}
        )
    # Process h2 sections (pairs of heading, content)
    for i in range(1, len(sections), 2):
        h2 = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if not content:
            continue
        # Split on h3 if content is large (>4000 chars)
        if len(content) > 4000:
            h3_sections = re.split(r"^###\s+(.+)$", content, flags=re.MULTILINE)
            # h3_sections[0] is content before first h3
            pre_h3 = h3_sections[0].strip()
            if pre_h3:
                chunks.append(
                    {
                        "type": "markdown",
                        "source": source,
                        "h1": h1,
                        "h2": h2,
                        "h3": None,
                        "text": pre_h3,
                    }
                )
            # Process h3 sections
            for j in range(1, len(h3_sections), 2):
                h3 = h3_sections[j].strip()
                h3_content = (
                    h3_sections[j + 1].strip() if j + 1 < len(h3_sections) else ""
                )
                if h3_content:
                    chunks.append(
                        {
                            "type": "markdown",
                            "source": source,
                            "h1": h1,
                            "h2": h2,
                            "h3": h3,
                            "text": h3_content,
                        }
                    )
        else:
            chunks.append(
                {
                    "type": "markdown",
                    "source": source,
                    "h1": h1,
                    "h2": h2,
                    "text": content,
                }
            )
    return chunks


if __name__ == "__main__":
    with open("./sample-readme.md") as f:
        chunks = chunk_markdown(f.read(), "telescope.nvim")
        __import__("pprint").pprint(chunks)
