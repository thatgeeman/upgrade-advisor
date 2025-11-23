from pathlib import Path

UPLOADS_DIR = Path("uploads").resolve()


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
