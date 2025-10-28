from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from state import SourceAnalysisState
from tools import glob_tool, grep_tool, file_read_tool, treesitter_tool, save_report_tool

planner_prompt = ChatPromptTemplate.from_messages([
    ("system", "Hello"),
    ("human", "World"),
])

llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="dummy",
    model="qwen/qwen3-coder-30b", 
    temperature=0
)

print("File is syntactically correct")