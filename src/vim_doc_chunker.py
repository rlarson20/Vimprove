import pprint
import re
from typing import Any


def chunk_vimdoc(text: str, source: str) -> list[dict[str, Any]]:
    """
    Split vimdoc on section delimiters (==== or ----).
    Extract heading, tags, and body for each section.
    Sub-chunk if body exceeds ~1000 tokens (4000 chars heuristic).
    """
    section_pattern = r"^[=]{10,}$|^[-]{10,}$"
    parts = re.split(section_pattern, text, flags=re.MULTILINE)

    chunks = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n")
        # first non-empty line usually heading
        heading = ""
        heading_idx = 0
        for i, line in enumerate(lines):
            if line.strip():
                heading = line.strip()
                heading_idx = i
                break
        # Extract tags from heading line (pattern: *tag-name*)
        tags = re.findall(r"\*([^*]+)\*", heading)

        # body after heading
        body_lines = lines[heading_idx + 1 :]
        body = "\n".join(body_lines).strip()

        # sub-chunk
        if len(body) > 4000:
            # Split on subsection markers (word followed by ~) or double newlines
            subsections = re.split(r"\n\n+|\n[A-Z].*?~\n", body)
            for sub in subsections:
                sub = sub.strip()
                if len(sub) < 100:  # Skip tiny fragments
                    continue
                chunks.append(
                    {
                        "type": "vimdoc",
                        "source": source,
                        "heading": heading,
                        "tags": tags,
                        "text": sub,
                    }
                )
        else:
            chunks.append(
                {
                    "type": "vimdoc",
                    "source": source,
                    "heading": heading,
                    "tags": tags,
                    "text": body,
                }
            )

    return chunks


if __name__ == "__main__":
    with open("./sample-vimdoc.txt") as f:
        chunks = chunk_vimdoc(f.read(), "sample")
        pprint.pprint(chunks)
