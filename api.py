#!/usr/bin/env python3
"""
Vimprove API server.
Provides query endpoint for retrieving relevant docs and generating responses.

Usage:
    export OPENROUTER_API_KEY=your_key
    uv run api.py [--port 8000] [--host 0.0.0.0]
"""

import os
from pathlib import Path
from typing import Any
import httpx

import uvicorn
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.retriever import VimproveRetriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    global retriever, openrouter_key

    cache_dir = Path(os.environ.get("VIMPROVE_CACHE_DIR", "./vimprove-cache")).resolve()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if not openrouter_key:
        print("Warning: OPENROUTER_API_KEY not set. Query endpoint will fail.")

    print(f"Loading retriever from {cache_dir}...")
    retriever = VimproveRetriever(cache_dir)
    print(f"✓ Retriever ready ({retriever.collection.count()} chunks)")

    yield  # App runs here


app = FastAPI(
    title="Vimprove API",
    description="RAG-powered Neovim configuration assistant",
    version="0.1.0",
    lifespan=lifespan,
)


# Global retriever (loaded on startup)
retriever: VimproveRetriever | None = None
openrouter_key: str | None = None


class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query about Neovim")
    context: str | None = Field(None, description="Optional config snippet for context")
    n_results: int = Field(10, ge=1, le=50, description="Number of chunks to retrieve")
    source_filter: str | None = Field(
        None, description="Filter by source (e.g., 'telescope.nvim')"
    )
    model: str = Field(
        "anthropic/claude-4.5-sonnet", description="OpenRouter model to use"
    )
    max_tokens: int = Field(
        2000, ge=100, le=4000, description="Max tokens for response"
    )


class QueryResponse(BaseModel):
    query: str
    response: str
    sources: list[dict[str, Any]]
    model_used: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "retriever_loaded": retriever is not None,
        "chunks_count": retriever.collection.count() if retriever else 0,
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the documentation and generate a response. Returns explanation + config snippet + relevant doc sections."""
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    if not openrouter_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")

    # Retrieve relevant chunks
    results = retriever.search(
        query=request.query,
        n_results=request.n_results,
        source_filter=request.source_filter,
    )

    if not results:
        raise HTTPException(status_code=404, detail="No relevant documentation found")

    # Build prompt
    prompt = build_prompt(request.query, results, request.context)

    # Call OpenRouter
    response_text = await call_openrouter(
        prompt=prompt, model=request.model, max_tokens=request.max_tokens
    )

    # Format sources for response
    sources = [
        {
            "source": r["metadata"]["source"],
            "type": r["metadata"]["type"],
            "heading": r["metadata"].get("heading"),  # vimdoc
            "tags": r["metadata"].get("tags"),  # vimdoc
            "headings": r["metadata"].get("headings"),  # markdown
            "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
            "distance": r["distance"],
        }
        for r in results[:5]  # Top 5 sources only
    ]

    return QueryResponse(
        query=request.query,
        response=response_text,
        sources=sources,
        model_used=request.model,
    )


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Streaming version of query endpoint.
    Returns Server-Sent Events with response chunks.
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    if not openrouter_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")

    # Retrieve relevant chunks
    results = retriever.search(
        query=request.query,
        n_results=request.n_results,
        source_filter=request.source_filter,
    )

    if not results:
        raise HTTPException(status_code=404, detail="No relevant documentation found")

    # Build prompt
    prompt = build_prompt(request.query, results, request.context)

    # Stream response
    async def generate():
        async for chunk in stream_openrouter(
            prompt=prompt, model=request.model, max_tokens=request.max_tokens
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def build_prompt(query: str, results: list[dict[str, Any]], context: str | None) -> str:
    """Build prompt for LLM with retrieved docs and query."""

    # Format retrieved chunks
    docs_text = "\n\n---\n\n".join(
        [
            f"**Source:** {r['metadata']['source']}\n"
            + f"**Type:** {r['metadata']['type']}\n"
            + (
                f"**Heading:** {r['metadata']['heading']}\n"
                if r["metadata"].get("heading")
                else ""
            )
            + (
                f"**Tags:** {r['metadata']['tags']}\n"
                if r["metadata"].get("tags")
                else ""
            )
            + (
                f"**Section:** {r['metadata']['headings']}\n"
                if r["metadata"].get("headings")
                else ""
            )
            + "\n"
            + r["text"]
            for r in results
        ]
    )

    context_section = ""
    if context:
        context_section = f"""## Current Config
```lua
{context}
```
"""

    prompt = f"""You are an expert Neovim configuration assistant. Answer the user's question using the provided documentation.

## Query

{query}
{context_section}

## Documentation

{docs_text}

--- 

Provide a response with:

Explanation (2-3 sentences): What the user needs to do.
Configuration (complete Lua snippet): Ready-to-use code.
Sources (1-2 key references): Where to learn more.

Keep it concise. Use idiomatic Lua (e.g., vim.keymap.set over vim.api.nvim_set_keymap).
If the docs don't fully answer the question, say so."""
    return prompt


async def call_openrouter(prompt: str, model: str, max_tokens: int) -> str:
    """Call OpenRouter API for completion."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": "https://www.github.com/rlarson20/Vimprove",
                "X-Title": "Vimprove",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenRouter API error: {response.text}",
            )

        data = response.json()
        return data["choices"][0]["message"]["content"]


async def stream_openrouter(prompt: str, model: str, max_tokens: int):
    """Stream response from OpenRouter API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": "https://www.github.com/rlarson20/Vimprove",
                "X-Title": "Vimprove",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenRouter API error: {error_text.decode()}",
                )

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break

                    # Handle empty or malformed data
                    if not data.strip():
                        continue

                    try:
                        import json

                        chunk = json.loads(data)

                        # Safely navigate the nested structure
                        if (
                            chunk.get("choices")
                            and len(chunk["choices"]) > 0
                            and chunk["choices"][0].get("delta")
                            and chunk["choices"][0]["delta"].get("content")
                        ):
                            yield chunk["choices"][0]["delta"]["content"]

                    except json.JSONDecodeError:
                        # Handle malformed JSON specifically
                        continue
                    except (KeyError, IndexError, TypeError):
                        # Handle missing keys, empty arrays, or wrong types
                        continue


def main():
    parser = argparse.ArgumentParser(description="Vimprove API server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    load_dotenv()
    uvicorn.run("api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
