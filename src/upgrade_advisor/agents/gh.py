import logging

from smolagents import CodeAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class GitHubAgent:
    """Agent that interacts with GitHub repositories using MCP tools."""

    def __init__(self, model, tools=None):
        self.model = model
        if tools is None:
            tools = []
            logger.info("No tools provided; initializing with an empty toolset.")
        self.agent = CodeAgent(
            tools=tools,
            model=model,
            max_steps=10,
            additional_authorized_imports=["json", "datetime", "math", "git"],
        )
        logger.info(f"GitHubAgent initialized with model and tools: {tools}.")
