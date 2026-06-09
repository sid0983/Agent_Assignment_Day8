# mcp_servers/bug_tracker_server.py
"""
MCP Server: Local Bug Tracker
=============================
A simple local bug tracker exposed as MCP tools.

Tools Exposed:
  - file_bug: Create a bug with an auto-generated ID
  - update_bug: Update status, assignee, priority, or notes
  - list_bugs: List bugs filtered by status or severity
  - bug_summary: Count bugs by component and status

Transport: stdio
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BugTracker")

PROJECT_ROOT = Path(__file__).parent.parent
BUG_DATA_DIR = PROJECT_ROOT / "bug_data"
BUGS_FILE = BUG_DATA_DIR / "bugs.json"

VALID_STATUSES = {"open", "in-progress", "resolved"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()


def load_bugs() -> list[dict[str, Any]]:
    if not BUGS_FILE.exists():
        return []
    return json.loads(BUGS_FILE.read_text(encoding="utf-8"))


def current_bugs() -> list[dict[str, Any]]:
    """Return one current record per bug ID, keeping the latest update if duplicated."""
    bugs_by_id: dict[str, dict[str, Any]] = {}
    for bug in load_bugs():
        bug_id = str(bug.get("bug_id", "")).upper()
        if not bug_id:
            continue

        existing = bugs_by_id.get(bug_id)
        if existing is None or bug.get("updated_at", "") >= existing.get("updated_at", ""):
            bugs_by_id[bug_id] = bug

    return sorted(bugs_by_id.values(), key=lambda bug: bug.get("created_at", ""))


def save_bugs(bugs: list[dict[str, Any]]) -> None:
    BUG_DATA_DIR.mkdir(parents=True, exist_ok=True)
    BUGS_FILE.write_text(json.dumps(bugs, indent=2), encoding="utf-8")


def next_bug_id(bugs: list[dict[str, Any]]) -> str:
    max_number = 0
    for bug in bugs:
        bug_id = str(bug.get("bug_id", "BUG-0"))
        if bug_id.startswith("BUG-"):
            try:
                max_number = max(max_number, int(bug_id.split("-", 1)[1]))
            except ValueError:
                continue
    return f"BUG-{max_number + 1:04d}"


def find_bug(bugs: list[dict[str, Any]], bug_id: str) -> dict[str, Any]:
    requested_id = bug_id.strip().upper()
    for bug in bugs:
        if bug["bug_id"].upper() == requested_id:
            return bug
    raise ValueError(f"Bug '{bug_id}' not found")


def validate_choice(field_name: str, value: str, allowed: set[str]) -> str:
    normalized = normalize(value)
    if normalized not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return normalized


@mcp.tool()
def file_bug(
    title: str,
    description: str,
    severity: str,
    component: str,
    priority: str = "medium",
) -> dict[str, Any]:
    """Create a new bug with an auto-generated ID.

    Args:
        title: Short bug title
        description: What is broken and how to reproduce it
        severity: low, medium, high, or critical
        component: Product area or module where the bug appears
        priority: low, medium, high, or urgent

    Returns:
        The newly created bug record.
    """
    if not title.strip():
        raise ValueError("title is required")
    if not description.strip():
        raise ValueError("description is required")
    if not component.strip():
        raise ValueError("component is required")

    bugs = load_bugs()
    now = utc_now()
    bug = {
        "bug_id": next_bug_id(bugs),
        "title": title.strip(),
        "description": description.strip(),
        "severity": validate_choice("severity", severity, VALID_SEVERITIES),
        "priority": validate_choice("priority", priority, VALID_PRIORITIES),
        "component": component.strip(),
        "status": "open",
        "assignee": None,
        "notes": [],
        "created_at": now,
        "updated_at": now,
    }

    bugs.append(bug)
    save_bugs(bugs)
    return bug


@mcp.tool()
def update_bug(
    bug_id: str,
    status: str | None = None,
    assignee: str | None = None,
    notes: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    """Update fields on an existing bug.

    Args:
        bug_id: Bug ID such as BUG-0001
        status: Optional status: open, in-progress, or resolved
        assignee: Optional person responsible for the bug
        notes: Optional note to append to the bug history
        priority: Optional priority: low, medium, high, or urgent

    Returns:
        The updated bug record.
    """
    bugs = load_bugs()
    bug = find_bug(bugs, bug_id)

    if status is not None:
        bug["status"] = validate_choice("status", status, VALID_STATUSES)
    if assignee is not None:
        bug["assignee"] = assignee.strip() or None
    if priority is not None:
        bug["priority"] = validate_choice("priority", priority, VALID_PRIORITIES)
    if notes is not None and notes.strip():
        bug["notes"].append({
            "text": notes.strip(),
            "created_at": utc_now(),
        })

    bug["updated_at"] = utc_now()
    save_bugs(bugs)
    return bug


@mcp.tool()
def list_bugs(status: str | None = None, severity: str | None = None) -> list[dict[str, Any]]:
    """List bugs, optionally filtered by status or severity.

    Args:
        status: Optional status filter: open, in-progress, or resolved
        severity: Optional severity filter: low, medium, high, or critical

    Returns:
        Matching bug records sorted by creation order.
    """
    bugs = current_bugs()
    status_filter = validate_choice("status", status, VALID_STATUSES) if status else None
    severity_filter = validate_choice("severity", severity, VALID_SEVERITIES) if severity else None

    results = []
    for bug in bugs:
        if status_filter and bug["status"] != status_filter:
            continue
        if severity_filter and bug["severity"] != severity_filter:
            continue
        results.append(bug)
    return results


@mcp.tool()
def bug_summary() -> dict[str, Any]:
    """Count open, in-progress, and resolved bugs grouped by component.

    Returns:
        Current bug counts by status and component.
    """
    status_totals = {
        "open": 0,
        "in-progress": 0,
        "resolved": 0,
    }
    by_component: dict[str, dict[str, int]] = {}

    for bug in current_bugs():
        component = bug["component"]
        status = bug["status"]
        if component not in by_component:
            by_component[component] = {
                "open": 0,
                "in-progress": 0,
                "resolved": 0,
            }
        by_component[component][status] += 1
        status_totals[status] += 1

    return {
        "status_totals": status_totals,
        "by_component": by_component,
        "total_current_bugs": sum(status_totals.values()),
        "note": "Each current bug is counted once in exactly one status.",
    }


if __name__ == "__main__":
    print("Starting Bug Tracker MCP Server...", file=sys.stderr, flush=True)
    mcp.run(transport="stdio")
