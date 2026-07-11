#!/usr/bin/env python3
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import hindsight

mcp = FastMCP("graphiti-memory")


@mcp.tool()
def retain() -> str:
    """Ingest new trace entries into HINDSIGHT memory."""
    return "retained" if hindsight.retain() == 0 else "retain failed"


@mcp.tool()
def bootstrap() -> str:
    """Rebuild memory from the complete trace corpus."""
    return "bootstrapped" if hindsight.bootstrap() == 0 else "bootstrap failed"


@mcp.tool()
def recall(query: str, limit: int = 6) -> str:
    """Retrieve relevant memories for a query."""
    return hindsight._render_recall(query, limit)


@mcp.tool()
def observe() -> str:
    """Generate neutral observation summaries."""
    return "observed" if hindsight.observe() == 0 else "observe failed"


@mcp.tool()
def reflect(query: str, limit: int = 6) -> str:
    """Generate a reflective answer and a new opinion candidate."""
    return hindsight._render_reflect(query, limit)


@mcp.tool()
def reinforce(prior: float, supports: bool, learning_rate: float = 0.2) -> float:
    """Update opinion confidence deterministically."""
    return hindsight.reinforce(prior, supports, learning_rate)


if __name__ == "__main__":
    mcp.run(transport="stdio")
