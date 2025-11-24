import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def get_example_requirements_question() -> str:
    return """
    Here are the contents of my requirements file:

    numpy==1.19.5
    pandas==2.1.3
    scipy==1.12.0
    opencv-python==4.8.1.78
    torch==2.1.2

    help me fix it, its giving errors
    """


def get_example_pyproject_question() -> str:
    return """
    Here are the contents of my pyproject.toml file:

    [tool.poetry]
    name = "example-project"
    version = "0.1.0"
    description = "An example Python project"
    authors = ["Your Name <your.email@example.com>"]

    [tool.poetry.dependencies]
    python = "^3.8"
    numpy = "^1.21.0"
    pandas = "^1.3.0"
    requests = "^2.26.0"
    fastapi = "^0.70.0"
    uvicorn = "^0.15.0"

    [tool.poetry.dev-dependencies]
    pytest = "^6.2.5"
    black = "^21.9b0"

    Help me identify any potential package upgrade issues.
    I wish to upgrade numpy to version 1.23.0 and pandas to version 1.5.0.
    """


def _monkeypatch_gradio_save_history():
    """Guard against non-int indices in Gradio's chat history saver.

    Gradio 5.49.1 occasionally passes a component (e.g., Textbox) as the
    conversation index when save_history=True, which raises a TypeError. We
    coerce unexpected index types to None so Gradio inserts a new conversation
    instead of erroring.
    """
    import gradio as gr

    if getattr(gr.ChatInterface, "_ua_safe_patch", False):
        return

    original = gr.ChatInterface._save_conversation

    def _safe_save_conversation(self, index, conversation, saved_conversations):
        if not isinstance(index, int):
            index = None
        try:
            return original(self, index, conversation, saved_conversations)
        except Exception:
            logger.exception("Failed to save chat history; leaving history unchanged.")
            return index, saved_conversations

    gr.ChatInterface._save_conversation = _safe_save_conversation
    gr.ChatInterface._ua_safe_patch = True
