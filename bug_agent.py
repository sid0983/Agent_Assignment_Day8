# bug_agent.py
"""
LangGraph + MCP Agent: Local Bug Tracker
========================================
A separate conversational agent for filing, updating, listing, and
summarizing bugs through the Bug Tracker MCP server.

Usage:
    python -X utf8 bug_agent.py
    python -X utf8 bug_agent.py --query "File a high severity bug in checkout..."
"""

import asyncio
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

PROJECT_ROOT = Path(__file__).parent.resolve()
BUG_SERVER = str(PROJECT_ROOT / "mcp_servers" / "bug_tracker_server.py")


def load_env_file(env_path: Path = PROJECT_ROOT / ".env") -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_env_file()

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.2

SYSTEM_PROMPT = """You are a developer-focused bug tracker assistant.

Use the Bug Tracker tools whenever the user wants to file, update, list, query,
assign, prioritize, or summarize bugs.

Bug tracker rules:
- Ask for missing required details before filing a bug: title, description, severity, and component.
- Valid severities are low, medium, high, and critical.
- Valid priorities are low, medium, high, and urgent.
- Valid statuses are open, in-progress, and resolved.
- A status update replaces the old status. A bug can be in only one status at a time.
- For lists and summaries, use only the latest tool output from the JSON data. Do not count earlier conversation history as current bug state.
- When a bug is created or updated, clearly mention the bug ID.
- Keep responses concise and useful for a developer workflow.
"""

MCP_CONFIG = {
    "bug_tracker": {
        "command": sys.executable,
        "args": [BUG_SERVER],
        "transport": "stdio",
    },
}


def has_valid_openai_key() -> bool:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    placeholders = {
        "your_key_here",
        "sk-your-key-here",
        "sk-your-openai-key-here",
    }
    return bool(api_key) and api_key not in placeholders


async def build_agent(checkpointer=None):
    client = MultiServerMCPClient(MCP_CONFIG)
    tools = await client.get_tools()

    print(f"\nLoaded {len(tools)} bug tracker tools:")
    for tool in tools:
        print(f"  - {tool.name}")

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
    """Approve or deny pending bug tracker tool calls before execution."""
    approved = []
    denied = []

    while True:
        state = graph.get_state(config)

        if not state.next or "tools" not in state.next:
            break

        last_msg = state.values["messages"][-1]
        pending_calls = last_msg.tool_calls

        print("\n" + "-" * 60)
        print("  [Human Review] Agent wants to call:")
        for tc in pending_calls:
            args_str = (
                ", ".join(f"{key}={value!r}" for key, value in tc["args"].items())
                if tc["args"] else "no args"
            )
            print(f"    - {tc['name']}({args_str})")
        print("-" * 60)

        decision = input("  Approve tool call(s)? (y/n): ").strip().lower()

        if decision == "y":
            for tc in pending_calls:
                approved.append(tc["name"])
            await graph.ainvoke(None, config=config)
            continue

        for tc in pending_calls:
            denied.append(tc["name"])

        await graph.aupdate_state(
            config,
            {
                "messages": [
                    ToolMessage(
                        content="Denied by human reviewer.",
                        tool_call_id=tc["id"],
                        name=tc["name"],
                    )
                    for tc in pending_calls
                ]
            },
            as_node="tools",
        )

        tool_names = ", ".join(f"`{tc['name']}`" for tc in pending_calls)
        await graph.aupdate_state(
            config,
            {
                "messages": [
                    AIMessage(
                        content=(
                            f"Action blocked. You denied the {tool_names} tool call(s), "
                            "so I did not change or read the bug tracker data for that request."
                        )
                    )
                ]
            },
            as_node="call_model",
        )
        break

    return approved, denied


def print_help() -> None:
    print("""
Example Bug Tracker Prompts
---------------------------
File a bug:
  "File a critical checkout bug: payment fails after submitting card details. Component: payments. Priority urgent."

Update a bug:
  "Assign BUG-0001 to Priya and mark it in-progress."
  "Add a note to BUG-0001: reproduced on Windows with Chrome."
  "Mark BUG-0001 resolved."

Query bugs:
  "List all open bugs."
  "Show high severity bugs."
  "Give me a bug summary by component."

Commands:
  help   - Show examples
  clear  - Reset conversation
  quit   - Exit
""")


async def run_interactive_chat() -> None:
    print("=" * 60)
    print("  LangGraph + MCP Agent  |  Local Bug Tracker")
    print("=" * 60)
    print(f"\nBug data file : {PROJECT_ROOT / 'bug_data' / 'bugs.json'}")
    print(f"LLM Model     : {LLM_MODEL}")
    print("HITL          : enabled before every bug tracker tool call")
    print("\nConnecting to Bug Tracker MCP server...")

    checkpointer = MemorySaver()
    graph = await build_agent(checkpointer)
    session_id = 0

    print("\nAgent ready. Type 'help' for examples, 'clear' to reset, or 'quit' to exit.")

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

        config = {"configurable": {"thread_id": f"bug-session-{session_id}"}}

        try:
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
        except Exception as exc:
            print(f"\nError: {exc}")


async def run_single_query(query: str) -> None:
    print(f"\nQuery: {query}\n")
    graph = await build_agent()
    result = await graph.ainvoke({"messages": [{"role": "user", "content": query}]})
    print(f"\nResponse:\n{result['messages'][-1].content}")


if __name__ == "__main__":
    if not has_valid_openai_key():
        print("Error: OPENAI_API_KEY is missing or still uses the placeholder value.")
        print(f"  Add OPENAI_API_KEY=your_real_key_here to: {PROJECT_ROOT / '.env'}")
        print("  Or in PowerShell run: $env:OPENAI_API_KEY=\"your_real_key_here\"")
        sys.exit(1)

    if "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            asyncio.run(run_single_query(sys.argv[idx + 1]))
        else:
            print('Usage: python -X utf8 bug_agent.py --query "your question here"')
    else:
        asyncio.run(run_interactive_chat())
