import ast
import json
import logging
from typing import Any, Iterator, Optional

from pydantic import BaseModel
from smolagents import CodeAgent, ToolCall, ToolOutput
from smolagents.agents import StreamEvent
from smolagents.mcp_client import MCPClient
from smolagents.memory import ActionStep, FinalAnswerStep, PlanningStep
from smolagents.models import ChatMessageStreamDelta, ChatMessageToolCall

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


def to_event_schema(evt: Any) -> Optional[StreamEvent]:
    """Convert various event types to standardized StreamEvent schemas."""
    if isinstance(
        evt,
        (
            ChatMessageStreamDelta,
            PlanningStep,
            ActionStep,
            ToolCall,
        ),
    ):
        return evt

    # Tool output (result from a tool execution)
    if isinstance(evt, ToolOutput):
        tool_call = getattr(evt, "tool_call", None)
        tool_name = getattr(tool_call, "name", None) if tool_call is not None else None
        schema = map_tool_call_to_schema(tool_name) if tool_name else None

        # Normalize output to a Python object first
        raw_output = getattr(evt, "output", None)
        normalized_output = raw_output
        """
        IMPORTANT:
        Thing to note is that the MCP can
        return outputs in different formats:
        - JSON strings (e.g., '{"key": "value"}')
        - Python-literal strings (e.g., "{'key': 'value'}")
        - Direct Python objects (e.g., dicts, lists)
        We need to handle these cases to convert them into a consistent Python object.
        """
        if isinstance(raw_output, str):
            # Try JSON first
            try:
                normalized_output = json.loads(raw_output)
            except Exception:
                # Fallback to Python-literal parsing (single-quoted dicts)
                try:
                    normalized_output = ast.literal_eval(raw_output)
                except Exception:
                    logger.warning(
                        f"Failed to parse tool output string for tool '{tool_name}'. Returning raw output."
                    )
                    normalized_output = raw_output  # keep as-is if not parseable

        # if dict or list, keep as is
        parsed_output = normalized_output
        if schema is not None:
            try:
                # Pydantic v2: model_validate; fallback to parse_obj for v1
                if hasattr(schema, "model_validate"):
                    parsed_output = schema.model_validate(normalized_output)
                else:
                    parsed_output = schema.parse_obj(normalized_output)
                logger.info(
                    f"Successfully parsed tool output for tool '{tool_name}' into schema '{schema.__name__}'."
                )
            except Exception as e:
                logger.warning(
                    f"Failed to parse tool output for tool '{tool_name}' into schema '{schema.__name__}': {e}. Returning normalized output."
                )

        # Return a new ToolOutput with normalized output and original tool_call
        return ToolOutput(
            id=getattr(evt, "id", ""),
            output=parsed_output,
            is_final_answer=getattr(evt, "is_final_answer", False),
            observation=getattr(evt, "observation", None),
            tool_call=tool_call,
        )

    # Final answer
    if isinstance(evt, FinalAnswerStep):
        output = getattr(evt, "output", None)
        return FinalAnswerStep(output=output)

    # ChatMessageToolCall (non-streaming tool call object sometimes yielded by models)
    if isinstance(evt, ChatMessageToolCall):
        func = getattr(evt, "function", None)
        name = getattr(func, "name", None)
        arguments = getattr(func, "arguments", None)
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                logger.warning(
                    f"Failed to parse arguments string for tool '{name}'. Returning raw arguments."
                )
                pass
        return ToolCall(
            id=getattr(evt, "id", None),
            name=name,
            arguments=arguments,
        )

    # Ignore unknown event types or return None
    return None


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
            additional_authorized_imports=[
                "json",
                "datetime",
                "math",
                "re",
                "typing",
                "ast",
                "packaging.version",
            ],
        )
        logger.info(f"PackageDiscoveryAgent initialized with model and tools: {tools}.")

    def _discover_package_info(self, user_input: str) -> Iterator[StreamEvent]:
        """Discover package information based on user input.

        Yields StreamEvent items as the agent runs (planning, action, tool calls,
        tool outputs, final answer, and streaming deltas). Each yielded event
        can be normalized further by the caller if needed.
        """
        prompt = get_package_discovery_prompt(user_input)
        logger.info(f"Running agent with max_steps: {self.agent.max_steps}.")
        try:
            for event in self.agent.run(
                prompt,
                max_steps=self.agent.max_steps,
                stream=True,
            ):
                normalized = to_event_schema(event)
                if normalized is not None:
                    yield normalized

        except Exception as e:
            logger.error(f"Error discovering package info: {e}")
            yield {
                "name": "unknown",
                "version": "unknown",
                "summary": "Error occurred: " + str(e),
            }

    def discover_package_info(self, user_input: str):
        """Public method to start package discovery."""
        return self._discover_package_info(user_input)


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
    for event in package_agent.discover_package_info(user_query):
        logger.info(f"Agent Event: {event}")
