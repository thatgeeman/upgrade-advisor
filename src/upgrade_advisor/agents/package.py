import json
import logging
from typing import Iterator, Optional

from pydantic import BaseModel
from smolagents import CodeAgent
from smolagents.mcp_client import MCPClient

from ..schema import (  # noqa
    GithubRepoSchema,
    PackageGitHubandReleasesSchema,
    PackageInfoSchema,
    PackageSearchResponseSchema,
    PackageVersionResponseSchema,
)
from .prompts import get_package_discovery_prompt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler("package_agent.log"))

tool_schemas = {
    # pypi_search returns full PyPI payload with info + releases
    "PyPI_MCP_pypi_search": PackageSearchResponseSchema,  # corrected schema
    "PyPI_MCP_pypi_search_version": PackageVersionResponseSchema,
    "PyPI_MCP_resolve_repo_from_url": GithubRepoSchema,
    "PyPI_MCP_github_repo_and_releases": PackageGitHubandReleasesSchema,
}


def map_tool_call_to_schema(tool_name: str) -> Optional[type[BaseModel]]:
    return tool_schemas.get(tool_name, None)


# TODO: The response from the agent is not being properly
# parsed into the expected schema.
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
            add_base_tools=True,
            additional_authorized_imports=[
                "json",
                "time",
                "datetime",
                "math",
                "re",
                "typing",
                "ast",
                "packaging.version",
            ],
        )
        logger.info(f"PackageDiscoveryAgent initialized with model and tools: {tools}.")

    def _discover_package_info(
        self, user_input: str, reframed_question: str = None
    ) -> str:
        """Discover package information based on user input and return it as text.

        The smolagents runtime sometimes returns a dict (structured output),
        an AgentText (string subclass), or even None. We normalize whatever the
        agent produces into a string so downstream prompts (and logging) do not
        crash when attempting to parse the response.
        """
        prompt = get_package_discovery_prompt(user_input, reframed_question)
        logger.info(f"Running agent with max_steps: {self.agent.max_steps}.")
        try:
            result = self.agent.run(task=prompt, max_steps=self.agent.max_steps)
            logger.info(
                f"Package discovery completed successfully. \n"
                f"The return type of result: {type(result)}"
            )
            return self._normalize_agent_output(result)

        except Exception as e:
            logger.error(f"Error discovering package info: {e}")
            return f"Error occurred while discovering package info: {e}"

    def _normalize_agent_output(self, result) -> str:
        """Convert smolagents output into a robust string for downstream prompts."""
        if result is None:
            return ""

        # Avoid importing json/ast inside the generated code; normalize here instead.
        try:
            if hasattr(result, "model_dump"):
                # Pydantic models or similar objects
                try:
                    result = result.model_dump()
                except Exception:
                    logger.exception("Failed to dump model; using repr fallback.")
                    pass

            if isinstance(result, (dict, list)):
                try:
                    return json.dumps(result, indent=2, default=str)
                except Exception:
                    return str(result)

            if isinstance(result, Iterator) and not isinstance(result, (str, bytes)):
                # Materialize streaming events or generators
                materialized = list(result)
                return self._normalize_agent_output(materialized)

            return str(result)
        except Exception:
            logger.exception("Failed to normalize agent output; using repr fallback.")
            try:
                return repr(result)
            except Exception:
                return ""

    def discover_package_info(
        self, user_input: str, reframed_question: str = None
    ) -> str:
        """Public method to start package discovery."""
        return self._discover_package_info(
            user_input, reframed_question=reframed_question
        )


if __name__ == "__main__":  # Example usage of PackageDiscoveryAgent
    import os

    import dotenv
    from smolagents.models import InferenceClientModel

    dotenv.load_dotenv()

    token = os.getenv("HF_TOKEN")
    mcp_client = MCPClient(
        server_parameters=[
            {
                "url": "https://mcp-1st-birthday-pypi-mcp.hf.space/gradio_api/mcp/",
                "transport": "streamable-http",
            }
        ],
        structured_output=True,
    )

    package_agent = PackageDiscoveryAgent(
        model=InferenceClientModel(token=token), tools=mcp_client.get_tools()
    )

    user_query = "Discover information about the 'requests' package."
    logger.info(
        "Package discovery result:\n%s",
        package_agent.discover_package_info(user_query),
    )
