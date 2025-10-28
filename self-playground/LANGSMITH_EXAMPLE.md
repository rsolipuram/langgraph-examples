# LangSmith Tracing Example

## What You'll See in LangSmith

Once you've set up LangSmith tracing (see [LANGSMITH_SETUP.md](LANGSMITH_SETUP.md)), here's what the traces look like:

---

## Example 1: Arithmetic Agent (quickstart.py)

**Question:** "Add 3 and 4"

### Trace Overview
```
Run: Add 3 and 4
├─ Duration: 3.2s
├─ Status: Success
├─ Tokens: 345 total (250 input, 95 output)
└─ Cost: $0.0012
```

### Detailed Trace
```
┌─ Agent Graph Execution (3.2s)
│
├─ [START] → llm_call
│
├─ llm_call (1.2s)
│  └─ ChatOpenAI.invoke()
│     ├─ Model: google/gemma-3-12b
│     ├─ Input Messages:
│     │  ├─ SystemMessage: "You are a helpful assistant..."
│     │  └─ HumanMessage: "Add 3 and 4"
│     ├─ Output:
│     │  └─ AIMessage (tool_calls=[
│     │       {name: "add", args: {a: 3, b: 4}}
│     │     ])
│     ├─ Tokens: 150 input, 45 output
│     └─ Latency: 1.2s
│
├─ llm_call → tool_node (conditional edge)
│
├─ tool_node (0.3s)
│  └─ add.invoke()
│     ├─ Input: {a: 3, b: 4}
│     ├─ Output: "7"
│     └─ Latency: 0.001s (instant)
│
├─ tool_node → llm_call (edge)
│
├─ llm_call (1.5s)
│  └─ ChatOpenAI.invoke()
│     ├─ Input Messages:
│     │  ├─ SystemMessage: "You are a helpful assistant..."
│     │  ├─ HumanMessage: "Add 3 and 4"
│     │  ├─ AIMessage (with tool_call)
│     │  └─ ToolMessage: "7"
│     ├─ Output:
│     │  └─ AIMessage: "The sum of 3 and 4 is 7."
│     ├─ Tokens: 200 input, 50 output
│     └─ Latency: 1.5s
│
├─ llm_call → END (conditional edge)
│
└─ [END]
```

---

## Example 2: Code Analysis Agent (quickstartcode_simple.py)

**Question:** "What functions are defined in quickstart.py?"

### Trace Overview
```
Run: What functions are defined in quickstart.py?
├─ Duration: 4.1s
├─ Status: Success
├─ Tokens: 512 total (380 input, 132 output)
└─ Cost: $0.0018
```

### Detailed Trace
```
┌─ Agent Graph Execution (4.1s)
│
├─ [START] → llm_call
│
├─ llm_call (1.3s)
│  └─ ChatOpenAI.invoke()
│     ├─ Input Messages:
│     │  ├─ SystemMessage: "You are a helpful assistant..."
│     │  └─ HumanMessage: "What functions are defined in quickstart.py?"
│     ├─ Output:
│     │  └─ AIMessage (tool_calls=[
│     │       {name: "list_functions", args: {file_path: "quickstart.py"}}
│     │     ])
│     └─ Latency: 1.3s
│
├─ llm_call → tool_node
│
├─ tool_node (0.4s)
│  └─ list_functions.invoke()
│     ├─ Input: {file_path: "quickstart.py"}
│     ├─ Command: sg run --pattern "def $FUNC($$$)" --lang python quickstart.py
│     ├─ Output: "quickstart.py:18:def multiply(a: int, b: int)...
│     │           quickstart.py:29:def add(a: int, b: int)...
│     │           quickstart.py:40:def divide(a: int, b: int)..."
│     └─ Latency: 0.4s
│
├─ tool_node → llm_call
│
├─ llm_call (2.1s)
│  └─ ChatOpenAI.invoke()
│     ├─ Input Messages:
│     │  ├─ SystemMessage
│     │  ├─ HumanMessage: "What functions..."
│     │  ├─ AIMessage (with tool_call)
│     │  └─ ToolMessage: [full ast-grep output]
│     ├─ Output:
│     │  └─ AIMessage: "The following functions are defined:
│     │                  - multiply(a, b): Multiplies two integers
│     │                  - add(a, b): Adds two integers
│     │                  - divide(a, b): Divides two integers
│     │                  ..."
│     └─ Latency: 2.1s
│
├─ llm_call → END
│
└─ [END]
```

---

## Key Insights from Traces

### 1. **Performance Bottlenecks**
You can see that LLM calls take 1-2 seconds, while tool execution is instant (or milliseconds for ast-grep).

### 2. **Token Usage**
- First LLM call: ~150 tokens (just system + user message)
- Second LLM call: ~200-300 tokens (includes tool results)
- Total cost: ~$0.001-0.002 per question

### 3. **Tool Call Accuracy**
You can verify:
- Are the right tools being called?
- Are the arguments correct?
- Is the tool output what you expected?

### 4. **Prompt Engineering**
You can see the exact prompts sent to the LLM and iterate on them to improve results.

---

## Using Traces for Debugging

### Scenario: Tool Not Being Called

If you see traces like:
```
llm_call → END (without calling tools)
```

Check:
1. Tool descriptions - are they clear?
2. System prompt - does it encourage tool use?
3. User question - is it specific enough?

### Scenario: Wrong Tool Called

If `list_classes` is called instead of `list_functions`:
1. Check tool descriptions for overlap
2. Make descriptions more distinct
3. Add examples to tool docstrings

### Scenario: Tool Returns Empty

If tool execution shows:
```
Output: "No functions found."
```

Check:
1. File path - is it correct?
2. ast-grep pattern - does it match?
3. Test the command manually

---

## Advanced: Comparing Runs

### Experiment: Different System Prompts

Run 1 (simple):
```python
"You are a helpful assistant."
```
→ Result: Works, but verbose

Run 2 (specific):
```python
"You are a code analysis assistant. Be concise."
```
→ Result: More focused answers

Compare in LangSmith UI to see token usage and quality differences.

### Experiment: Different Models

1. Run with Gemma: See current performance
2. Run with GPT-4: Compare quality and cost
3. Run with Claude: Compare reasoning

LangSmith lets you filter and compare by model, tags, or metadata.

---

## Sharing Traces

### Public Traces

When you run an agent, you might see:
```
View trace: https://smith.langchain.com/public/abc123-def456
```

You can share this URL with anyone (no login required) to show:
- What your agent did
- How it reasoned
- What tools it used

Perfect for:
- Debugging with teammates
- Sharing examples
- Documentation

### Private Traces

All traces are private by default. Only you (and your team) can see them in your LangSmith project.

---

## Monitoring in Production

### Key Metrics to Watch

1. **Success Rate**: % of runs that complete without errors
2. **Average Latency**: How long each run takes
3. **Token Usage**: Cost per run
4. **Tool Usage**: Which tools are most/least used
5. **Error Patterns**: Common failure modes

### Setting Up Alerts

(In LangSmith UI)
1. Go to Monitoring
2. Set thresholds:
   - Alert if latency > 10s
   - Alert if error rate > 5%
   - Alert if cost > $X per day

---

## Summary

LangSmith tracing gives you:
- ✅ Complete visibility into agent behavior
- ✅ Tools for debugging and optimization
- ✅ Cost and performance monitoring
- ✅ Easy sharing and collaboration

It's especially valuable when:
- Developing new agents
- Debugging unexpected behavior
- Optimizing prompts and tools
- Monitoring production deployments

**Get started:** See [LANGSMITH_SETUP.md](LANGSMITH_SETUP.md)
