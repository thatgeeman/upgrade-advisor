import logging

import gradio as gr
from mcp import StdioServerParameters
from smolagents import CodeAgent, InferenceClientModel, MCPClient

from config import GITHUB_PAT as GITHUB_TOKEN
from config import GITHUB_TOOLSETS, HF_TOKEN
from src.upgrade_advisor.tools import resolve_repo_from_url

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


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
    gh_mcp_http_params = None
    mcp_client = MCPClient(
        server_parameters=[gh_mcp_params],
    )
    tools = mcp_client.get_tools()  # this already connects the client
    print(f"Discovered tools: {[tool.name for tool in tools]}")

    model = InferenceClientModel(
        token=HF_TOKEN,
        # model_id="meta-llama/Llama-3.1-8B-Instruct" -> prefers to use web_search
    )
    additional_authorized_imports = [
        # "requests",  # so that requests to html docs can be made
    ]

    custom_tools = [resolve_repo_from_url]
    agent = CodeAgent(
        tools=[*tools, *custom_tools],
        model=model,
        additional_authorized_imports=additional_authorized_imports,
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
        An AI assistant that helps you verify if an upgrade can be performed
        safely from one version of a software package to another, given
        all your depencencies. It uses GitHub's MCP tools to analyze the
        dependencies and check for compatibility issues.
        """,
    )

    demo.launch()

finally:
    logger.info("Disconnecting MCP client")
    try:
        mcp_client.disconnect()
    except Exception:
        pass
