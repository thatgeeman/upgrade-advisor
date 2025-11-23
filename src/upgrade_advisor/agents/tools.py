import logging
from pathlib import Path

from smolagents.tools import Tool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


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

    def __init__(self, upload_root: Path):
        self.upload_root = upload_root.resolve()
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
