#!/usr/bin/env python3
"""
Flexible Code Analysis Agent - Simple LangGraph pattern

This agent analyzes code repositories with minimal prescriptive prompting.
Based on the pattern from quickstartcode.py with flexibility for the LLM to decide.
"""

import os
import argparse
import operator
from typing import Literal
from typing_extensions import TypedDict, Annotated
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, START, END

from tools import glob_tool, grep_tool, file_read_tool, treesitter_tool

# Configure LLM
model = ChatOpenAI(
    model="qwen/qwen3-coder-30b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)

# Bind tools to model
tools = [glob_tool, grep_tool, file_read_tool, treesitter_tool]
model_with_tools = model.bind_tools(tools)

# Simple State Definition
class AnalysisState(TypedDict):
    """Simple state - just messages and metadata."""
    messages: Annotated[list[BaseMessage], operator.add]
    repo_path: str
    output_filename: str
    llm_calls: int


# Node: LLM Call
def llm_call(state: AnalysisState):
    """LLM decides whether to call a tool or provide final answer."""

    # Simple system message - let LLM figure out the rest
    system_msg = SystemMessage(
        content=f"""You are a code analysis assistant analyzing repository: {state['repo_path']}

Available tools:
- glob_tool(pattern, repo_path): Find files matching patterns
- grep_tool(query, repo_path, path_glob): Search for exact strings in files
- file_read_tool(path, repo_path, start_line, end_line): Read file contents
- treesitter_tool(path, repo_path, treesitter_query): Parse code structure

Use tools to gather information, then provide your analysis."""
    )

    response = model_with_tools.invoke(
        [system_msg] + state["messages"]
    )

    return {
        "messages": [response],
        "llm_calls": state.get('llm_calls', 0) + 1
    }


# Node: Tool Execution
def tool_node(state: AnalysisState):
    """Execute the tools requested by the LLM."""

    last_message = state["messages"][-1]
    results = []

    for tool_call in last_message.tool_calls:
        # Inject repo_path into all tool calls
        tool_call["args"]["repo_path"] = state["repo_path"]

        # Execute the tool
        tool_map = {t.name: t for t in tools}
        tool_name = tool_call["name"]

        if tool_name in tool_map:
            try:
                result = tool_map[tool_name].invoke(tool_call["args"])
                results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
            except Exception as e:
                results.append(ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=tool_call["id"]
                ))

    return {"messages": results}


# Router: Continue or End
def should_continue(state: AnalysisState) -> Literal["tool_node", "END"]:
    """Decide if we should continue or stop."""

    messages = state["messages"]
    last_message = messages[-1]

    # If LLM made tool calls, execute them
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_node"

    # Otherwise, we're done
    return "END"


# Build Graph
def build_graph():
    """Construct the simple StateGraph."""

    workflow = StateGraph(AnalysisState)

    # Add nodes
    workflow.add_node("llm_call", llm_call)
    workflow.add_node("tool_node", tool_node)

    # Set entry point
    workflow.add_edge(START, "llm_call")

    # Add conditional edge from llm_call
    workflow.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "tool_node": "tool_node",
            "END": END
        }
    )

    # Loop back from tool_node to llm_call
    workflow.add_edge("tool_node", "llm_call")

    return workflow.compile()


# Main Execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flexible code analysis agent")
    parser.add_argument("repo_path", help="Path to repository")
    parser.add_argument("query", help="Your analysis query")
    parser.add_argument("--output", "-o", dest="output_filename",
                       default="analysis_report.md",
                       help="Output filename (default: analysis_report.md)")
    args = parser.parse_args()

    # Validate repo path
    if not os.path.exists(args.repo_path):
        print(f"❌ Error: Repository path does not exist: {args.repo_path}")
        exit(1)

    # Build agent
    print("🤖 Building flexible analysis agent...")
    app = build_graph()

    # Initial state
    initial_state = {
        "repo_path": os.path.abspath(args.repo_path),
        "output_filename": args.output_filename,
        "messages": [HumanMessage(content=args.query)],
        "llm_calls": 0
    }

    print(f"📂 Repository: {initial_state['repo_path']}")
    print(f"❓ Query: {args.query}")
    print(f"📝 Output: {args.output_filename}")
    print("\n" + "="*60)
    print("Starting analysis...")
    print("="*60 + "\n")

    # Run the agent
    final_state = None
    step = 0

    for event in app.stream(initial_state, {"recursion_limit": 50}):
        step += 1
        for node_name, node_output in event.items():
            print(f"\n[Step {step}] {node_name}")

            if "messages" in node_output and node_output["messages"]:
                last_msg = node_output["messages"][-1]

                if isinstance(last_msg, AIMessage):
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        print(f"  🔧 Calling: {[tc['name'] for tc in last_msg.tool_calls]}")
                    elif hasattr(last_msg, 'content') and last_msg.content:
                        preview = last_msg.content[:200]
                        print(f"  💭 Response: {preview}{'...' if len(last_msg.content) > 200 else ''}")

                if isinstance(last_msg, ToolMessage):
                    preview = last_msg.content[:150]
                    print(f"  📊 Result: {preview}{'...' if len(last_msg.content) > 150 else ''}")

        final_state = event

    print("\n" + "="*60)
    print("✅ Analysis complete!")
    print("="*60)

    # Extract final response and save
    if final_state:
        for node_output in final_state.values():
            if "messages" in node_output:
                for msg in reversed(node_output["messages"]):
                    if isinstance(msg, AIMessage) and hasattr(msg, 'content') and msg.content and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                        # This is the final AI response
                        print(f"\n📄 Saving analysis to: {args.output_filename}")

                        # Ensure directory exists
                        os.makedirs(os.path.dirname(args.output_filename) if os.path.dirname(args.output_filename) else '.', exist_ok=True)

                        with open(args.output_filename, 'w', encoding='utf-8') as f:
                            f.write(msg.content)

                        print(f"✅ Saved {len(msg.content)} characters")
                        break

    print(f"\n🔢 Total LLM calls: {final_state.get(list(final_state.keys())[-1], {}).get('llm_calls', 'N/A')}")
