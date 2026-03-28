# mcp_servers/notes_server.py
"""
MCP Server: Notes Manager
=========================
A simple MCP server that exposes local markdown notes to AI agents.
Built with FastMCP from the official MCP Python SDK.

Tools Exposed:
  - list_notes: List all available markdown notes with metadata
  - read_note: Read the full contents of a specific note
  - search_notes: Search notes by keyword across all files

Transport: stdio (launched as subprocess by MCP client)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# ─── Initialize MCP Server ───────────────────────────────────────────
mcp = FastMCP("NotesManager")

# ─── Configuration ────────────────────────────────────────────────────
# Notes directory - relative to project root
NOTES_DIR = Path(__file__).parent.parent / "notes"


# ─── Tool: List Notes ─────────────────────────────────────────────────
@mcp.tool()
def list_notes() -> list[dict]:
    """List all available markdown notes with metadata.

    Returns a list of dictionaries containing:
      - filename: Name of the markdown file
      - size_bytes: File size in bytes
      - last_modified: Last modification timestamp
    """
    notes = []
    for filepath in sorted(NOTES_DIR.glob("*.md")):
        stat = filepath.stat()
        notes.append({
            "filename": filepath.name,
            "size_bytes": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return notes


# ─── Tool: Read Note ──────────────────────────────────────────────────
@mcp.tool()
def read_note(filename: str) -> str:
    """Read the full contents of a specific markdown note.

    Args:
        filename: Name of the markdown file to read (e.g., 'meeting_notes.md')

    Returns:
        The full text content of the note.

    Raises:
        ValueError: If path traversal is detected
        FileNotFoundError: If the note doesn't exist
    """
    # Security: Prevent path traversal attacks
    safe_path = (NOTES_DIR / filename).resolve()
    if not str(safe_path).startswith(str(NOTES_DIR.resolve())):
        raise ValueError("Access denied: path traversal detected")

    if not safe_path.exists():
        raise FileNotFoundError(f"Note '{filename}' not found")

    if not safe_path.suffix == ".md":
        raise ValueError("Only markdown (.md) files are supported")

    return safe_path.read_text(encoding="utf-8")


# ─── Tool: Search Notes ───────────────────────────────────────────────
@mcp.tool()
def search_notes(query: str) -> list[dict]:
    """Search across all notes for a keyword or phrase.

    Performs case-insensitive search across all markdown files.

    Args:
        query: The search term or phrase to look for

    Returns:
        List of matches with filename and matching line excerpts.
    """
    results = []
    query_lower = query.lower()

    for filepath in sorted(NOTES_DIR.glob("*.md")):
        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")
        matching_lines = []

        for i, line in enumerate(lines, 1):
            if query_lower in line.lower():
                matching_lines.append({
                    "line_number": i,
                    "text": line.strip(),
                })

        if matching_lines:
            results.append({
                "filename": filepath.name,
                "matches": matching_lines,
                "total_matches": len(matching_lines),
            })

    return results


# ─── Entry Point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Notes MCP Server...", file=sys.stderr, flush=True)
    mcp.run(transport="stdio")
