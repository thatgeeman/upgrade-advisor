import asyncio
import logging
import random
import threading
from typing import Any

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_lock = threading.Lock()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def get_example_questions(n: int = 3) -> str:
    requirements_question = """ Here are the contents of my requirements file:

        numpy==1.19.5
        pandas==2.1.3
        scipy==1.12.0
        opencv-python==4.8.1.78
        torch==2.1.2

        help me fix it, its giving errors
        """
    requirements_question_2 = """Here are the contents of my requirements.txt:

        numpy==1.19.5
        pandas==2.2.0
        scipy==1.12.0
        scikit-learn==1.4.2
        python-dateutil==2.8.2


        I’m on Python 3.11 and running:

        pip install -r requirements.txt

        I get this error:

        ERROR: Cannot install pandas==2.2.0 and numpy==1.19.5 because these
        package versions have conflicting dependencies

        Can you help me adjust the versions so they all work together on Python
        3.11, and explain how you picked them?"""
    pyproject_question = """
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
    requiments_question_apple = """Here’s my requirements.txt:

        torch==2.1.2
        torchvision==0.16.0
        torchaudio==2.1.2
        numpy==1.26.2


        I’m on a MacBook with Apple Silicon (M2), Python 3.10, using:

        pip install -r requirements.txt

        I get errors about no matching wheel for torch:

        ERROR: Could not find a version that satisfies the requirement torch==2.1.2

        How should I change these dependencies so they work correctly on M2,
        and what install commands should I use?"""

    upgraded_python_question = """I had a project running on Python 3.8 with
                               this requirements.txt:

        numpy==1.20.0
        pandas==1.2.3
        scikit-learn==0.24.1
        xgboost==1.4.0


        I upgraded my system to Python 3.12 and tried:

        pip install -r requirements.txt

        Now I get multiple errors about incompatible versions and missing wheels.

        I’d like to:

        Make this environment work on Python 3.12

        Keep roughly the same libraries, but I’m fine upgrading to newer
        compatible versions

        Can you propose updated versions for these packages that work on Python
        3.12 and explain any major breaking changes I should watch for?"""

    pip_confusion_question = """I’m using Poetry, but I also ran pip install
                             manually a few times and now things are broken.

        My pyproject.toml dependencies:

        [tool.poetry.dependencies]
        python = "^3.10"
        fastapi = "^0.95.0"
        uvicorn = "^0.22.0"


        pip list shows different versions:

        fastapi 0.100.0

        uvicorn 0.23.0

        When I run poetry run uvicorn app.main:app, I get import errors like:

        ImportError: cannot import name 'FastAPI' from 'fastapi'

        Can you explain what’s going on with Poetry vs pip in this situation,
        and give me a clear set of steps to get back to a consistent
        environment?"""

    all_questions = [
        requirements_question,
        requirements_question_2,
        pyproject_question,
        requiments_question_apple,
        upgraded_python_question,
        pip_confusion_question,
    ]
    choices = random.sample(all_questions, k=n)
    # format as list of lists for gradio examples
    choices = [[q] for q in choices]

    return choices


def to_openai_message_format(role: str, content: str, append_to: list = None) -> dict:
    message = {
        "role": role,
        "content": [
            {
                "type": "text",
                "text": content,
            }
        ],
    }
    if append_to is not None:
        # if its supposed to be appended to a list
        append_to.append(message)
        return append_to
    return message


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


def run_coro_sync(coro) -> Any:
    """Run an async coroutine and return its result from sync code.

    - If no event loop is running: use asyncio.run().
    - If a loop is already running: dispatch to a dedicated background loop.
    """
    try:
        loop = asyncio.get_running_loop()
        loop_running = loop.is_running()
    except RuntimeError:
        loop = None
        loop_running = False

    # No loop: safest case
    if not loop_running:
        return asyncio.run(coro)

    # Loop already running: use background loop in another thread
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            _bg_loop = asyncio.new_event_loop()
            _bg_thread = threading.Thread(
                target=_bg_loop.run_forever,
                name="async-tool-background-loop",
                daemon=True,
            )
            _bg_thread.start()

        bg_loop = _bg_loop

    future = asyncio.run_coroutine_threadsafe(coro, bg_loop)
    return future.result()
