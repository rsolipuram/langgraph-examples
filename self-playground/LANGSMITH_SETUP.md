# LangSmith Tracing Setup

LangSmith provides powerful tracing and monitoring for your LangChain/LangGraph agents.

## Benefits

✅ **Visualize agent execution** - See the full trace of LLM calls and tool usage
✅ **Debug issues** - Inspect inputs, outputs, and errors in detail
✅ **Monitor performance** - Track latency, token usage, and costs
✅ **Compare runs** - See how changes affect behavior
✅ **Share traces** - Collaborate with team members

---

## Setup Steps

### 1. Create LangSmith Account

1. Go to [https://smith.langchain.com](https://smith.langchain.com)
2. Sign up for a free account
3. Navigate to Settings → API Keys
4. Create a new API key and copy it

### 2. Create `.env` File

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```bash
# LangSmith Configuration
LANGCHAIN_API_KEY=lsv2_pt_your_actual_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=langgraph-code-analysis
```

**Important:** Add `.env` to `.gitignore` to avoid committing your API key!

### 3. Verify Setup

Run either agent:
```bash
python quickstart.py
# or
python quickstartcode_simple.py
```

You should see a message at the end like:
```
View trace: https://smith.langchain.com/public/...
```

### 4. View Traces

1. Go to [https://smith.langchain.com](https://smith.langchain.com)
2. Click on your project (default: "langgraph-code-analysis")
3. You'll see all your agent runs with:
   - Execution timeline
   - LLM calls with prompts and responses
   - Tool invocations with inputs and outputs
   - Token usage and costs
   - Errors and performance metrics

---

## What Gets Traced

### Automatic Tracing (Already Enabled)

Both `quickstart.py` and `quickstartcode_simple.py` now include:

```python
from dotenv import load_dotenv
load_dotenv()  # Loads LANGCHAIN_* env vars
```

This automatically traces:
- ✅ **LLM calls** - Every model invocation with full context
- ✅ **Tool calls** - Tool selection and execution
- ✅ **Agent workflow** - Full graph execution flow
- ✅ **Errors** - Stack traces and error messages
- ✅ **Timing** - Latency for each component

### Example Trace Structure

```
Agent Run
├─ llm_call (node)
│  └─ ChatOpenAI.invoke()
│     ├─ Input: [SystemMessage, HumanMessage]
│     ├─ Output: AIMessage(tool_calls=[...])
│     ├─ Tokens: 150 input, 45 output
│     └─ Latency: 1.2s
├─ tool_node (node)
│  └─ list_functions.invoke()
│     ├─ Input: {file_path: "quickstart.py"}
│     ├─ Output: "def multiply... def add..."
│     └─ Latency: 0.3s
└─ llm_call (node)
   └─ ChatOpenAI.invoke()
      ├─ Input: [SystemMessage, HumanMessage, AIMessage, ToolMessage]
      ├─ Output: AIMessage(content="The following functions...")
      ├─ Tokens: 300 input, 80 output
      └─ Latency: 1.5s
```

---

## Customization

### Change Project Name

Edit `.env`:
```bash
LANGCHAIN_PROJECT=my-custom-project-name
```

### Disable Tracing Temporarily

Set to false or comment out:
```bash
# LANGCHAIN_TRACING_V2=false
```

### Add Metadata and Tags

You can add custom metadata to runs:

```python
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(
    tags=["production", "v1.0"],
    metadata={"user_id": "123", "session": "abc"}
)

result = agent.invoke(
    {"messages": messages, "llm_calls": 0},
    config=config
)
```

### Programmatic Access

```python
from langsmith import Client

client = Client()

# Get recent runs
runs = client.list_runs(project_name="langgraph-code-analysis", limit=10)

for run in runs:
    print(f"Run: {run.name}")
    print(f"Status: {run.status}")
    print(f"Latency: {run.latency}ms")
```

---

## Troubleshooting

### "No traces appearing"

1. Check `.env` file exists and has correct values
2. Verify `LANGCHAIN_TRACING_V2=true` (not "True" or "1")
3. Check API key is valid (starts with `lsv2_pt_`)
4. Make sure `load_dotenv()` is called before agent creation

### "Invalid API key"

1. Regenerate key at https://smith.langchain.com/settings
2. Update `.env` file
3. Restart your script

### "Traces not showing tool details"

This is normal - LangSmith shows the tool calls within the LLM invocation. Expand the ChatOpenAI nodes to see tool call details.

---

## Free Tier Limits

LangSmith free tier includes:
- 5,000 traces per month
- 30-day trace retention
- Full feature access

For most development work, this is plenty!

---

## Advanced Features

### Feedback and Annotations

Add feedback to runs:
```python
from langsmith import Client

client = Client()
client.create_feedback(
    run_id="run_id_here",
    key="correctness",
    score=0.9,
    comment="Great answer!"
)
```

### Datasets and Evaluations

Create test datasets and run evaluations:
```python
from langsmith import Client

client = Client()

# Create dataset
dataset = client.create_dataset("code-analysis-tests")

# Add examples
client.create_example(
    dataset_id=dataset.id,
    inputs={"question": "What functions are in quickstart.py?"},
    outputs={"expected": "multiply, add, divide, llm_call, tool_node, should_continue"}
)

# Run evaluation
# (see LangSmith docs for full evaluation setup)
```

### Compare Experiments

1. Change your prompt or model
2. Set a different project name or tags
3. Run the same questions
4. Use LangSmith UI to compare side-by-side

---

## Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Tracing Guide](https://docs.smith.langchain.com/tracing)
- [Evaluation Guide](https://docs.smith.langchain.com/evaluation)
- [Python Client](https://docs.smith.langchain.com/python-client)

---

## Security Note

**Never commit your `.env` file or API keys to git!**

Add to `.gitignore`:
```
.env
.env.local
*.env
```
