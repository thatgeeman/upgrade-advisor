import json

from ..schema import (
    GithubRepoSchema,
    PackageGitHubandReleasesSchema,
    PackageSearchResponseSchema,
    PackageVersionResponseSchema,
)


def get_package_discovery_prompt(user_input: str) -> str:
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
    Define and use this helper to safely convert to a Python dict before indexing:

    def _to_mapping(x):
        import json, ast
        # Already a mapping
        if isinstance(x, dict):
            return x
        # Pydantic v2 model
        if hasattr(x, "model_dump"):
            try:
                return x.model_dump()
            except Exception:
                pass
        # JSON or Python-literal string
        if isinstance(x, str):
            try:
                return json.loads(x)
            except Exception:
                try:
                    return ast.literal_eval(x)
                except Exception:
                    pass
        return x  # as-is if already usable

    ATTENTION: User query to solve:
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
    - When you have gathered the required info, call final_answer with the BEST structured object
      that answers the user query according to the appropriate schema.
    """
