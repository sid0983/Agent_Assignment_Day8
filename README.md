# LangGraph + MCP Agent: Notes & Calculator

A LangGraph ReAct agent that connects to two local MCP (Model Context Protocol) servers — one for reading markdown notes and one for math operations. Demonstrates how to build a tool-using AI agent with a multi-turn chat interface.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Setup & Installation](#setup--installation)
3. [How to Run](#how-to-run)
4. [Architecture Overview](#architecture-overview)
5. [Component Breakdown](#component-breakdown)
   - [MCP Servers](#mcp-servers)
   - [MCP Client](#mcp-client)
   - [Agent Framework (LangGraph)](#agent-framework-langgraph)
   - [Chat System](#chat-system)
   - [Conversation Memory](#conversation-memory)
6. [Example Interactions](#example-interactions)
7. [Human-in-the-Loop](#human-in-the-loop)
8. [Extending the Project](#extending-the-project)

---

## Project Structure

```
langgraph-mcp-project/
├── agent.py                   # Main entry point — LangGraph agent + chat loop
├── requirements.txt           # Python dependencies
├── run.bat                    # Windows launch script (handles UTF-8)
├── README.md                  # This file
│
├── mcp_servers/
│   ├── notes_server.py        # MCP server exposing notes tools
│   └── calculator_server.py   # MCP server exposing math tools
│
└── notes/                     # Sample markdown notes (agent's data)
    ├── meeting_notes.md
    ├── project_ideas.md
    └── todo.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11 or higher
- An OpenAI API key

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

If you already have an older LangChain ecosystem installed, upgrade to the 1.x versions:

```bash
pip install "langgraph>=1.0.0" "langchain-openai>=1.0.0" "langchain>=1.0.0" "langchain-mcp-adapters>=0.1.0" "mcp[cli]>=1.2.0"
```

### Step 2: Configure Your API Key

The project reads the key from a `.env` file or environment variable.

**Option A — .env file** (recommended):

```
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
```

**Option B — Environment variable**:

```bash
# macOS / Linux
export OPENAI_API_KEY=sk-your-key-here

# Windows CMD
set OPENAI_API_KEY=sk-your-key-here

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-your-key-here"
```

---

## How to Run

### Interactive chat (recommended for demo)

```bash
# Windows — use run.bat or this command:
python -X utf8 agent.py

# macOS / Linux
python agent.py
```

The `-X utf8` flag is required on Windows to prevent encoding errors from special characters in terminal output.

### Single query mode (quick test)

```bash
python -X utf8 agent.py --query "What notes do I have?"
```

### In-chat commands

| Command | Action                          |
|---------|---------------------------------|
| `help`  | Show example questions          |
| `clear` | Reset conversation history      |
| `quit`  | Exit the agent                  |

---

## Architecture Overview

```
User Input
    |
    v
+-------------------+
|   agent.py        |   <-- LangGraph state machine (ReAct loop)
|                   |
|  call_model node  |   <-- sends messages to GPT-4o-mini
|       |           |
|  tools_condition  |   <-- decides: need a tool? yes/no
|       |           |
|  tools node       |   <-- executes MCP tool calls
+-------------------+
    |           |
    v           v
Notes MCP    Calculator MCP
Server       Server
(stdio)      (stdio)
```

The agent loops — Reason, Act, Observe — until the LLM has enough information to give a final answer.

---

## Component Breakdown

### MCP Servers

**What is MCP?**
MCP (Model Context Protocol) is an open standard for connecting tools and data sources to AI agents. Each MCP server is a standalone Python process that exposes a set of typed functions (called tools) over a defined transport.

**Notes Server** (`mcp_servers/notes_server.py`)

Provides three tools for reading local markdown files:

| Tool          | What it does                                            |
|---------------|---------------------------------------------------------|
| `list_notes`  | Lists all `.md` files in `notes/` with size and date   |
| `read_note`   | Returns the full text of a specific note by filename    |
| `search_notes`| Case-insensitive keyword search across all notes        |

Security: The server validates file paths to block path traversal attacks (`../../etc/passwd`). Only `.md` files are accessible.

**Calculator Server** (`mcp_servers/calculator_server.py`)

Provides five math tools:

| Tool               | What it does                                         |
|--------------------|------------------------------------------------------|
| `add`              | Adds two numbers                                     |
| `multiply`         | Multiplies two numbers                               |
| `divide`           | Divides two numbers (raises error on divide-by-zero) |
| `percentage`       | Calculates X% of a value                            |
| `summarize_numbers`| Returns count, sum, mean, min, max, std_dev          |

Both servers are built with **FastMCP** — a decorator-based framework from the official MCP Python SDK. Adding a tool is as simple as decorating a Python function:

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("MyServer")

@mcp.tool()
def my_tool(param: str) -> str:
    """Description the LLM reads to decide when to call this tool."""
    return f"result for {param}"

mcp.run(transport="stdio")
```

Both servers use **stdio transport** — they run as child processes launched by the MCP client, communicating via stdin/stdout. No network port is opened.

---

### MCP Client

**File:** `agent.py` — the `MultiServerMCPClient` block

The MCP client (`langchain-mcp-adapters`) is responsible for:

1. Launching both MCP server subprocesses
2. Discovering all tools they expose (via `get_tools()`)
3. Converting those tools into LangChain-compatible `BaseTool` objects
4. Routing tool call requests from the agent to the correct server at runtime

```python
client = MultiServerMCPClient({
    "notes": {
        "command": sys.executable,      # python interpreter
        "args": ["mcp_servers/notes_server.py"],
        "transport": "stdio",
    },
    "calculator": {
        "command": sys.executable,
        "args": ["mcp_servers/calculator_server.py"],
        "transport": "stdio",
    },
})

tools = await client.get_tools()   # returns 8 tools total (3 + 5)
```

The `langchain-mcp-adapters` library acts as a bridge — it speaks MCP protocol to the servers and speaks LangChain's tool interface to the agent. This means any MCP-compatible server can be plugged in without changing the agent code.

---

### Agent Framework (LangGraph)

**File:** `agent.py` — the `build_agent()` function

LangGraph is used to build a **ReAct agent** as a state machine. The state is a list of messages (`MessagesState`). The graph has two nodes:

| Node         | Role                                                                 |
|--------------|----------------------------------------------------------------------|
| `call_model` | Sends the message history to GPT-4o-mini and gets a response        |
| `tools`      | Executes any tool calls the LLM included in its response            |

The edges control flow:

```
START --> call_model
              |
         tools_condition
         /            \
    (tool call)    (no tool call)
        |                |
      tools             END
        |
    call_model  (loops back)
```

`tools_condition` is a built-in LangGraph helper that checks whether the LLM's last message contains tool calls. If yes, routes to `tools`. If no, routes to `END`.

This loop is the **ReAct pattern** (Reason + Act):
- The LLM reasons about what it needs
- It acts by calling a tool
- It observes the result (tool output is appended to message history)
- It reasons again with that new information
- Repeats until it can answer without calling any more tools

---

### Chat System

**File:** `agent.py` — the `run_interactive_chat()` function

The chat loop works as follows:

1. User types a message
2. The message is appended to `conversation_history` (a Python list)
3. `graph.ainvoke({"messages": conversation_history})` is called — the full history is passed in every time
4. LangGraph runs the ReAct loop internally until a final answer is produced
5. The final assistant message is extracted and printed
6. The assistant's response is appended to `conversation_history`
7. Loop repeats

The LLM sees the full conversation history on every turn, which is how it understands follow-up questions and context from earlier in the session.

---

### Conversation Memory

**What memory exists in this project:**

This project uses **in-process, session-scoped memory** only. The `conversation_history` list in `run_interactive_chat()` acts as a rolling message buffer — the LLM sees all prior messages in every request.

| Property         | Details                                              |
|------------------|------------------------------------------------------|
| Type             | In-memory Python list (no database, no vector store) |
| Scope            | Single session only — wiped when the process exits   |
| Mechanism        | Full message history passed to LLM on every call     |
| Limit            | No truncation — grows until the LLM context window fills |
| Persistence      | None — no disk storage, no LangGraph checkpointer    |

**What this means for demos:**
- The agent remembers everything said earlier in the conversation
- Asking "what did I just ask you?" works fine
- Restarting the process starts fresh
- There is no long-term memory between sessions

**What is NOT present:**
- No `MemorySaver` or `SqliteSaver` checkpointer
- No vector store / semantic search over past conversations
- No summarization of old messages
- No user profile or preference storage

---

## Example Interactions

```
You: What notes do I have?
Agent: You have 3 notes: meeting_notes.md, project_ideas.md, todo.md
  Tools used: list_notes

You: Read the meeting notes
Agent: [returns full content of meeting_notes.md]
  Tools used: list_notes, read_note

You: What is 15% of the $250K budget from those notes?
Agent: 15% of $250,000 is $37,500
  Tools used: percentage

You: Search for anything about action items
Agent: [returns matching lines from all notes]
  Tools used: search_notes
```

---

## Human-in-the-Loop

**Can Human-in-the-Loop (HITL) be added to this project? Yes — LangGraph has built-in support for it.**

### What HITL means here

Instead of the agent automatically executing every tool call, the graph pauses before running a tool and asks the human: "The agent wants to call `read_note(meeting_notes.md)` — approve or cancel?"

### How LangGraph supports this

LangGraph's HITL mechanism requires two additions:

1. **A checkpointer** — saves graph state between interruptions so it can be resumed
2. **`interrupt_before=["tools"]`** in `graph.compile()` — pauses the graph before the `tools` node runs

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

checkpointer = MemorySaver()
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"]   # pause here and wait for human
)

# First invoke — runs until the interrupt
config = {"configurable": {"thread_id": "session-1"}}
result = graph.invoke({"messages": [...]}, config=config)

# Inspect pending tool calls
pending = result["messages"][-1].tool_calls
print(f"Agent wants to call: {pending[0]['name']}({pending[0]['args']})")

# Human approves: resume normally
graph.invoke(Command(resume=None), config=config)

# Human rejects: resume with a modified state or cancel message
graph.invoke(Command(resume="User cancelled this tool call"), config=config)
```

### What you can demonstrate with HITL

- Show the agent pausing mid-task and listing what tool it intends to call
- Approve it and show the result appearing
- Deny it and show the agent adapting its response
- Approve some tool calls but not others in a multi-step task

### Current state of this project

The current code does not include a checkpointer, so HITL is not active. Adding it requires modifying only `build_agent()` in `agent.py` and updating the chat loop in `run_interactive_chat()` to handle the interrupt/resume cycle. The MCP servers and graph structure do not need to change.

---

## Extending the Project

### Add a new MCP server

1. Create `mcp_servers/my_server.py` with `@mcp.tool()` decorated functions
2. Add it to the `MultiServerMCPClient` config in `agent.py`

### Switch LLM

```python
# Anthropic Claude
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-opus-4-6")

# Local Ollama
from langchain_ollama import ChatOllama
model = ChatOllama(model="llama3.2")
```

### Switch to remote MCP servers (HTTP transport)

```python
"my_remote_server": {
    "transport": "http",
    "url": "http://remote-host:8000/mcp",
    "headers": {"Authorization": "Bearer YOUR_TOKEN"},
}
```

---

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [FastMCP Documentation](https://gofastmcp.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Human-in-the-Loop Guide](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
