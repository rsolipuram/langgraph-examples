#!/usr/bin/env python3
"""
Code Analysis Agent using ast-grep CLI directly with LangChain/LangGraph

This agent can answer questions about code by using ast-grep directly via subprocess.
Follows the same pattern as quickstart.py but with ast-grep tools.
"""

import subprocess
import json
import os
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

# Step 1: Import LangChain components
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END


# Step 2: Configure local LLM
model = ChatOpenAI(
    model="google/gemma-3-12b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)


# Step 3: Get current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


# Step 4: Define ast-grep tools using subprocess
@tool
def list_functions(file_path: str) -> str:
    """List all function definitions in a Python file."""
    try:
        cmd = ["sg", "run", "--pattern", "def $FUNC($$$)", "--lang", "python", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.stdout else "No functions found."
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def list_classes(file_path: str) -> str:
    """List all class definitions in a Python file."""
    try:
        cmd = ["sg", "run", "--pattern", "class $CLASS", "--lang", "python", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.stdout else "No classes found."
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def find_imports(file_path: str) -> str:
    """Find all import statements in a Python file."""
    try:
        cmd1 = ["sg", "run", "--pattern", "import $$$", "--lang", "python", file_path]
        cmd2 = ["sg", "run", "--pattern", "from $$$", "--lang", "python", file_path]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
        return f"{result1.stdout}\n{result2.stdout}" if (result1.stdout or result2.stdout) else "No imports found."
    except Exception as e:
        return f"Error: {str(e)}"


# Step 5: Create tools list
tools = [list_functions, list_classes, find_imports]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)


# Step 6: Define state
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# Step 7: Define model node
def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    response = model_with_tools.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant tasked with analyzing code using ast-grep tools."
            )
        ]
        + state["messages"]
    )

    return {
        "messages": [response],
        "llm_calls": state.get('llm_calls', 0) + 1
    }


# Step 8: Define tool node
def tool_node(state: dict):
    """Performs the tool calls"""

    result = []
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        try:
            observation = tool.invoke(tool_call["args"])
            result.append(ToolMessage(
                content=str(observation),
                tool_call_id=tool_call["id"]
            ))
        except Exception as e:
            result.append(ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=tool_call["id"]
            ))

    return {"messages": result}


# Step 9: Define logic to determine whether to end
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop"""

    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tool_node"

    return END


# Step 10: Build the agent
agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END]
)
agent_builder.add_edge("tool_node", "llm_call")
agent = agent_builder.compile()


# Step 11: Main execution
if __name__ == "__main__":
    # Visualize the agent graph
    try:
        graph_image = agent.get_graph(xray=True).draw_mermaid_png()
        with open("code_agent_graph.png", "wb") as f:
            f.write(graph_image)
        print("Agent graph saved to: code_agent_graph.png\n")
    except Exception as e:
        print(f"Could not generate graph visualization: {e}\n")

    print("=" * 60)
    print("Code Analysis Agent Ready!")
    print("=" * 60)

    # Test question
    question = "What functions are defined in quickstart.py? List their names and what they do."
    print(f"\nQuestion: {question}\n")

    messages = [HumanMessage(content=question)]
    result = agent.invoke({"messages": messages, "llm_calls": 0})

    print("=" * 60)
    print("Agent Response:")
    print("=" * 60)
    for m in result["messages"]:
        m.pretty_print()

    print(f"\n\nTotal LLM calls: {result['llm_calls']}")
