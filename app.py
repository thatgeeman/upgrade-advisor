import logging

import gradio as gr
from mcp import StdioServerParameters
from smolagents import InferenceClientModel, MCPClient

from config import (
    CHAT_HISTORY_TURNS_CUTOFF,
    CHAT_HISTORY_WORD_CUTOFF,
    GITHUB_TOOLSETS,
    HF_TOKEN,
)
from config import GITHUB_PAT as GITHUB_TOKEN
from src.upgrade_advisor.agents.package import PackageDiscoveryAgent
from src.upgrade_advisor.chat.chat import (
    qn_rewriter,
    run_document_qa,
    summarize_chat_history,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


async def chat_fn(message, history):
    # parse incoming history is a list of dicts with 'role' and 'content' keys
    if len(history) > 0:
        summarized_history = await summarize_chat_history(
            history,
            turns_cutoff=CHAT_HISTORY_TURNS_CUTOFF,
            word_cutoff=CHAT_HISTORY_WORD_CUTOFF,
        )
    else:
        summarized_history = ""

    message = message.strip()
    rewritten_message, is_rewritten_good = await qn_rewriter(
        message, summarized_history
    )
    if is_rewritten_good:
        logger.info(f"Rewritten question: {rewritten_message}")
    else:
        logger.info(f"Using original question: {message}")
        rewritten_message = None
    # Collect events from the agent run
    events = package_agent.discover_package_info(
        user_input=message, reframed_question=rewritten_message
    )
    # Build a concise context from tool outputs
    # context = build_context_from_events(events)
    context = events
    logger.info(f"Built context of length {len(context)}")
    logger.info(f"Context content:\n{context}")
    # Run a document QA pass using the user's question
    qa_answer = await run_document_qa(
        question=message, context=context, rewritten_question=rewritten_message
    )
    logger.info(f"QA answer: {qa_answer}")
    return {
        "role": "assistant",
        "content": qa_answer,
    }


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

        pypi_mcp_client = MCPClient(
            server_parameters=[pypi_mcp_params, gh_mcp_params],
            structured_output=True,
        )

        with pypi_mcp_client as pypi_toolset:
            logger.info("MCP clients connected successfully")

            package_agent = PackageDiscoveryAgent(
                model=InferenceClientModel(token=HF_TOKEN),
                tools=pypi_toolset,
            )

            demo = gr.ChatInterface(
                fn=chat_fn,
                title="Python Package Discovery Agent",
                type="messages",
                save_history=True,
                examples=[
                    ["Tell me about the 'requests' package."],
                    ["What is the latest version of 'numpy'?"],
                    ["Which version of 'pandas' is compatible with 'numpy' 2.0?"],
                ],
            )
            demo.launch()

    finally:
        logger.info("Disconnecting MCP client")
