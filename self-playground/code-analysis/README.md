# LangGraph Source Code Analysis Agent

A read-only stateful agent built with LangGraph that analyzes source code repositories and generates comprehensive Markdown reports.

## Features

✅ **Read-Only Analysis** - Never modifies source code
✅ **Intelligent Tool Usage** - Automatically selects appropriate tools (glob, grep, file reading)
✅ **Markdown Reports** - Generates well-formatted analysis reports
✅ **Latest LangGraph** - Uses modern LangGraph patterns with StateGraph
✅ **Local LLM Support** - Works with local Gemma model

## Architecture

The agent follows the PRD specification with a clean StateGraph workflow:

```
START → plan → [tool_node ⟷ plan loop] → format_final_report → save_report → END
```

### Nodes

- **plan**: LLM orchestrates tool usage based on current state
- **tool_node**: Executes requested tools (glob, grep, file_read)
- **format_final_report**: Formats analysis into professional Markdown
- **save_report**: Persists report to disk

### State

```python
class AgentState(TypedDict):
    messages: list[AnyMessage]  # Conversation history
    repo_path: str              # Repository to analyze
    user_query: str             # Analysis request
    output_filename: str        # Report output path
    analysis_plan: List[str]    # Step-by-step plan
    scratchpad: str            # Accumulated findings
    final_report: str          # Formatted Markdown report
```

## Tools Available

### 1. glob_tool(pattern, repo_path)
Fast pattern-based file matching using Python's glob library.

**Examples:**
- `**/*.py` - All Python files
- `**/README*` - All README files
- `src/**/*.ts` - TypeScript files in src/

### 2. grep_tool(query, repo_path, path_glob)
Exact string search using ripgrep for precision and speed.

**Examples:**
- Find class definition: `query="class User"`
- Find function: `query="def process_payment"`
- Restrict to Python files: `path_glob="**/*.py"`

### 3. file_read_tool(path, repo_path, start_line, end_line)
Read full files or specific line ranges.

**Examples:**
- Read entire file: `path="src/main.py"`
- Read function: `path="src/api.py", start_line=40, end_line=90`

### 4. treesitter_tool(path, repo_path, treesitter_query)
Parse code structure using tree-sitter and extract nodes matching a query.

**Examples:**
- All function names: `treesitter_query="(function_definition name: (identifier) @name)"`
- All class names: `treesitter_query="(class_definition name: (identifier) @name)"`
- All imports: `treesitter_query="(import_statement) @import"`

## Usage

### Basic Usage

```bash
python agent.py /path/to/repo "Your analysis query" --output report.md
```

### Examples

**List main files:**
```bash
python agent.py .. "List the main Python files in this repository" --output files.md
```

**Analyze specific file:**
```bash
python agent.py .. "Analyze quickstart.py - what does it do?" --output quickstart_analysis.md
```

**Find function:**
```bash
python agent.py .. "Find the process_payment function and explain it" --output payment_analysis.md
```

**Repository overview:**
```bash
python agent.py .. "Give me an overview of this repository" --output overview.md
```

## Requirements

```
langchain-core>=1.0.1
langchain-openai>=1.0.1
langgraph>=1.0.1
python-dotenv>=1.0.0
tree-sitter>=0.25.0
tree-sitter-python>=0.25.0
ripgrep (rg command)
```

## Configuration

The agent uses a local LLM server. Configure in `agent.py`:

```python
model = ChatOpenAI(
    model="google/gemma-3-12b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)
```

## Workflow Examples

### Macro-Analysis (Repository Overview)

1. **plan**: "I need to find metadata files"
2. **tool_node**: Calls `glob_tool` for README, package.json, requirements.txt
3. **plan**: "I will read the most relevant ones"
4. **tool_node**: Calls `file_read_tool` on each found file
5. **plan**: "Now I need the architecture"
6. **tool_node**: Calls `glob_tool(pattern="src/**/*")`
7. **plan**: Analyzes findings and signals completion
8. **format_final_report**: Formats into Markdown
9. **save_report**: Saves to disk

### Micro-Analysis (Specific Function)

1. **plan**: "I need to find the function using grep"
2. **tool_node**: Calls `grep_tool(query="def process_payment")`
3. **plan**: "Found it at line 42, reading the function"
4. **tool_node**: Calls `file_read_tool(path="...", start_line=40, end_line=90)`
5. **plan**: Analyzes the code and signals completion
6. **format_final_report**: Formats analysis into Markdown
7. **save_report**: Saves to disk

## Implementation Details

### Latest LangGraph Patterns

- ✅ Uses `StateGraph` from langgraph.graph
- ✅ Proper tool binding with `.bind_tools()`
- ✅ Message-based state management
- ✅ Conditional edges with typed literals
- ✅ Recursion limit configuration

### Intelligent Loop Control

The agent prevents infinite loops by:
- Tracking tool call count
- Providing clear finish conditions in prompts
- Using recursion limits (default: 50)
- Explicitly telling LLM when to stop calling tools

### Error Handling

- Tool errors are captured and returned as ToolMessages
- File not found errors are gracefully handled
- Repository path validation before execution

## Sample Output

```markdown
# Repository Analysis Report

**Repository:** /path/to/repo
**Query:** Analyze quickstart.py

## Executive Summary

The quickstart.py file demonstrates a foundational LangGraph agent...

## Main Components

### 1. Tool Definitions
The script defines three arithmetic tools...

### 2. LLM Setup
Initializes ChatOpenAI model with local server...

## Conclusion

This script serves as an excellent starting point for understanding...
```

## Testing

Run the included test queries:

```bash
# Test 1: Simple file listing
python agent.py .. "List Python files" --output test1.md

# Test 2: Specific file analysis
python agent.py .. "Analyze quickstart.py" --output test2.md

# Test 3: Find and explain
python agent.py .. "Find multiply function and explain it" --output test3.md
```

## Troubleshooting

### Recursion Limit Reached

If you see `GraphRecursionError`, the agent is stuck in a loop. This usually means:
- The LLM keeps calling the same tool repeatedly
- The query is too vague or complex

**Solution:** Make your query more specific or increase `recursion_limit` in the config.

### Tool Errors

If tools return errors:
- **glob_tool**: Check the pattern syntax
- **grep_tool**: Ensure ripgrep (rg) is installed
- **file_read_tool**: Verify file paths are relative to repo_path

### No Report Generated

If no report is saved:
- Check that the output directory exists
- Verify file permissions
- Look for errors in the console output

## PRD Compliance

This implementation follows the PRD specification:

✅ Read-only agent (never modifies source code)
✅ StateGraph with proper node definitions
✅ All required tools (glob, grep, file_read, save_report)
✅ Macro and micro analysis workflows
✅ Markdown report generation
✅ Report persistence to disk

## Future Enhancements

Potential improvements (not in PRD):

- [ ] Support for multiple programming languages (JavaScript, TypeScript, Go, etc.)
- [ ] Support for multiple output formats (PDF, HTML)
- [ ] Interactive mode with followup questions
- [ ] Caching for faster repeated queries
- [ ] MCP integration for additional tools

## License

Part of the LangGraph self-playground project.
