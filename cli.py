#!/usr/bin/env python3
"""
Vimprove CLI client.

Usage:
    vimprove "How do I configure telescope?"
    vimprove "Setup LSP keymaps" --context config.lua
"""

import argparse
import sys
from pathlib import Path
import httpx
from rich.console import Console
from rich.markdown import Markdown


def main():
    parser = argparse.ArgumentParser(description="Query Vimprove API")
    parser.add_argument("query", help="Your question about Neovim")
    parser.add_argument(
        "--context", type=Path, help="Config file to include as context"
    )
    parser.add_argument(
        "--api-url", default="http://localhost:8000", help="API server URL"
    )
    parser.add_argument(
        "--model", default="anthropic/claude-3.5-sonnet", help="Model to use"
    )

    args = parser.parse_args()

    # Load context if provided
    context = None
    if args.context:
        if not args.context.exists():
            print(f"Error: Context file not found: {args.context}", file=sys.stderr)
            return 1
        context = args.context.read_text()

    # Query API
    console = Console()

    with console.status("[bold green]Querying documentation..."):
        try:
            response = httpx.post(
                f"{args.api_url}/query",
                json={"query": args.query, "context": context, "model": args.model},
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", file=sys.stderr)
            return 1

    data = response.json()

    # Display response
    console.print("\n[bold cyan]Response:[/bold cyan]\n")
    console.print(Markdown(data["response"]))

    # Display sources
    console.print("\n[bold cyan]Sources consulted:[/bold cyan]")
    for source in data["sources"]:
        console.print(f"  • {source['source']} ({source['type']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
