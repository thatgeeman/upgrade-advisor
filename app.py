import json
import logging

import gradio as gr
from mcp import StdioServerParameters
from smolagents import InferenceClientModel, MCPClient

from config import GITHUB_PAT as GITHUB_TOKEN
from config import GITHUB_TOOLSETS, HF_TOKEN
from src.upgrade_advisor.agents.package import PackageDiscoveryAgent
from src.upgrade_advisor.chat.chat import qn_rewriter, run_document_qa

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def build_context_from_events(events):
    # Build a compact textual context from structured tool outputs
    lines = []
    max_field_len = 500
    for e in events:
        # Only consider tool outputs here
        if hasattr(e, "tool_call") and hasattr(e, "output"):
            tool_call = e.tool_call
            tool_name = getattr(tool_call, "name", None) if tool_call else None
            out = getattr(e, "output", None)
            # Convert Pydantic -> dict; else keep dict/list; else str
            if hasattr(out, "model_dump"):
                data = out.model_dump()
            elif isinstance(out, (dict, list)):
                data = out
            else:
                # best-effort parse
                try:
                    data = json.loads(str(out))
                except Exception:
                    data = {"text": str(out)}

            # Redact long fields
            def shorten(v):
                if isinstance(v, str) and len(v) > max_field_len:
                    return v[:max_field_len] + "..."
                return v

            def safe_kv_pairs(obj, prefix=None):
                pairs = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, (dict, list)):
                            pairs.extend(safe_kv_pairs(v, prefix=f"{k}."))
                        else:
                            pairs.append((f"{prefix or ''}{k}", shorten(v)))
                elif isinstance(obj, list):
                    for i, v in enumerate(obj[:20]):
                        if not isinstance(v, (dict, list)):
                            pairs.append((f"item[{i}]", shorten(v)))
                return pairs

            kv = safe_kv_pairs(data)
            # Keep only key facts likely useful for QA
            key_lines = []
            for k, v in kv:
                kl = k.lower()
                if any(
                    s in kl
                    for s in [
                        "name",
                        "version",
                        "summary",
                        "home",
                        "project_urls",
                        "url",
                        "owner",
                        "repo",
                        "releases",
                    ]
                ):
                    key_lines.append(f"{k}: {v}")
            if key_lines:
                lines.append(f"[tool:{tool_name}]\n" + "\n".join(key_lines))
    return "\n".join(lines)[:8000]  # cap context length


async def chat_fn(message, history):
    message = message.strip()
    rewritten_qn = await qn_rewriter(message)
    logger.info(f"Rewritten question: {rewritten_qn}")
    # Collect events from the agent run
    events = list(package_agent.discover_package_info(rewritten_qn))
    # Build a concise context from tool outputs
    context = build_context_from_events(events)
    # Run a document QA pass using the user's question
    qa_answer = await run_document_qa(rewritten_qn, context, original_question=message)
    # Also append a short bullet summary of key facts
    lines = [qa_answer]
    if context:
        # Extract a few top lines as quick facts
        facts = [ln for ln in context.splitlines() if ":" in ln][:10]
        if facts:
            lines.append("\nKey facts:")
            lines.extend(f"- {f}" for f in facts[:10])
    return "\n".join(lines)


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
            server_parameters=[pypi_mcp_params], structured_output=True
        )
        gh_mcp_client = MCPClient(
            server_parameters=[gh_mcp_params],
            structured_output=False,  # explicitly set to silence
            # FutureWarning; set True if you need structured outputs
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
            )
            demo.launch()

    finally:
        logger.info("Disconnecting MCP client")
