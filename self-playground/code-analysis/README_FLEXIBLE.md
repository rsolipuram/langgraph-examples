# Flexible Code Analysis Agent

**Simple, broad, and efficient LangGraph agent for code analysis**

## Philosophy

This version follows the **minimalist pattern** from `quickstartcode.py`:
- ✅ **Minimal prompting** - Let the LLM figure out what to do
- ✅ **Simple state** - Just messages and metadata
- ✅ **Fast model** - Uses qwen/qwen3-coder-30b for better speed
- ✅ **No prescription** - LLM decides how to use tools

## Key Differences from agent.py

### agent.py (Prescriptive)
```python
# Lots of guidance
system_msg = f"""Tool calls made so far: {tool_call_count}

INSTRUCTIONS:
1. If tool_calls made is 0-1: You can call tools
2. If tool_calls made is 2-3: Should prepare to finish
3. If tool_calls made is 4+: STOP NOW

BE EFFICIENT: For most queries, 1-2 tool calls...

When you have information to answer the query:
- Provide a comprehensive text response
- DO NOT call any tools...
"""
```

### agent_flexible.py (Broad)
```python
# Minimal guidance - let LLM decide
system_msg = SystemMessage(
    content=f"""You are a code analysis assistant analyzing: {repo_path}

Available tools:
- glob_tool, grep_tool, file_read_tool, treesitter_tool

Use tools to gather information, then provide your analysis."""
)
```

## Usage

```bash
python agent_flexible.py /path/to/repo "your query" --output report.md
```

### Examples

```bash
# Explain a file
python agent_flexible.py . "explain agent.py and functionality" -o analysis.md

# Find specific code
python agent_flexible.py .. "find all classes in quickstart.py" -o classes.md

# Analyze patterns
python agent_flexible.py /my/project "what design patterns are used?" -o patterns.md
```

## Performance Comparison

**Same query: "explain agent.py and functionality"**

### agent.py (Prescriptive):
- Model: google/gemma-3-12b
- Tool calls: 2 (treesitter, file_read)
- LLM calls: 3
- Time: **58 seconds**
- Report: 4,581 characters

### agent_flexible.py (Flexible):
- Model: qwen/qwen3-coder-30b
- Tool calls: 2 (glob, file_read)
- LLM calls: 3
- Time: **~15 seconds** (estimated)
- Report: 2,337 characters

## Why It's Faster

1. **Better Model**: qwen/qwen3-coder-30b is optimized for code
2. **Simpler Prompts**: Less text for LLM to process
3. **LLM Freedom**: Model makes efficient decisions
4. **No Overthinking**: Minimal guidance = faster responses

## Configuration

Edit line 24 to change the model:

```python
model = ChatOpenAI(
    model="qwen/qwen3-coder-30b",  # Change here
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed",
    temperature=0
)
```

### Recommended Models

- `qwen/qwen3-coder-30b` - Best for code (default)
- `google/gemma-3-12b` - Good general purpose
- `deepseek-coder-v2` - Excellent for code analysis
- `gpt-4` - Most capable (requires API key)

## Code Structure

**Super simple - only ~230 lines!**

```python
# State - just messages and metadata
class AnalysisState(TypedDict):
    messages: list[BaseMessage]
    repo_path: str
    output_filename: str
    llm_calls: int

# Nodes
def llm_call(state):      # LLM decides what to do
def tool_node(state):     # Execute tools
def should_continue():    # Continue or end?

# Graph - simple loop
START → llm_call ⟷ tool_node → END
```

## When to Use Which Version

### Use `agent.py` (Prescriptive) when:
- You need structured reports with specific format
- You want to control tool usage patterns
- You're analyzing large codebases (need limits)
- You need detailed progress tracking

### Use `agent_flexible.py` (Flexible) when:
- You want fast, concise answers
- You trust the LLM to make good decisions
- You're doing exploratory analysis
- You want minimal configuration

## Tools Available

All 4 tools from the main agent:

1. **glob_tool** - Find files by pattern
2. **grep_tool** - Search for exact strings
3. **file_read_tool** - Read file contents
4. **treesitter_tool** - Parse code structure

The LLM chooses which tools to use and how!

## Example Session

```bash
$ python agent_flexible.py . "what does agent.py do?" -o /tmp/out.md

🤖 Building flexible analysis agent...
📂 Repository: /path/to/code-analysis
❓ Query: what does agent.py do?
📝 Output: /tmp/out.md

============================================================
Starting analysis...
============================================================

[Step 1] llm_call
  🔧 Calling: ['glob_tool']

[Step 2] tool_node
  📊 Result: ['agent.py']

[Step 3] llm_call
  🔧 Calling: ['file_read_tool']

[Step 4] tool_node
  📊 Result: #!/usr/bin/env python3...

[Step 5] llm_call
  💭 Response: # Agent.py Analysis...

============================================================
✅ Analysis complete!
============================================================

📄 Saving analysis to: /tmp/out.md
✅ Saved 2337 characters

🔢 Total LLM calls: 3
```

## Benefits of This Approach

### 1. **Simplicity**
- Easy to understand (200 lines vs 300+)
- Easy to modify
- Easy to debug

### 2. **Speed**
- Minimal prompts = faster LLM processing
- Better model choice
- Efficient tool usage

### 3. **Flexibility**
- LLM adapts to any query type
- No rigid workflow
- Natural language understanding

### 4. **Trust the Model**
- Modern LLMs are smart
- They know when to use tools
- They can decide how much to analyze

## Limitations

- Less structured output format
- May use different tools than expected
- Shorter reports (more concise)
- No built-in retry logic

## Tips for Best Results

1. **Be Specific in Queries**
   - ✅ "explain the plan_node function in agent.py"
   - ❌ "tell me about the code"

2. **Use Natural Language**
   - ✅ "how does this agent work?"
   - ✅ "what tools are available?"
   - ✅ "find all classes"

3. **Trust the Process**
   - Let LLM choose tools
   - Don't micromanage
   - Review output quality

## Future Ideas

- [ ] Add streaming output
- [ ] Support multiple models in parallel
- [ ] Add conversation history
- [ ] Interactive mode (follow-up questions)
- [ ] Cost tracking

## License

Part of the LangGraph self-playground project.
