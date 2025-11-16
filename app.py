import logging

import gradio as gr
from mcp import StdioServerParameters
from smolagents import CodeAgent, InferenceClientModel, MCPClient

from config import GITHUB_PAT as GITHUB_TOKEN
from config import GITHUB_TOOLSETS, HF_TOKEN

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

if __name__ == "__main__":
    logger.info("Starting MCP client for GitHub MCP server")
    logger.info(f"Using toolsets: {GITHUB_TOOLSETS}")

    try:
        gh_mcp_params = StdioServerParameters(
            # for StdioServerParameters, we use podman to run the
            # MCP server from GH in a container
            command="podman",
            args=[
                "run",
                "-i",
                "--rm",
                "-e",
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "-e",
                "GITHUB_READ_ONLY",
                "-e",
                "GITHUB_TOOLSETS",
                "ghcr.io/github/github-mcp-server",
            ],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN,
                "GITHUB_READ_ONLY": "1",
                "GITHUB_TOOLSETS": GITHUB_TOOLSETS,
            },
        )
        pypi_mcp_params = dict(
            url="https://mcp-1st-birthday-pypi-mcp.hf.space/gradio_api/mcp/",
            transport="streamable-http",
        )

        with MCPClient(
            server_parameters=[gh_mcp_params, pypi_mcp_params],
            structured_output=True,
        ) as tools:
            print(f"Discovered tools: {[tool.name for tool in tools]}")

            model = InferenceClientModel(
                token=HF_TOKEN,
                # model_id="meta-llama/Llama-3.1-8B-Instruct",  # -> prefers to use web_search
            )
            additional_authorized_imports = [
                # "requests",  # so that requests to html docs can be made
            ]

            agent = CodeAgent(
                tools=[*tools],
                model=model,
                additional_authorized_imports=additional_authorized_imports,
                max_steps=25,
            )

            demo = gr.ChatInterface(
                fn=lambda message, history: str(agent.run(message)),
                type="messages",
                examples=[
                    """
                    Currently, I'm using pandas version 1.3.0 in my project.
                    I want to upgrade to version 2.0.0.
                    Here is my dependency list:
                    pandas==1.3.0, numpy==1.21.0, matplotlib==3.4.2.
                    Can you help me determine if this upgrade is safe and what
                    potential issues I might face?",
                    """
                ],
                title="Upgrade Assistant with MCP Tools",
                description="""
                As an AI dependancy checker that investigates each library and its
                dependancy chain
                to check if an upgrade that the user requested can be performed
                safely without causing deprecations, security vulnerabilities
                or obsolete version clashes.
                It uses GitHub's MCP tools and the PyPI MCP tools to analyze the
                dependencies and check for compatibility issues.
                Finally a report is written
                clearly stating why the upgrade is or is not reccomended.
                """,
            )

            demo.launch()

    finally:
        logger.info("Disconnecting MCP client")
