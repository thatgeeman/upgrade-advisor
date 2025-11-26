import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

from smolagents.tools import Tool

from src.upgrade_advisor.const import ALLOWED_OS, UPLOADS_DIR
from src.upgrade_advisor.schema import (
    GithubRepoSchema,
    PackageGitHubandReleasesSchema,
    PackageSearchResponseSchema,
    PackageVersionResponseSchema,
    UVResolutionResultSchema,
)

from .pypi_api import (
    github_repo_and_releases,
    pypi_search,
    pypi_search_version,
    resolve_repo_from_url,
)
from .uv_resolver import resolve_environment

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class AsyncTool(Tool):
    """A least-effort base class for defining an asynchronous tool.

    Improvements that can be made:
    - Timeout handling for async tasks.
    - Cancellation support for long-running tasks.
    """

    loop = asyncio.get_event_loop()
    task = None

    async def forward(self) -> Any:
        raise NotImplementedError(
            "AsyncTool subclasses must implement the forward method."
        )

    def async_forward(self, *args, **kwargs) -> Any:
        self.task = asyncio.create_task(self.forward(*args, **kwargs))
        try:
            # call the async forward method and wait for result
            return self.loop.run_until_complete(self.task)
        except asyncio.CancelledError as e:
            logger.error(f"Tool {self.name} execution was cancelled: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error in tool {self.name} execution: {e}")
            raise e
        finally:
            logger.info(f"Tool {self.name} execution completed.")

    def _inspect_args(self):
        import inspect

        sig = inspect.signature(self.forward)
        bound = sig.bind_partial()
        return bound.args, bound.kwargs

    def __call__(self, *args, **kwargs):
        """Stripped down call method to support async forward calls."""
        if not self.is_initialized:
            self.setup()
        encoded_inputs = self.encode(*args, **kwargs)
        # call async forward instead of forward
        # we could aalso just await here, but this way we can have a sync interface
        outputs = self.async_forward({**encoded_inputs})
        decoded_outputs = self.decode(outputs)
        return decoded_outputs


class ReadUploadFileTool(Tool):
    """Tool to safely read files saved in the `uploads` directory."""

    name = "read_upload_file"
    description = """
        Read a user-uploaded text file from the uploads directory.
        Input: `path` should be the absolute path you received (or a filename)
        under the `uploads` folder. Returns the file contents as text."""
    inputs = {
        "path": {
            "type": "string",
            "description": "Absolute or relative path to the uploaded file \
                that is present under the `uploads` directory.",
        }
    }
    output_type = "string"

    def __init__(self):
        self.upload_root = UPLOADS_DIR
        super().__init__()

    def forward(self, path: str) -> str:
        file_path = Path(path).expanduser()
        if not file_path.is_absolute():
            file_path = self.upload_root / file_path

        try:
            resolved = file_path.resolve()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"File not found: {file_path}") from exc

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")

        try:
            resolved.relative_to(self.upload_root)
        except ValueError as exc:
            raise ValueError(
                f"Refusing to read '{resolved}': \
                    not inside uploads directory {self.upload_root}"
            ) from exc

        if resolved.is_dir():
            raise IsADirectoryError(f"Refusing to read directory: {resolved}")

        return resolved.read_text(encoding="utf-8")


class WriteTomlFileTool(Tool):
    """Tool to write pyproject.toml content to a temp file."""

    name = "write_toml_file"
    description = """
        Write the provided pyproject.toml content to a temporary file.
        This is a useful tool to create a pyproject.toml file for dependency
        resolution.
        Especially if the user wants to introduce a few changes (like
        adding or updating dependencies) to the original
        pyproject.toml file before resolving dependencies.
        Also useful if the user cannot upload files directly or if the uploaded
        file has missing sections or formatting issues.
        """
    inputs = {
        "content": {
            "type": "string",
            "description": "The content of the pyproject.toml file to write.",
        }
    }
    output_type = "string"

    def __init__(self):
        self.upload_root = UPLOADS_DIR
        self.temp_dir = self.upload_root / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        super().__init__()

    def forward(self, content: str) -> str:
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".toml",
            delete=False,  # do not delete so it can be read later
            encoding="utf-8",
            dir=str(self.temp_dir),
        ) as temp_file:
            logger.info(
                f"Temporary directory exists: {os.path.exists(str(self.temp_dir))}"
            )
            temp_file.write(content)
        shutil.move(temp_file.name, str(self.temp_dir / "pyproject.toml"))
        # return as pyproject.toml
        return str(self.temp_dir / "pyproject.toml")


class ResolvePyProjectTOMLTool(Tool):
    """Tool to resolve dependencies from a pyproject.toml file using uv."""

    name = "resolve_pyproject_toml"
    description = """Using `uv` resolver, this tool takes a pyproject.toml file
        and resolves its dependencies according to the specified strategy and
        environment settings (Python version, platform, etc.). It does not
        support requirements.txt files. The file needs to be provided as an
        absolute path.
        It returns a dictionary with the schema described in `output_schema` attribute.
        """

    output_schema = UVResolutionResultSchema.schema()
    output_type = "object"
    inputs = {
        "toml_file": {
            "type": "string",
            "description": "Absolute path to the pyproject.toml file.",
        },
        "resolution_strategy": {
            "type": "string",
            "description": "Resolution strategy: 'lowest-direct', 'lowest', 'highest'.",
        },
        "python_platform": {
            "type": "string",
            "description": f"Target Python platform. One of the allowed OS values in {ALLOWED_OS}.",
        },
        "python_version": {
            "type": "string",
            "description": "Target Python version, e.g., '3.10'. Should be >= 3.8.",
        },
        "universal": {
            "type": "boolean",
            "description": "Whether to use universal wheels. Defaults to False. Cannot be True if a specific platform/OS is specified.",
        },
    }

    def __init__(self):
        super().__init__()

    def forward(
        self,
        toml_file: str,
        resolution_strategy: str,
        python_platform: str,
        python_version: str,
        universal: bool,
    ) -> dict:
        result = resolve_environment(
            toml_file=toml_file,
            resolution_strategy=resolution_strategy,
            python_platform=python_platform,
            python_version=python_version,
            universal=universal,
        )
        return result


class PypiSearchTool(AsyncTool):
    """Tool to search PyPI for package metadata."""

    name = "pypi_search"
    description = """
        Get metadata about a PyPI package by its name.
        It returns a dictionary with the schema described in `output_schema` attribute.
        """
    inputs = {
        "package": {
            "type": "string",
            "description": "Name of the package to look up on PyPI.",
        },
        "cutoff": {
            "type": "integer",
            "description": "The maximum number of releases to include in the response. Defaults to 10.",
        },
    }
    output_type = "object"
    output_schema = PackageSearchResponseSchema.schema()

    def __init__(self):
        super().__init__()

    async def forward(self, package: str, cutoff: int) -> dict:
        result = await pypi_search(package, cutoff=cutoff)
        return result


class PypiSearchVersionTool(AsyncTool):
    """Tool to search PyPI for specific package version metadata."""

    name = "pypi_search_version"
    description = """
        Get metadata about a specific version of a PyPI package. 
        It returns a dictionary with the schema described in `output_schema` attribute.
        """
    inputs = {
        "package": {
            "type": "string",
            "description": "Name of the package to look up on PyPI.",
        },
        "version": {
            "type": "string",
            "description": "Version number of the released package.",
        },
        "cutoff": {
            "type": "integer",
            "description": "The maximum number of URLs to include in the response from the end of the list. Defaults to 10.",
        },
    }
    output_type = "object"
    output_schema = PackageVersionResponseSchema.schema()

    def __init__(self):
        super().__init__()

    async def forward(self, package: str, version: str, cutoff: int) -> dict:
        result = await pypi_search_version(package, version, cutoff=cutoff)
        return result


class RepoFromURLTool(Tool):
    """Tool to extract GitHub repository information from a URL."""

    name = "repo_from_url"
    description = """
        Extract GitHub repository information from a given URL.
        Returns a dictionary containing the owner and repository name.
        It returns a dictionary with the schema described in `output_schema` attribute.
        """
    inputs = {
        "url": {
            "type": "string",
            "description": "GitHub repository URL with https:// prefix.",
        }
    }
    output_type = "object"
    output_schema = GithubRepoSchema.schema()

    def __init__(self):
        super().__init__()

    def forward(self, url: str) -> dict:
        result = resolve_repo_from_url(url)

        return result


class RepoFromPyPITool(AsyncTool):
    """Tool to extract GitHub repository information from a PyPI package."""

    name = "repo_from_pypi"
    description = """
        Extract GitHub repository information from a given PyPI package name.
        It looks up the PyPI index with the package name to find the
        Github repository URL of the project and all releases published to
        PyPI.
        Some projects may not have a GitHub repository listed in their PyPI
        metadata.
        It returns a dictionary with the schema described in `output_schema` attribute.
        """
    inputs = {
        "package": {
            "type": "string",
            "description": "Name of the PyPI package.",
        },
        "cutoff": {
            "type": "integer",
            "description": "The maximum number of releases to include in the response. Defaults to 10.",
        },
    }
    output_type = "object"
    output_schema = PackageGitHubandReleasesSchema.schema()

    def __init__(self):
        super().__init__()

    async def forward(self, package: str, cutoff: int) -> dict:
        result = await github_repo_and_releases(package, cutoff=cutoff)

        return result
