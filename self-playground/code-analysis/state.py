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
