# mcp_servers/calculator_server.py
"""
MCP Server: Smart Calculator
=============================
An MCP server that exposes mathematical operations to AI agents.
Demonstrates numeric tool capabilities alongside the Notes server.

Tools Exposed:
  - add: Add two numbers
  - multiply: Multiply two numbers
  - divide: Divide two numbers (with zero-check)
  - percentage: Calculate percentage of a value
  - summarize_numbers: Get statistical summary of a list of numbers

Transport: stdio
"""

import math
import sys
from mcp.server.fastmcp import FastMCP

# ─── Initialize MCP Server ───────────────────────────────────────────
mcp = FastMCP("Calculator")


# ─── Tool: Add ────────────────────────────────────────────────────────
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b.
    """
    return a + b


# ─── Tool: Multiply ──────────────────────────────────────────────────
@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b.
    """
    return a * b


# ─── Tool: Divide ────────────────────────────────────────────────────
@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide the first number by the second.

    Args:
        a: Numerator
        b: Denominator (must not be zero)

    Returns:
        The result of a / b.

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


# ─── Tool: Percentage ────────────────────────────────────────────────
@mcp.tool()
def percentage(value: float, percent: float) -> float:
    """Calculate a percentage of a value.

    Example: percentage(200, 15) returns 30.0 (15% of 200)

    Args:
        value: The base value
        percent: The percentage to calculate

    Returns:
        The percentage amount.
    """
    return (value * percent) / 100


# ─── Tool: Summarize Numbers ─────────────────────────────────────────
@mcp.tool()
def summarize_numbers(numbers: list[float]) -> dict:
    """Get a statistical summary of a list of numbers.

    Args:
        numbers: A list of numeric values to analyze

    Returns:
        Dictionary with count, sum, mean, min, max, and std_dev.
    """
    if not numbers:
        raise ValueError("List cannot be empty")

    n = len(numbers)
    total = sum(numbers)
    mean = total / n
    min_val = min(numbers)
    max_val = max(numbers)

    # Standard deviation
    variance = sum((x - mean) ** 2 for x in numbers) / n
    std_dev = math.sqrt(variance)

    return {
        "count": n,
        "sum": round(total, 2),
        "mean": round(mean, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "std_dev": round(std_dev, 2),
    }


# ─── Entry Point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Calculator MCP Server...", file=sys.stderr, flush=True)
    mcp.run(transport="stdio")
