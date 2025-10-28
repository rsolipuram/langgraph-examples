#!/usr/bin/env python3
"""
Code Analysis Agent using ast-grep-mcp and LangChain/LangGraph

This agent can answer questions about code by using ast-grep for structural code search.
It uses the MultiServerMCPClient for persistent MCP connections.
"""

import asyncio
import os
import glob as glob_module
from typing import Literal
from typing_extensions import TypedDict, Annotated
import operator
from dotenv import load_dotenv

# Load environment variables for LangSmith tracing
load_dotenv()

# LangSmith tracing is automatically enabled if these env vars are set:
# - LANGCHAIN_TRACING_V2=true
# - LANGCHAIN_API_KEY=your_api_key
# - LANGCHAIN_PROJECT=your_project_name (optional)

# Step 1: Import MCP and LangChain components
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END


# Step 2: Configure local LLM
model = ChatOpenAI(
    model="google/gemma-3-12b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)


# Step 3: Define state
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# Step 4: Create MCP client with persistent connection
def get_mcp_client():
    """Create MultiServerMCPClient for ast-grep-mcp"""
    return MultiServerMCPClient(
        {
            "ast-grep": {
                "command": "uvx",
                "args": ["--from", "git+https://github.com/ast-grep/ast-grep-mcp", "ast-grep-server"],
                "transport": "stdio",
            }
        }
    )


# Step 4.5: Define glob tool
@tool
def glob_files(pattern: str, base_path: str = None) -> str:
    """
    Find files matching a glob pattern.

    Args:
        pattern: Glob pattern to match files (e.g., "*.py", "**/*.js", "src/**/*.ts")
        base_path: Base directory to search from (defaults to current directory)

    Returns:
        Newline-separated list of matching file paths

    Examples:
        - "*.py" - Find all Python files in current directory
        - "**/*.py" - Find all Python files recursively
        - "src/**/*.ts" - Find all TypeScript files in src directory
    """
    import os

    # Use base_path if provided, otherwise use current directory
    search_dir = base_path if base_path else os.path.dirname(os.path.abspath(__file__))

    # Change to the search directory for glob operation
    original_dir = os.getcwd()
    try:
        os.chdir(search_dir)

        # Use glob with recursive support
        matches = glob_module.glob(pattern, recursive=True)

        # Convert to absolute paths
        absolute_matches = [os.path.abspath(m) for m in matches]

        # Sort for consistent output
        absolute_matches.sort()

        if not absolute_matches:
            return f"No files found matching pattern: {pattern}"

        return "\n".join(absolute_matches)

    finally:
        os.chdir(original_dir)


# Step 5: Define model node
async def llm_call(state: dict, model_with_tools):
    """LLM decides whether to call a tool or not"""

    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))

    response = await model_with_tools.ainvoke(
        [
            SystemMessage(
                content=f"""You are a helpful code analysis assistant with access to ast-grep tools and file search.

IMPORTANT: When using find_code or find_code_by_rule, use this path:
project_folder: "{current_dir}"

Available Tools:
1. glob_files - Find files matching glob patterns
   Required: pattern (glob pattern like "*.py", "**/*.js")
   Optional: base_path (defaults to {current_dir})
   Examples: "*.py", "**/*.ts", "src/**/*.js"

2. find_code - Search using simple AST patterns
   Required: project_folder (absolute path), pattern (ast-grep pattern)
   Optional: language, max_results, output_format

3. find_code_by_rule - Search using YAML rules (advanced)
   Required: project_folder (absolute path), yaml (YAML rule string)
   Optional: max_results, output_format

4. dump_syntax_tree - Inspect AST structure
   Required: code, language
   Optional: format (cst/ast/pattern)

5. test_match_code_rule - Test a YAML rule
   Required: code, yaml

Patterns for Python (IMPORTANT: DO NOT include colons in patterns!):
- Find functions: "def $FUNC($$$)"
- Find classes: "class $CLASS"
- Find imports: "from $MOD import $$$" or "import $MOD"
- Find decorators: "@$DECORATOR"
- Use $ for wildcards: $NAME, $EXPR, etc.
- Use $$$ for variable length matches

When asked about code:
1. Use glob_files first to find relevant files if needed
2. Always use {current_dir} as the project_folder for ast-grep tools
3. Use tools to inspect the actual code
4. Report what you found accurately"""
            )
        ]
        + state["messages"]
    )

    return {
        "messages": [response],
        "llm_calls": state.get('llm_calls', 0) + 1
    }


# Step 6: Define tool node
async def tool_node(state: dict, tools_by_name: dict):
    """Performs the tool calls"""
    from langchain_core.messages import ToolMessage
    import traceback

    result = []
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        try:
            print(f"\n[DEBUG] Calling tool: {tool_call['name']}")
            print(f"[DEBUG] Args: {tool_call['args']}")
            observation = await tool.ainvoke(tool_call["args"])
            print(f"[DEBUG] Result: {observation}")
            result.append(ToolMessage(
                content=str(observation),
                tool_call_id=tool_call["id"]
            ))
        except Exception as e:
            error_msg = f"Error executing tool: {str(e)}\n{traceback.format_exc()}"
            print(f"[DEBUG] Error: {error_msg}")
            result.append(ToolMessage(
                content=error_msg,
                tool_call_id=tool_call["id"]
            ))

    return {"messages": result}


# Step 7: Define logic to determine whether to end
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


# Step 8: Build and run the agent
async def main():
    """Main function to set up and run the agent"""

    print("Loading ast-grep-mcp tools using MultiServerMCPClient...")

    # Create persistent MCP client
    client = get_mcp_client()

    # Get tools from the client
    mcp_tools = await client.get_tools()

    # Add custom glob tool
    all_tools = [glob_files] + list(mcp_tools)
    print(f"Loaded {len(all_tools)} tools: {[tool.name for tool in all_tools]}\n")

    # Create tools lookup
    tools_by_name = {tool.name: tool for tool in all_tools}

    # Bind tools to model
    model_with_tools = model.bind_tools(all_tools)

    # Build workflow
    agent_builder = StateGraph(MessagesState)

    # Add nodes - create proper async wrapper functions
    async def llm_call_node(state):
        return await llm_call(state, model_with_tools)

    async def tool_node_wrapper(state):
        return await tool_node(state, tools_by_name)

    agent_builder.add_node("llm_call", llm_call_node)
    agent_builder.add_node("tool_node", tool_node_wrapper)

    # Add edges
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END]
    )
    agent_builder.add_edge("tool_node", "llm_call")

    # Compile the agent
    agent = agent_builder.compile()

    # Visualize the agent graph
    try:
        graph_image = agent.get_graph(xray=True).draw_mermaid_png()
        with open("code_agent_graph.png", "wb") as f:
            f.write(graph_image)
        print("Agent graph saved to: code_agent_graph.png\n")
    except Exception as e:
        print(f"Could not generate graph visualization: {e}\n")

    # Example: Ask a question about code
    print("=" * 60)
    print("Code Analysis Agent Ready!")
    print("=" * 60)

    # Test question
    question = "What functions are defined in quickstart.py? Show me their names and signatures."
    print(f"\nQuestion: {question}\n")

    messages = [HumanMessage(content=question)]
    result = await agent.ainvoke({"messages": messages, "llm_calls": 0})

    print("=" * 60)
    print("Agent Response:")
    print("=" * 60)
    for m in result["messages"]:
        m.pretty_print()

    print(f"\n\nTotal LLM calls: {result['llm_calls']}")

    # Test glob tool
    print("\n" + "=" * 60)
    print("Testing Glob Tool")
    print("=" * 60)

    glob_questions = [
        "Find all Python files in the current directory using glob",
        "Use glob to find all .png files recursively",
        "List all files with 'quickstart' in their name using glob patterns"
    ]

    for glob_question in glob_questions:
        print(f"\n\nQuestion: {glob_question}\n")
        messages = [HumanMessage(content=glob_question)]
        result = await agent.ainvoke({"messages": messages, "llm_calls": 0})

        print("-" * 60)
        print("Response:")
        print("-" * 60)
        # Print only the final assistant response
        for m in result["messages"]:
            if hasattr(m, 'content') and not hasattr(m, 'tool_calls'):
                print(m.content)

        print(f"\nLLM calls: {result['llm_calls']}")


if __name__ == "__main__":
    asyncio.run(main())
