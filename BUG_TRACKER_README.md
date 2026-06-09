# LangGraph + MCP Agent: Local Bug Tracker

A separate bug tracker use case for this project. It lets a developer file bugs,
update status and ownership, set priority, list matching bugs, and get summaries
through a conversational LangGraph agent.

This demo is intentionally separate from the existing Notes + Calculator agent.

## Files

```text
langgraph-mcp-project/
|-- bug_agent.py                         # Bug tracker conversational agent
|-- run_bug_tracker.bat                  # Windows launcher
|-- mcp_servers/
|   `-- bug_tracker_server.py            # MCP server exposing bug tools
`-- bug_data/
    `-- bugs.json                        # Created automatically after first bug
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `file_bug(title, description, severity, component, priority)` | Creates a new bug with an auto-generated ID |
| `update_bug(bug_id, status, assignee, notes, priority)` | Updates status, assignee, priority, or appends notes |
| `list_bugs(status, severity)` | Lists bugs, optionally filtered by status or severity |
| `bug_summary()` | Counts open, in-progress, and resolved bugs by component |

## Valid Values

Statuses:

```text
open
in-progress
resolved
```

Severities:

```text
low
medium
high
critical
```

Priorities:

```text
low
medium
high
urgent
```

## Setup

Use the same environment as the main project.

Install dependencies if needed:

```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

Make sure your `.env` file contains a real OpenAI API key:

```env
OPENAI_API_KEY=sk-your-real-key-here
LLM_MODEL=gpt-4o-mini
```

## Run

Interactive mode:

```powershell
.\run_bug_tracker.bat
```

Interactive mode has Human-in-the-Loop enabled. Before any bug tracker MCP tool
runs, the agent shows the pending tool call and asks you to approve or deny it.

Single-query mode:

```powershell
.\run_bug_tracker.bat --query "List all open bugs."
```

## Example Prompts

File a bug:

```text
File a critical checkout bug: payment fails after submitting card details.
Component: payments. Priority urgent.
```

Update a bug:

```text
Assign BUG-0001 to Priya and mark it in-progress.
```

Add notes:

```text
Add a note to BUG-0001: reproduced on Windows with Chrome.
```

Resolve a bug:

```text
Mark BUG-0001 resolved.
```

Query bugs:

```text
List all open bugs.
Show high severity bugs.
Give me a bug summary by component.
```

## Data Storage

Bug records are stored locally as JSON:

```text
bug_data/bugs.json
```

The file is created automatically the first time you file a bug. Each bug record
includes an ID, title, description, severity, priority, component, status,
assignee, notes, and timestamps.

## Demo Flow

1. Start the bug tracker agent.
2. File one or two bugs with different components and severities.
3. Assign a bug and move it to `in-progress`.
4. Resolve one bug.
5. Ask for a summary by component.
6. Deny one proposed tool call to show the HITL blocking behavior.

Example:

```text
You: File a high severity login bug: users get a blank page after sign in. Component: auth. Priority high.
Agent: Created BUG-0001...

You: Assign BUG-0001 to Asha and mark it in-progress.
Agent: Updated BUG-0001...

You: Give me a bug summary by component.
Agent: ...
```

## Human-in-the-Loop

HITL is enabled in `bug_agent.py` for interactive mode. The LangGraph app uses a
checkpointer and `interrupt_before=["tools"]`, so every MCP tool call pauses
before execution.

Approval example:

```text
You: List all open bugs.

[Human Review] Agent wants to call:
  - list_bugs(status='open')
Approve tool call(s)? (y/n): y

Agent: ...
Approved : list_bugs
```

Denial example:

```text
You: Mark BUG-0001 resolved.

[Human Review] Agent wants to call:
  - update_bug(bug_id='BUG-0001', status='resolved')
Approve tool call(s)? (y/n): n

Agent: Action blocked. You denied the `update_bug` tool call(s), so I did not
change or read the bug tracker data for that request.
Denied   : update_bug
```
