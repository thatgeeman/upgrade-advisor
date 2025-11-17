import logging

from smolagents import CodeAgent

from src.upgrade_advisor.schema import (
    GithubRepoSchema,
    PackageGitHubandReleasesSchema,
    PackageInfoSchema,
    PackageVersionResponseSchema,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler("package_agent.log"))

# TODO: The response from the agent is not being properly parsed into the expected schema.
# See https://github.com/huggingface/smolagents/pull/1660


class PackageDiscoveryAgent:
    """Agent that discovers metadata about Python packages using MCP tools."""

    def __init__(self, model, tools=None):
        self.model = model
        if tools is None:
            tools = []
            logger.info("No tools provided; initializing with an empty toolset.")

        self.agent = CodeAgent(
            tools=tools,
            model=model,
            max_steps=10,
            use_structured_outputs_internally=True,
            additional_authorized_imports=["json", "datetime", "math", "re", "typing"],
        )
        logger.info(f"PackageDiscoveryAgent initialized with model and tools: {tools}.")

    def discover_package_info(self, user_input: str) -> dict:
        """Discover package information based on user input."""
        prompt = f"""
        You are a package discovery agent that discovers metadata about Python PyPI packages. 
        You will be provided with user input
        that may contain names of Python packages with or without version numbers.
        Your task is to use the available MCP tools to find relevant metadata
        about the specified packages.
        ATTENTION: Here is the user input:
        {user_input}
        IMPORTANT: For each tool, there is a specific return schema that must be followed. 
        Make sure the `dict` you return from each tool call adheres to the specified schema.
        SCHEMA DETAILS:
        The tools and their corresponding response schemas are as follows:
        `PyPI_MCP_pypi_search` tool returns data in the PackageInfoSchema: {PackageInfoSchema.schema_json()}
        `PyPI_MCP_pypi_search_version` tool returns data in the PackageVersionResponseSchema: {PackageVersionResponseSchema.schema_json()}
        `PyPI_MCP_resolve_repo_from_url` tool returns data in the GithubRepoSchema: {GithubRepoSchema.schema_json()}
        `PyPI_MCP_github_repo_and_releases` tool returns data in the PackageGitHubandReleasesSchema: {PackageGitHubandReleasesSchema.schema_json()}
        """
        try:
            response = self.agent.run(prompt, max_steps=self.agent.max_steps)
            if isinstance(response, dict):
                logger.info(f"Agent response (dict): {response}")
                return response
            elif isinstance(response, str):
                import json

                logger.info(f"Agent response (str): {response}")
                return json.loads(response)
            else:
                logger.error(
                    f"Unexpected response type: {type(response)}. Expected dict or str."
                )
                raise ValueError("Unexpected response type from agent.")

        except Exception as e:
            logger.error(f"Error discovering package info: {e}")
            return {
                "name": "unknown",
                "version": "unknown",
                "summary": "Error occurred: " + str(e),
            }
