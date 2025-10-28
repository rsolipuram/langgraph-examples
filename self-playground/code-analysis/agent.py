#!/usr/bin/env python3
"""
LangGraph Source Analysis Agent
Follows the PRD specification for analyzing source code repositories.
"""

import os
import argparse
import operator
from typing import List, Dict, Any, Optional, Annotated, TypedDict, Literal
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AnyMessage, ToolMessage, HumanMessage, SystemMessage, AIMessage

from state import SourceAnalysisState
from tools import glob_tool, grep_tool, file_read_tool, treesitter_tool, save_report_tool

# Configure LLM with tools bound
model = ChatOpenAI(
    model="google/gemma-3-12b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)

# Bind tools to model (excluding save_report_tool which is used separately)
tools = [glob_tool, grep_tool, file_read_tool, treesitter_tool]
model_with_tools = model.bind_tools(tools)

# Agent State Definition
class AgentState(TypedDict):
    """Extended state with message history for tool calling."""
    messages: Annotated[list[AnyMessage], operator.add]
    repo_path: str
    user_query: str
    output_filename: str
    analysis_plan: List[str]
    scratchpad: str
    final_report: str


# Node: Plan and Execute
def plan_node(state: AgentState) -> Dict[str, Any]:
    """
    The LLM 'brain' that orchestrates tools based on the state.
    This node decides whether to call tools or finish the analysis.
    """

    # Count how many tool calls we've made
    tool_call_count = sum(1 for msg in state["messages"] if isinstance(msg, AIMessage) and msg.tool_calls)

    # Build system message with current context
    system_msg = f"""You are a senior software engineer analyzing a codebase.

Repository Path: {state['repo_path']}
User Query: {state['user_query']}

Tool calls made so far: {tool_call_count}

You have access to these tools:
1. glob_tool(pattern, repo_path) - Find files matching a pattern (e.g., "**/*.py", "**/README*")
2. grep_tool(query, repo_path, path_glob) - Search for exact strings in files (e.g., "class User", "def process_payment")
3. file_read_tool(path, repo_path, start_line, end_line) - Read file contents or specific line ranges
4. treesitter_tool(path, repo_path, treesitter_query) - Parse code structure and extract nodes (e.g., all function names, all imports)

INSTRUCTIONS:
1. If tool_calls made is 0-1: You can call tools to gather information
2. If tool_calls made is 2-3: You should be preparing to finish - only call tools if absolutely necessary
3. If tool_calls made is 4+: STOP calling tools and provide your final analysis NOW based on what you have

BE EFFICIENT: For most queries, 1-2 tool calls should be sufficient. Don't over-analyze.

When you have information to answer the query:
- Provide a comprehensive text response analyzing what you found
- DO NOT call any tools
- Your response will be formatted into a Markdown report

Previous conversation context is below (use ToolMessages to understand what you already know)."""

    messages = [SystemMessage(content=system_msg)] + state["messages"]

    response = model_with_tools.invoke(messages)

    return {"messages": [response]}


# Node: Execute Tools
def tool_node(state: AgentState) -> Dict[str, Any]:
    """Execute the tools requested by the LLM."""

    last_message = state["messages"][-1]
    results = []

    for tool_call in last_message.tool_calls:
        # Inject repo_path into all tool calls
        tool_call["args"]["repo_path"] = state["repo_path"]

        # Execute the tool
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Find and invoke the tool
        tool_map = {t.name: t for t in tools}
        if tool_name in tool_map:
            try:
                result = tool_map[tool_name].invoke(tool_args)
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


# Node: Format Final Report
def format_final_report_node(state: AgentState) -> Dict[str, Any]:
    """
    Takes the conversation history and formats it into a clean Markdown report.
    """

    # Extract all the analysis from the conversation
    analysis_text = []
    for msg in state["messages"]:
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            analysis_text.append(msg.content)
        elif isinstance(msg, ToolMessage):
            # Include relevant tool results in context
            pass

    combined_analysis = "\n\n".join(analysis_text)

    # Format the final report
    formatter_prompt = f"""You are a technical writer. Format the following analysis into a comprehensive, well-structured Markdown report.

Repository: {state['repo_path']}
Query: {state['user_query']}

Analysis:
{combined_analysis}

Create a professional Markdown report with:
- Clear title and sections
- Bullet points and code blocks where appropriate
- Well-organized findings
- Conclusion/summary

Output ONLY the Markdown report, nothing else."""

    formatter = ChatOpenAI(
        model="google/gemma-3-12b",
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-needed",
        temperature=0
    )

    response = formatter.invoke([HumanMessage(content=formatter_prompt)])

    return {"final_report": response.content}


# Node: Save Report
def save_report_node(state: AgentState) -> Dict[str, Any]:
    """Save the final report to disk."""

    output_path = state['output_filename']

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

    # Write the report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(state['final_report'])

    print(f"\n✅ Report saved to: {output_path}")
    print(f"📄 Report size: {len(state['final_report'])} characters")

    return {}


# Router: Decide whether to continue or finish
def should_continue(state: AgentState) -> Literal["tool_node", "format_final_report"]:
    """
    Decide if we should continue the tool loop or format the final report.
    """

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM made tool calls, execute them
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_node"

    # Otherwise, the LLM is done and we should format the report
    return "format_final_report"


# Build the Graph
def build_graph():
    """Construct the StateGraph for the analysis agent."""

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("format_final_report", format_final_report_node)
    workflow.add_node("save_report", save_report_node)

    # Set entry point
    workflow.add_edge(START, "plan")

    # Add edges
    workflow.add_conditional_edges(
        "plan",
        should_continue,
        {
            "tool_node": "tool_node",
            "format_final_report": "format_final_report",
        },
    )
    workflow.add_edge("tool_node", "plan")  # Loop back to plan after tool execution
    workflow.add_edge("format_final_report", "save_report")
    workflow.add_edge("save_report", END)

    return workflow.compile()


# Main Execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a source code repository")
    parser.add_argument("repo_path", help="Absolute path to the repository")
    parser.add_argument("user_query", help="Your analysis query")
    parser.add_argument("--output", "-o", dest="output_filename",
                       default="analysis_report.md",
                       help="Output filename for the report (default: analysis_report.md)")
    args = parser.parse_args()

    # Validate repo path
    if not os.path.exists(args.repo_path):
        print(f"❌ Error: Repository path does not exist: {args.repo_path}")
        exit(1)

    # Build the agent
    print("🤖 Building analysis agent...")
    app = build_graph()

    # Initial state
    initial_state: AgentState = {
        "repo_path": os.path.abspath(args.repo_path),
        "user_query": args.user_query,
        "output_filename": args.output_filename,
        "analysis_plan": [],
        "scratchpad": "",
        "final_report": "",
        "messages": [HumanMessage(content=args.user_query)],
    }

    print(f"📂 Repository: {initial_state['repo_path']}")
    print(f"❓ Query: {args.user_query}")
    print(f"📝 Output: {args.output_filename}")
    print("\n" + "="*60)
    print("Starting analysis...")
    print("="*60 + "\n")

    # Run the agent with recursion limit
    final_state = None
    config = {"recursion_limit": 50}  # Increase from default 25

    step_count = 0
    tool_count = 0
    for event in app.stream(initial_state, config=config):
        step_count += 1
        for node_name, node_output in event.items():
            print(f"\n📍 Step {step_count} - Node: {node_name}", end="")

            if node_output and "messages" in node_output:
                last_msg = node_output["messages"][-1]
                if isinstance(last_msg, AIMessage):
                    if last_msg.tool_calls:
                        tool_count += 1
                        print(f" [Tool call #{tool_count}]")
                        print(f"🔧 Tool calls: {[tc['name'] for tc in last_msg.tool_calls]}")
                        for tc in last_msg.tool_calls:
                            args_str = ', '.join(f'{k}={v[:50] if isinstance(v, str) and len(v) > 50 else v}'
                                               for k, v in tc['args'].items() if k != 'repo_path')
                            print(f"   - {tc['name']}({args_str})")
                    elif last_msg.content:
                        print(" [Generating analysis]")
                        print(f"💭 Analysis length: {len(last_msg.content)} characters")
                        print(f"   Preview: {last_msg.content[:200]}...")
                    else:
                        print()
                elif isinstance(last_msg, ToolMessage):
                    result_len = len(last_msg.content)
                    print(f" [Tool result: {result_len} chars]")
                    print(f"📊 Preview: {last_msg.content[:200]}...")
            else:
                print()
        final_state = event

    print("\n" + "="*60)
    print("✅ Analysis complete!")
    print("="*60)
