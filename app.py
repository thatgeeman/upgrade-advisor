import logging
import shutil
from pathlib import Path

import gradio as gr
from mcp import StdioServerParameters
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter
from smolagents import InferenceClientModel

from config import (
    AGENT_MODEL,
    CHAT_HISTORY_TURNS_CUTOFF,
    CHAT_HISTORY_WORD_CUTOFF,
    GITHUB_PAT,
    GITHUB_READ_ONLY,
    GITHUB_TOOLSETS,
    HF_TOKEN,
)
from src.upgrade_advisor.agents.package import PackageDiscoveryAgent
from src.upgrade_advisor.chat.chat import (
    qn_rewriter,
    run_document_qa,
    summarize_chat_history,
)
from src.upgrade_advisor.misc import (
    _monkeypatch_gradio_save_history,
    get_example_pyproject_question,
    get_example_requirements_question,
)
from src.upgrade_advisor.theme import christmas

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# this is to use the gradio-upload-mcp server for file uploads
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
uploads_dir = uploads_dir.resolve()

_monkeypatch_gradio_save_history()


async def chat_fn(message, history, persisted_attachments=None):
    # parse incoming history is a list of dicts with 'role' and 'content' keys
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"Received message: {message}")
    logger.info(f"History: {history}")
    if len(history) > 0:
        summarized_history = await summarize_chat_history(
            history,
            turns_cutoff=CHAT_HISTORY_TURNS_CUTOFF,
            word_cutoff=CHAT_HISTORY_WORD_CUTOFF,
        )
    else:
        summarized_history = ""
    incoming_attachments = message.get("files", []) if isinstance(message, dict) else []
    persisted_attachments = persisted_attachments or []
    # If no new attachments are provided, keep using the previously persisted ones.
    attachments = incoming_attachments or persisted_attachments
    latest_attachment = attachments[-1] if attachments else []

    logger.info(f"Summarized chat history:\n{summarized_history}")
    logger.info(f"With attachments: {attachments} (incoming: {incoming_attachments})")
    logger.info(f"Latest attachment: {latest_attachment}")
    logger.info(f"Persisted attachments: {persisted_attachments}")

    # if attachements are present message is a dict with 'text' and 'files' keys
    message = message.get("text", "") if isinstance(message, dict) else message
    # overwrite messages with the text content only
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
    # add chat summary to message
    message = f"""
        CHAT SUMMARY SO FAR:
        {summarized_history}
        CURRENT QUESTION FROM USER:
        {message}
        """
    if len(attachments) > 0:
        message += """Attached FILE:\n"""
        # use the last file from the list of files only, as
        # the single file is expected to be a pyproject.toml
        # copy to uploads directory
        if latest_attachment:
            # take the last uploaded file
            source_file = latest_attachment
            file_name = f"{timestamp}_{Path(latest_attachment).name}"
        elif len(persisted_attachments) > 0:
            # take the last persisted file if no new uploads
            source_file = persisted_attachments[-1]
            file_name = f"{timestamp}_{Path(persisted_attachments[-1]).name}"
        else:
            source_file = None
            file_name = None

        logger.info(f"Copying uploaded file {source_file} to {uploads_dir}")
        shutil.copy(source_file, uploads_dir / file_name)
        message += f"""
            FILE PATH: {uploads_dir / file_name}\n
            """
    logger.info(f"Final message to agent:\n{message}")
    # Run the package discovery agent to build context
    context = agent.discover_package_info(
        user_input=message, reframed_question=rewritten_message
    )
    # Build a concise context from tool outputs
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
    }, attachments


def main():
    logger.info("Starting MCP client...")

    try:
        gh_mcp_params = dict(
            url="https://api.githubcopilot.com/mcp/",
            transport="streamable-http",
            headers={
                "Authorization": f"Bearer {GITHUB_PAT}",
                "X-MCP-Toolsets": GITHUB_TOOLSETS,
                "X-MCP-Readonly": GITHUB_READ_ONLY,
            },
        )
        # pypi_mcp_params = dict(
        #     # url="https://mcp-1st-birthday-pypi-mcp.hf.space/gradio_api/mcp/",
        #     url="https://mcp-1st-birthday-uv-pypi-mcp.hf.space/gradio_api/mcp/",
        #     transport="streamable-http",
        # )
        upload_mcp_params = StdioServerParameters(
            command="uvx",
            args=[
                "--from",
                "gradio[mcp]",
                "gradio",
                "upload-mcp",
                # Base must be the Gradio root; upload-mcp adds
                # /gradio_api/upload.
                # The docs are misleading here, it has gradio_api/upload as the base.
                "https://mcp-1st-birthday-uv-pypi-mcp.hf.space/",
                uploads_dir.as_posix(),
            ],
        )

        # pypi_mcp_client = MCPClient(
        #     server_parameters=[
        #         # pypi_mcp_params,
        #         gh_mcp_params,
        #         upload_mcp_params,
        #     ],
        #     structured_output=True,
        # )

        model = InferenceClientModel(
            token=HF_TOKEN,
            model_id=AGENT_MODEL,
        )

        # Gradio chat interface state to persist uploaded files
        files_state = gr.State([])

        with MCPAdapt(
            serverparams=[
                gh_mcp_params,
                upload_mcp_params,
            ],
            adapter=SmolAgentsAdapter(structured_output=True),
        ) as toolset:
            logger.info("MCP clients connected successfully")

            global agent
            agent = PackageDiscoveryAgent(
                model=model,
                tools=toolset,
            )
            # link package_agent to the chat function

            # attach files from local machine
            demo = gr.ChatInterface(
                fn=chat_fn,
                chatbot=gr.Chatbot(
                    height=600,
                    type="messages",
                ),
                title="Package Upgrade Advisor",
                type="messages",
                # additional_inputs_accordion="Attach pyproject.toml file",
                textbox=gr.MultimodalTextbox(
                    label="pyproject.toml",
                    file_types=[".toml"],
                    file_count="single",
                    min_width=100,
                    sources="upload",
                    inputs=files_state,
                ),
                # additional_inputs=[files_state],
                additional_outputs=files_state,
                save_history=True,
                examples=[
                    ["Tell me about the 'requests' package. How to use it with JSON ?"],
                    [get_example_requirements_question()],
                    [get_example_pyproject_question()],
                    ["Which version of 'pandas' is compatible with 'numpy' 2.0?"],
                    [
                        {
                            "text": """Can I upgrade my dependencies from
                                       the attached pyproject.toml to work with
                                       python 3.14? Any suggestions on
                                       potential issues I should be aware of?""",
                            "files": ["tests/test2.toml"],
                        }
                    ],
                ],
                stop_btn=True,
                theme=christmas,
            )
            demo.launch()

    finally:
        logger.info("Cleaning up MCP client resources")
        # remove contents of uploads_dir
        for f in uploads_dir.iterdir():
            if f.is_dir():
                try:
                    shutil.rmtree(f)
                except Exception:
                    logger.exception(f"Failed to delete uploaded directory: {f}")
            else:
                try:
                    f.unlink()
                except Exception:
                    logger.exception(f"Failed to delete uploaded file: {f}")
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
