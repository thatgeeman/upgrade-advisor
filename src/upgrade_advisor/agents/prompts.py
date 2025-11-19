import json

from ..schema import (
    GithubRepoSchema,
    PackageGitHubandReleasesSchema,
    PackageSearchResponseSchema,
    PackageVersionResponseSchema,
)


def get_package_discovery_prompt(
    original_question: str, reframed_question: str = None
) -> str:
    user_input = f"""
    USER QUESTION:
    {original_question}
    """
    if reframed_question:
        user_input += f"\nREFRAMED QUESTION (LLM-generated):\n{reframed_question}\n"

    # Add the rest of the prompt content here...
    return f"""
    You are a package discovery agent that discovers metadata about
    Python PyPI packages.

    You will be provided with user input that may contain names of Python packages
    with or without version numbers. Your task is to use the available MCP tools
    to find relevant metadata about the specified packages.

    IMPORTANT EXECUTION GUIDELINES:
    - Do NOT print intermediate tool outputs. Do not wrap results in strings or code fences.
    - Always keep tool results as Python dicts/lists. Do not serialize them unless explicitly asked.
    - Return the final structured object using: final_answer(<python_dict>)
    - Ensure the returned object STRICTLY matches the expected schema for that tool.
      Do not add or rename keys. Keep value types correct.

    NORMALIZE TOOL OUTPUTS BEFORE INDEXING:
    Tool outputs may sometimes be strings representing dicts (e.g., single-quoted) or Pydantic-like objects.
    Define these helpers AT THE TOP of your code block and use them before indexing:
    `import json, ast, re`
    Then, use this helper function below `_to_mapping` and `_extract_version_fallback` to convert tool outputs to proper mappings:

    ```python
    def _to_mapping(x):
        # Already a mapping/list
        if isinstance(x, (dict, list)):
            return x
        # Pydantic v2 model
        if hasattr(x, "model_dump"):
            try:
                return x.model_dump()
            except Exception:
                pass
        # JSON or Python-literal string
        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(x)
            except Exception:
                pass
        return x  # as-is if already usable

    def _extract_version_fallback(text):
        if not isinstance(text, str):
            return None
        m = re.search(r"['\"]version['\"]\\s*:\\s*['\"]([^'\"]+)['\"]", text)
        return m.group(1) if m else None
    ```

    - Always call _to_mapping(...) on any tool result BEFORE indexing. Example:
      d = _to_mapping(PyPI_MCP_pypi_search(package="pandas"))
      if isinstance(d, dict) and "info" in d and isinstance(d["info"], dict):
          latest = d["info"].get("version") or _extract_version_fallback(str(d))

    {user_input}

    SCHEMA DETAILS (use these exact shapes):
    - Tool: PyPI_MCP_pypi_search
      Schema: PackageSearchResponseSchema
      JSON Schema: {json.dumps(PackageSearchResponseSchema.model_json_schema())}

    - Tool: PyPI_MCP_pypi_search_version
      Schema: PackageVersionResponseSchema
      JSON Schema: {json.dumps(PackageVersionResponseSchema.model_json_schema())}

    - Tool: PyPI_MCP_resolve_repo_from_url
      Schema: GithubRepoSchema
      JSON Schema: {json.dumps(GithubRepoSchema.model_json_schema())}

    - Tool: PyPI_MCP_github_repo_and_releases
      Schema: PackageGitHubandReleasesSchema
      JSON Schema: {json.dumps(PackageGitHubandReleasesSchema.model_json_schema())}

    HINTS:
    - MCP tool outputs are often structured (Python dict/list). Use them directly.
    - If you get a string result, call _to_mapping(result) BEFORE indexing like result["info"].
    - Also be careful of the types. Some fields may be optional or missing. Some fields are ints/floats.
    - Always prefer MCP tool data over web search data for package metadata.
    - However, If you use the `web_search`, you must only rely on documentation
    from the official package website, PyPI page, or official GitHub repo.
    - If the `web_search` tool is used, ALWAYS validate the info with MCP tool data if possible.
    - NEVER fabricate data. If you cannot find the info, say so.
    - For parsing version numbers, use the `packaging.version` module. 
    - Never use ast/json modules outside the helpers; import them once at the top and only call _to_mapping / _extract_version_fallback.
    - When you have gathered the required info, call final_answer with the BEST structured object
      that answers the user query according to the appropriate schema.
    """
