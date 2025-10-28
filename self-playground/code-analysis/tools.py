
import os
import glob
import subprocess
import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
import itertools

@tool
def glob_tool(pattern: str, repo_path: str) -> List[str]:
    """
    Finds all file paths relative to the repo root matching a glob pattern.
    Example: "**/*.py" or "src/**/package.xml"
    """
    original_cwd = os.getcwd()
    os.chdir(repo_path)
    try:
        return glob.glob(pattern, recursive=True)
    finally:
        os.chdir(original_cwd)

@tool
def grep_tool(query: str, repo_path: str, path_glob: str = "**/*") -> List[Dict[str, Any]]:
    """
    Uses 'ripgrep' (rg) to find exact string matches in files.
    'query' is the literal string to search for (e.g., "class User").
    'path_glob' is a glob pattern to restrict the search (e.g., "**/*.py").
    Returns a JSON list of matches.
    """
    try:
        command = [
            'rg',
            '--json',
            '-e', query,
            '-g', path_glob,
            repo_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        matches = []
        for line in result.stdout.strip().split('\n'):
            matches.append(json.loads(line))
        return matches
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return [{"error": str(e)}]

@tool
def file_read_tool(path: str, repo_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    Reads the full content or a specific line range of a file.
    'path' is the relative file path from the repo root.
    If 'start_line' and 'end_line' are provided, reads only that range.
    """
    file_path = os.path.join(repo_path, path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if start_line is None or end_line is None:
                return f.read()
            else:
                # Adjust for 1-based line numbers
                start_line = max(0, start_line - 1)
                return "".join(itertools.islice(f, start_line, end_line))
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def treesitter_tool(path: str, repo_path: str, treesitter_query: str) -> List[str]:
    """
    Uses tree-sitter to parse a file and extract all nodes matching a query.

    Example queries for Python:
    - All function names: "(function_definition name: (identifier) @name)"
    - All class names: "(class_definition name: (identifier) @name)"
    - All imports: "(import_statement) @import"

    Returns a list of the text content of all matching nodes.
    """
    try:
        from tree_sitter import Language, Parser, Query, QueryCursor
        import tree_sitter_python as tspython

        # Load Python language
        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)

        # Read the file
        file_path = os.path.join(repo_path, path)
        with open(file_path, 'rb') as f:
            source_code = f.read()

        # Parse the file
        tree = parser.parse(source_code)

        # Execute the query
        query = Query(PY_LANGUAGE, treesitter_query)
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        # Extract text from captured nodes
        results = []
        for pattern_index, captures_dict in matches:
            for capture_name, nodes in captures_dict.items():
                for node in nodes:
                    text = source_code[node.start_byte:node.end_byte].decode('utf-8')
                    results.append(text)

        return results if results else ["No matches found"]

    except ImportError as e:
        return [f"Error: tree-sitter not installed. Run: pip install tree-sitter tree-sitter-python"]
    except Exception as e:
        return [f"Error parsing file: {str(e)}"]

# The spec mentions using WriteFileTool, which we will instantiate in the agent
from langchain_community.tools.file_management import WriteFileTool
save_report_tool = WriteFileTool()
