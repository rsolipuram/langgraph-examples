Markdown



# Project Specification: LangGraph Source Analysis Reporting Agent



---## 1. Project Objective



To build a **read-only** stateful agent that can be given a local path to a source code repository and a user query. The agent will autonomously use a suite of tools to fulfill the query, generate a comprehensive analysis report in **Markdown**, and **save that report to disk.**



This agent will **never** modify the source code.



---## 2. Core Architecture: LangGraph `StateGraph`### Agent State Definition



The agent's memory is defined by the following `TypedDict`. This state will be passed to and modified by each node in the graph.```python

from typing import TypedDict, List, Optional, Dict, Any



class SourceAnalysisState(TypedDict):

    """The memory of our agent."""

    

    # --- Input ---

    repo_path: str      # The absolute local path to the repo

    user_query: str     # The initial user request

    

    # The desired filename for the final report, e.g., "my_repo_analysis.md"

    output_filename: str 

    

    # --- Internal State ---

    analysis_plan: List[str]  # The agent's step-by-step plan

    scratchpad: str         # "Short-term memory" for accumulating facts

    

    # --- Output ---

    # This field will hold the final, formatted Markdown

    # report before it's written to disk.

    final_report: str

3. Core Component Spec: The Agent's Tools

These tools are the agent's "eyes and hands." They must be implemented as @tool-decorated Python functions. They are read-only, fast, and classical.

1. GlobTool (File Tree Browsing)

Objective: To list files using fast, pattern-based matching.

Signature:

Python



@tooldef glob_tool(pattern: str) -> List[str]:

    """

    Finds all file paths relative to the repo root matching a glob pattern.

    Example: "**/*.py" or "src/**/package.xml"

    """

Implementation Notes:

Must use the Python glob library with recursive=True.

All paths returned should be relative to the state.repo_path.

2. GrepTool / RipGrepTool (Fast Content Search)

Objective: To find where a literal string (like a function name or class) exists. This is for precision and is much faster than RAG.

Signature:

Python



@tooldef grep_tool(query: str, path_glob: str = "**/*") -> List[Dict[str, Any]]:

    """

    Uses 'ripgrep' (rg) to find exact string matches in files.

    'query' is the literal string to search for (e.g., "class User").

    'path_glob' is a glob pattern to restrict the search (e.g., "**/*.py").

    Returns a JSON list of matches.

    """

Implementation Notes:

Must use subprocess to call rg (ripgrep) with the --json flag.

Example command: rg --json -e "class User" -g "**/*.py" /path/to/repo

Must parse the JSON output into a clean list of dictionaries: [{"file": "src/api.py", "line": 42, "match": "class User:..."}]

3. FileReadTool (Precise File Reading)

Objective: To read only the relevant parts of a file, identified via GrepTool or GlobTool.

Signature:

Python



@tooldef file_read_tool(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:

    """

    Reads the full content or a specific line range of a file.

    'path' is the relative file path from the repo root.

    If 'start_line' and 'end_line' are provided, reads only that range.

    """

Implementation Notes:

Must use standard Python file I/O and itertools.islice for efficient line-range reading.

All file paths are relative to the state.repo_path.

4. TreeSitterTool (Smart Code Parsing)

Objective: To parse the grammatical structure of code, enabling "smart chunking" (e.g., by function) and precise data extraction (e.g., "list all imports").

Signature:

Python



@tooldef treesitter_tool(path: str, treesitter_query: str) -> List[str]:

    """

    Uses tree-sitter to parse a file and extract all nodes matching a query.

    Example query for all function names in Python:

    (function_definition name: (identifier))

    """

Implementation Notes:

Requires the tree-sitter library and language-specific grammars (e.g., tree-sitter-python).

The tool will parse the file at path, execute the treesitter_query, and return a list of the text content of all matching nodes.

5. SaveReportTool (Report Persistence)

Objective: To save the final, formatted Markdown report to the filesystem.

LangChain Import:

Python



from langchain_community.tools.file_management import WriteFileTool

Implementation Notes:

This tool is pre-built and should be initialized once when building the agent: save_report_tool = WriteFileTool()

The agent will call this tool during the save_report graph node.

4. Core Logic: The Graph Definition

The StateGraph will be defined with a new final step for saving the report.

Nodes:

plan: The LLM "brain" that orchestrates tools based on the state.

execute_tools: The ToolExecutor that calls the tools chosen by plan.

format_final_report: A node that takes the final scratchpad content and formats it into a clean Markdown final_report.

save_report: A node that calls the save_report_tool to persist the final_report.

Edges:

Entry Point: plan

plan -> execute_tools (Standard edge)

execute_tools -> plan (Standard edge)

This creates the primary "think-act" loop.

plan -> format_final_report (Conditional edge)

format_final_report -> save_report (Standard edge)

save_report -> END (Final step)

Conditional Edge (should_continue_or_finish):

This logic, connected to the plan node, decides the next step.

IF the plan node's output is a request for a tool call, the graph routes to execute_tools.

IF the plan node's output explicitly states the analysis is finished, the graph routes to format_final_report.

5. Workflow 1 Spec: The Macro-Analysis Recipe

This is the recipe for the plan node when it detects a high-level query like "Analyze this repo."

Trigger: user_query is "Give me an overview of this repo."

plan (Step 1): "I need to find metadata files."

execute_tools: Calls GlobTool for "*README*", "*package.json", "*requirements.txt", "*pom.xml", etc.

plan (Step 2): Receives file lists. "I will read the most relevant ones."

execute_tools: Calls FileReadTool on each file found (e.g., FileReadTool("README.md")).

plan (Step 3): Receives file content. "Now I need the architecture."

execute_tools: Calls GlobTool(pattern="src/**/*") to get a file tree.

plan (Step 4): Receives the file list. "I have all information." The LLM synthesizes all facts into the scratchpad and signals to finish.

router: Detects finish signal and routes to format_final_report.

format_final_report (Node): The LLM is prompted: "Format the analysis in the scratchpad into a comprehensive, human-readable Markdown report." The output is saved to the state.final_report field.

save_report (Node): This node is triggered. It calls save_report_tool(file_path=state.output_filename, text=state.final_report).

END

6. Workflow 2 Spec: The Micro-Analysis (Read-Only) Recipe

This is the interactive loop for a specific query like "Find where process_payment is and explain its logic."

Trigger: user_query is "Find process_payment and analyze it."

plan (Loop 1): "I need to find the function. A literal grep search for 'def process_payment' is precise."

execute_tools: Calls GrepTool(query="def process_payment", path_glob="**/*.py").

plan (Loop 2): Receives [{"file": "src/api/payments.py", "line": 42, ...}]. "I found it. Now I must read the function to analyze it."

execute_tools: Calls FileReadTool(path="src/api/payments.py", start_line=40, end_line=90). (The LLM intelligently pads the line numbers).

plan (Loop 3): Receives the function's text. "I have the code. I will now analyze its logic, what it imports, and what it returns." The LLM writes its full analysis to the scratchpad and signals finish.

router: Routes to format_final_report.

format_final_report (Node): The LLM formats the analysis from the scratchpad into a clean Markdown answer and saves it to state.final_report.

save_report (Node): Calls save_report_tool(file_path=state.output_filename, text=state.final_report).

END