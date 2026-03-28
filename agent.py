# agent.py
"""
LangGraph + MCP Agent with Human-in-the-Loop
=============================================
A ReAct agent built with LangGraph that connects to two MCP servers
(Notes + Calculator) via langchain-mcp-adapters.

Human-in-the-Loop (HITL):
  In interactive mode, the agent pauses before every tool call and asks
  for your approval. You can approve (y) or deny (n) each tool execution.
  Denied tools return a cancellation message and the LLM adapts its answer.

Usage:
    python -X utf8 agent.py                          # interactive chat with HITL
    python -X utf8 agent.py --query "..."            # single query, no HITL
"""

import os
import sys
import asyncio
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).parent.resolve()
NOTES_SERVER = str(PROJECT_ROOT / "mcp_servers" / "notes_server.py")
CALC_SERVER  = str(PROJECT_ROOT / "mcp_servers" / "calculator_server.py")

LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.7

SYSTEM_PROMPT = """You are a helpful AI assistant with access to two sets of tools:

1. Notes Tools:
   - list_notes: List all available markdown notes
   - read_note: Read a specific note by filename
   - search_notes: Search across all notes for keywords

2. Calculator Tools:
   - add: Add two numbers
   - multiply: Multiply two numbers
   - divide: Divide two numbers
   - percentage: Calculate percentage of a value
   - summarize_numbers: Get statistics for a list of numbers

For general knowledge questions, answer directly without tools.
When asked about notes, documents, meetings, todos, or project ideas, use the Notes tools.
When asked to calculate or analyze numbers, use the Calculator tools.
You can combine tools: read a note, extract numbers, then calculate with them.
If a tool call was denied by the user, acknowledge it and answer with what you know.
Format your responses clearly with markdown when appropriate.
"""

MCP_CONFIG = {
    "notes": {
        "command": sys.executable,
        "args": [NOTES_SERVER],
        "transport": "stdio",
    },
    "calculator": {
        "command": sys.executable,
        "args": [CALC_SERVER],
        "transport": "stdio",
    },
}


async def build_agent(client: MultiServerMCPClient, checkpointer=None):
    """
    Builds the LangGraph ReAct graph.

    When a checkpointer is provided, interrupt_before=["tools"] is enabled,
    which pauses the graph before every tool execution for human review.
    """
    tools = await client.get_tools()
    print(f"\nLoaded {len(tools)} tools from MCP servers:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    model = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

    def call_model(state: MessagesState):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
        response = model.bind_tools(tools).invoke(messages)
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", tools_condition)
    builder.add_edge("tools", "call_model")

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["tools"] if checkpointer else [],
    )


async def handle_hitl_loop(graph, config: dict) -> tuple[list[str], list[str]]:
    """
    After each graph invocation, check whether the graph is paused before
    the tools node. If so, show the pending tool calls to the user and ask
    for approval. Loop until the graph reaches END.

    Returns (approved_tools, denied_tools) for summary display.
    """
    approved = []
    denied   = []

    while True:
        state = graph.get_state(config)

        if not state.next or "tools" not in state.next:
            break

        last_msg      = state.values["messages"][-1]
        pending_calls = last_msg.tool_calls

        print("\n" + "-" * 50)
        print("  [Human Review] Agent wants to call:")
        for tc in pending_calls:
            args_str = (
                ", ".join(f"{k}={repr(v)}" for k, v in tc["args"].items())
                if tc["args"] else "no args"
            )
            print(f"    - {tc['name']}({args_str})")
        print("-" * 50)

        decision = input("  Approve? (y/n): ").strip().lower()

        if decision == "y":
            for tc in pending_calls:
                approved.append(tc["name"])
            await graph.ainvoke(None, config=config)
        else:
            for tc in pending_calls:
                denied.append(tc["name"])

            # Step 1 — satisfy the graph: inject ToolMessages so every tool_call_id
            # has a matching response. as_node="tools" advances the graph past
            # the tools node without actually executing anything.
            await graph.aupdate_state(
                config,
                {
                    "messages": [
                        ToolMessage(
                            content="Denied.",
                            tool_call_id=tc["id"],
                            name=tc["name"],
                        )
                        for tc in pending_calls
                    ]
                },
                as_node="tools",
            )

            # Step 2 — inject the final reply directly as the agent's response,
            # bypassing the LLM entirely so it cannot compute the answer on its own.
            tool_names = ", ".join(f"`{tc['name']}`" for tc in pending_calls)
            await graph.aupdate_state(
                config,
                {
                    "messages": [
                        AIMessage(
                            content=(
                                f"Action blocked. You denied the {tool_names} tool(s), "
                                f"so I cannot complete this request. "
                                f"Try again and approve the tool when prompted if you'd like the result."
                            )
                        )
                    ]
                },
                as_node="call_model",
            )
            break

    return approved, denied


async def run_interactive_chat():
    print("=" * 60)
    print("  LangGraph + MCP Agent  |  Human-in-the-Loop enabled")
    print("=" * 60)
    print(f"\nNotes directory : {PROJECT_ROOT / 'notes'}")
    print(f"LLM Model       : {LLM_MODEL}")
    print("\nConnecting to MCP servers...")

    client      = MultiServerMCPClient(MCP_CONFIG)
    checkpointer = MemorySaver()
    graph       = await build_agent(client, checkpointer)

    print("\n" + "-" * 60)
    print("Agent ready! Type your questions below.")
    print("  help   - example questions")
    print("  clear  - reset conversation")
    print("  quit   - exit")
    print("-" * 60)

    # Each session gets a unique thread_id so the checkpointer stores it separately.
    # Incrementing session_id on 'clear' effectively starts a fresh conversation.
    session_id = 0

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break
        if user_input.lower() == "help":
            print_help()
            continue
        if user_input.lower() == "clear":
            session_id += 1
            print("Conversation cleared.")
            continue

        config = {"configurable": {"thread_id": f"session-{session_id}"}}

        try:
            # Pass only the new user message.
            # The checkpointer appends it to the thread's existing message history.
            await graph.ainvoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )

            approved, denied = await handle_hitl_loop(graph, config)

            final_msg = graph.get_state(config).values["messages"][-1]
            print(f"\nAgent: {final_msg.content}")

            if approved:
                print(f"\n  Approved : {', '.join(approved)}")
            if denied:
                print(f"  Denied   : {', '.join(denied)}")

        except Exception as e:
            print(f"\nError: {e}")


def print_help():
    print("""
Example Questions
-----------------

Notes:
  "What notes do I have?"
  "Read my meeting notes"
  "Search for anything about budget"
  "What are the action items from the meeting?"
  "Summarize all my project ideas"

Calculator:
  "What is 15% of 250?"
  "Calculate (45 + 32) x 8"
  "Give me statistics for: 85, 92, 78, 95, 88"

Combined (read note + calculate):
  "Read the meeting notes and calculate 15% of the $250K budget"
  "How many action items are in my todo?"

HITL demo prompts:
  "Read my meeting notes"       -> approve list_notes, deny read_note
  "What is 20% of 500?"         -> deny the percentage tool, see LLM adapt
  "Search notes for action items, then add 3 + 7"  -> approve first, deny second

Commands:
  clear  - Reset conversation memory
  help   - Show this help
  quit   - Exit
""")


async def run_single_query(query: str):
    """Single query mode — no HITL, no checkpointer."""
    print(f"\nQuery: {query}\n")

    client = MultiServerMCPClient(MCP_CONFIG)
    graph  = await build_agent(client)

    result = await graph.ainvoke({"messages": [{"role": "user", "content": query}]})

    print(f"\nResponse:\n{result['messages'][-1].content}")

    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"\nTool called: {tc['name']}({tc['args']})")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("  Run: export OPENAI_API_KEY=your_key_here")
        sys.exit(1)

    if "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            asyncio.run(run_single_query(sys.argv[idx + 1]))
        else:
            print('Usage: python agent.py --query "your question here"')
    else:
        asyncio.run(run_interactive_chat())
