@echo off
REM Run the LangGraph + MCP Agent with UTF-8 support (required for emoji on Windows)
python -X utf8 agent.py %*
