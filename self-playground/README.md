# LangGraph Code Analysis Agent

This directory contains LangGraph agents for different use cases.

## Files

### 1. `quickstart.py` - Arithmetic Agent ✅ WORKING
A simple agent that performs arithmetic operations using tools.

**Features:**
- Uses local Gemma model (google/gemma-3-12b)
- Three tools: add, multiply, divide
- Demonstrates basic LangGraph workflow

**Run:**
```bash
python quickstart.py
```

**Example output:**
```
Add 3 and 4.
→ The sum of 3 and 4 is 7.
```

---

### 2. `quickstartcode.py` - Code Analysis Agent (MCP Version) ✅ WORKING
Advanced agent using ast-grep-mcp for code analysis via Model Context Protocol.

**Features:**
- Integrates with ast-grep-mcp server via `MultiServerMCPClient`
- 4 MCP tools: dump_syntax_tree, test_match_code_rule, find_code, find_code_by_rule
- Async/await architecture
- LangSmith tracing enabled
- Persistent MCP connection (no more ClosedResourceError!)

**Run:**
```bash
python quickstartcode.py
```

**Example output:**
```
What functions are defined in quickstart.py?
→ multiply(a, b): Multiplies two integers
→ add(a, b): Adds two integers
→ divide(a, b): Divides two integers
...
```

---

### 3. `quickstartcode_simple.py` - Code Analysis Agent (Direct CLI) ✅ WORKING
Simplified version using ast-grep CLI directly.

**Features:**
- Direct subprocess calls to `sg` command
- Custom tools: list_functions, list_classes, find_imports
- Synchronous execution
- Works with local Gemma model

**Run:**
```bash
python quickstartcode_simple.py
```

**Example output:**
```
What functions are defined in quickstart.py?
→ multiply(a, b): Multiplies two integers
→ add(a, b): Adds two integers
→ divide(a, b): Divides two integers
→ llm_call(state): Decides whether to call a tool
→ tool_node(state): Performs the tool call
→ should_continue(state): Decides whether to continue the loop
```

---

## Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Optional: Enable LangSmith Tracing

LangSmith provides powerful tracing and debugging for your agents.

**Quick Setup:**
1. Sign up at [https://smith.langchain.com](https://smith.langchain.com)
2. Get your API key from Settings
3. Create `.env` file:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and add your API key:
   ```bash
   LANGCHAIN_API_KEY=lsv2_pt_your_api_key_here
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=langgraph-code-analysis
   ```

**See [LANGSMITH_SETUP.md](LANGSMITH_SETUP.md) for detailed instructions.**

When enabled, you'll see trace URLs after each run:
```
View trace: https://smith.langchain.com/public/...
```

### Requirements
- **langchain-core** (1.0.1) - Core LangChain functionality
- **langchain-openai** (1.0.1) - OpenAI-compatible API support
- **langgraph** (1.0.1) - Graph-based agent orchestration
- **langchain-mcp-adapters** (0.1.11) - MCP integration
- **mcp** (1.16.0) - Model Context Protocol SDK
- **ast-grep-cli** (0.39.6) - AST-based code search tool

### Local LLM Setup
The agents are configured to use a local LLM server at `http://127.0.0.1:1234`.

**Current configuration:**
```python
model = ChatOpenAI(
    model="google/gemma-3-12b",
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)
```

---

## Status

### ✅ All 3 Agents Working!

**quickstart.py** - Arithmetic agent ✅
**quickstartcode.py** - Code analysis agent (MCP version) ✅
**quickstartcode_simple.py** - Code analysis agent (CLI version) ✅

The local `google/gemma-3-12b` model supports function calling when used correctly, and MCP integration works with `MultiServerMCPClient`.

---

## Architecture

### LangGraph Pattern (Same for all agents)

```
START
  ↓
llm_call (decide tool usage)
  ↓
should_continue? (check tool calls)
  ├→ tool_node (execute tools) → llm_call (loop)
  └→ END (done)
```

### State Schema
```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
```

- `messages`: Conversation history (automatically concatenated with `operator.add`)
- `llm_calls`: Counter for LLM invocations

---

## AST-Grep Patterns

When using code analysis agents, these patterns work with Python:

```python
# Find functions (NO COLON!)
"def $FUNC($$$)"

# Find classes (NO COLON!)
"class $CLASS"

# Find imports
"import $$$"
"from $$$"

# Find decorators
"@$DECORATOR"

# Find tool definitions
"@tool"
```

**Wildcards:**
- `$VAR` - Single AST node
- `$$$` - Variable-length match (0 or more nodes)

**Important:** Don't include colons `:` in patterns - they cause parse errors!

---

## Debugging

### Enable Debug Output
Both code analysis agents have debug prints. Look for `[DEBUG]` lines in output.

### VS Code Debugging
Use `.vscode/launch.json` configuration:
```bash
F5 to start debugging
F10 to step over
F11 to step into
```

### Check Tool Execution
```bash
# Test ast-grep directly
sg --version
sg run --pattern "def $FUNC:" --lang python quickstart.py
```

---

## Next Steps

To make the code analysis agents functional:

1. **Switch to a function-calling model:**
   ```python
   # Option 1: Use OpenAI
   model = ChatOpenAI(model="gpt-4", temperature=0)

   # Option 2: Use Anthropic
   from langchain_anthropic import ChatAnthropic
   model = ChatAnthropic(model="claude-3-sonnet-20240229")

   # Option 3: Use a local model that supports function calling
   # (e.g., qwen/qwen3-coder-30b if it supports tools)
   ```

2. **Test with simple question:**
   ```python
   messages = [HumanMessage("List all functions in quickstart.py")]
   result = agent.invoke({"messages": messages, "llm_calls": 0})
   ```

3. **Verify tool execution:**
   - Check that `tool_calls` is not empty
   - Confirm tool_node is reached
   - Validate tool results are returned

---

## Examples of Questions to Ask

Once function calling works:

- "What functions are defined in quickstart.py?"
- "Find all classes in this directory"
- "Show me all the imports"
- "Find functions decorated with @tool"
- "What is the structure of the llm_call function?"

---

## Resources

- [LangChain Docs](https://docs.langchain.com/)
- [LangGraph Docs](https://docs.langchain.com/langgraph)
- [ast-grep Docs](https://ast-grep.github.io/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [ast-grep-mcp GitHub](https://github.com/ast-grep/ast-grep-mcp)
