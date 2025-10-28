#!/usr/bin/env python3
"""Minimal test to debug tool calling issue"""

from typing import Literal
from typing_extensions import TypedDict, Annotated
import operator

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END


# Model
model = ChatOpenAI(
    model="google/gemma-3-12b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)


# Tool
@tool
def list_functions(file_path: str) -> str:
    """List all function definitions in a Python file."""
    return f"Functions in {file_path}: multiply, add, divide"


# Bind tools
tools = [list_functions]
tools_by_name = {t.name: t for t in tools}
model_with_tools = model.bind_tools(tools)


# State
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


# Nodes
def llm_call(state: dict):
    print(f"\n=== LLM CALL ===")
    response = model_with_tools.invoke(
        [SystemMessage(content="You are a helpful assistant.")]
        + state["messages"]
    )
    print(f"Tool calls: {response.tool_calls}")
    return {"messages": [response]}


def tool_node(state: dict):
    print(f"\n=== TOOL NODE ===")
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    return END


# Build graph
graph_builder = StateGraph(MessagesState)
graph_builder.add_node("llm_call", llm_call)
graph_builder.add_node("tool_node", tool_node)
graph_builder.add_edge(START, "llm_call")
graph_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
graph_builder.add_edge("tool_node", "llm_call")
agent = graph_builder.compile()


# Test
if __name__ == "__main__":
    messages = [HumanMessage(content="List functions in quickstart.py")]
    result = agent.invoke({"messages": messages})

    print("\n=== FINAL RESULT ===")
    for m in result["messages"]:
        m.pretty_print()
