import logging
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from typing import Literal

from upgrade_advisor.agents.tools.parse_response import parse_resolved_deps
from upgrade_advisor.const import ALLOWED_OS, UV_VERSION
from upgrade_advisor.schema import (
    ResolvedDep,
    ResolveResult,
    UVResolutionResultSchema,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@contextmanager
def temp_directory():
    """Context manager that yields a temporary directory and cleans it up afterwards."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    except Exception as e:
        logger.error(f"Error creating or using temporary directory: {str(e)}")
        raise e
    finally:
        safe_remove(temp_dir)


def safe_remove(path):
    """Safely removes a file or directory if it exists."""
    if not os.path.exists(path):
        return
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)
        elif os.path.exists(path):
            logger.error(f"Path {path} exists but is neither a file nor a directory.")
            raise ValueError(
                f"Path {path} exists but is neither a file nor a directory."
            )
    except Exception as e:
        logger.error(f"Error removing path {path}: {str(e)}")
        raise e


def install_pip_package(package_name: str, version: str = None):
    """Installs a pip package using python -m pip install."""
    import subprocess

    package_spec = f"{package_name}=={version}" if version else package_name
    try:
        logger.info(f"Installing package: {package_spec}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package_spec],
        )
    except Exception as e:
        logger.error(f"Error logging package installation: {str(e)}")
        raise e


def clean_up_toml_file(toml_path: str):
    # remove any lines related to package mode and the package souce paths
    # under it  from the toml file
    with open(toml_path, "r") as f:
        toml_content = f.readlines()
    # rewrite the toml file without those lines
    with open(toml_path, "w") as f:
        skip_next = False
        for line in toml_content:
            if line.strip().startswith("package-mode"):
                # package-mode = true
                skip_next = True
                continue
            if skip_next:
                # packages = [ {include = "src/*"} ] ...
                if line.strip().startswith("packages"):
                    skip_next = False
                continue
            f.write(line)
    logger.info(f"Cleaned up temporary toml file at: {toml_path}")


def check_python_exists(version_str: str) -> str:
    """Parses a python version string and returns a standardized format."""
    import subprocess

    import packaging.version

    try:
        version = packaging.version.parse(version_str)
        if isinstance(version, packaging.version.Version):
            # check if python version is installed
            out = subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    f"import sys; print(sys.version_info[:3]) if sys.version_info[:2] == ({version.major}, {version.minor}) else None",
                ],
            )
            out = out.decode("utf-8").strip()
            if out and out != "None":
                logger.info(f"Python version {version_str} exists.")
                return True
            else:
                logger.info(f"Python version {version_str} does not exist.")
                return False
        else:
            raise ValueError(f"Invalid Python version: {version_str}")
    except packaging.version.InvalidVersion:
        raise ValueError(f"Invalid Python version: {version_str}")


def resolve_environment(
    toml_file: str,
    resolution_strategy: Literal["lowest-direct", "lowest", "highest"] = "highest",
    python_platform: Literal[ALLOWED_OS] = "linux",
    python_version: str = "3.10",
    universal: bool = False,
) -> dict:
    """
    Resolves the environment using uv tool based on the provided
    `pyproject.toml` file path and uv resolution parameters.

    Args:
        toml_file (str): Path to the pyproject.toml file.
        resolution_strategy (str): Resolution strategy to use. One of 'lowest-direct', 'lowest', 'highest'.
        python_platform (str): Target Python platform. One of the allowed OS values.
        python_version (str): Target Python version. E.g., '3.10'. Should be >= 3.8.
        universal (bool): Whether to use universal wheels. Defaults to False. Cannot be True if a specific platform is provided.
    Returns:
        dict: A dictionary containing the resolution result following UVResolutionResultSchema.
    """
    import subprocess

    import packaging.version

    errored = False
    if resolution_strategy not in [
        "lowest-direct",
        "lowest",
        "highest",
    ]:
        errored = True
        e = ValueError(
            f"Invalid resolution strategy: {resolution_strategy}. Must be one of 'lowest-direct', 'highest-direct', 'lowest', 'highest'."
        )

    # Validate python_platform and python_version
    try:
        packaging.version.parse(python_version)
    except packaging.version.InvalidVersion:
        errored = True
        e = ValueError(f"Invalid Python version: {python_version}")

    if (python_platform.lower() not in ALLOWED_OS) and not universal:
        # only validate if not universal
        errored = True
        e = ValueError(
            f"Invalid Python platform: {python_platform}. Must be one of {ALLOWED_OS}."
        )

    if not os.path.isfile(toml_file):
        errored = True
        e = FileNotFoundError(f"Toml file not found: {toml_file}")

    if errored:
        logger.error(f"Error before resolving environment: {str(e)}")
        return UVResolutionResultSchema(
            python_version=python_version,
            uv_version=UV_VERSION,
            output=ResolveResult(deps={}).model_dump(),
            errored=True,
            logs=str(e),
        ).model_dump()

    # copy the toml file to a temp directory
    with temp_directory() as temp_dir:
        temp_toml_path = os.path.join(temp_dir, "pyproject.toml")
        shutil.copy(toml_file, temp_toml_path)
        logger.info(f"Copied toml file to temporary path: {temp_toml_path}")
        # create fake readme.md in case it's required by the build system
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Temporary README\nThis is a temporary README file.")
        logger.info(f"Created temporary README at: {readme_path}")
        # clean up the toml file
        clean_up_toml_file(temp_toml_path)
        # install uv package in a virtual environment
        # curl -LsSf https://astral.sh/uv/0.9.11/install.sh | sh
        subprocess.check_call(
            [
                "bash",
                "-c",
                f"curl -LsSf https://astral.sh/uv/{UV_VERSION}/install.sh | env UV_UNMANAGED_INSTALL={temp_dir}/bin sh",
            ]
        )
        # add temp_dir to PATH
        os.environ["PATH"] = f"{temp_dir}/bin:" + os.environ["PATH"]
        logger.info(f"Added {temp_dir}/bin to PATH for uv executable.")

        venv_path = os.path.join(temp_dir, "venv")
        subprocess.check_call(
            [
                "uv",
                "venv",
                "--python",
                python_version,
                venv_path,
                "--clear",  # clear venv if exists
            ]
        )
        # activate: source /tmp/tmpxjawvuqp/venv/bin/activate but in ci/cd
        subprocess.check_call(
            ["bash", "-c", f"source {os.path.join(venv_path, 'bin', 'activate')}"]
        )
        logger.info(
            f"Created virtual environment at: {venv_path} with Python version: {python_version}"
        )
        # verify the python version in the venv (this is the new venv)
        python_executable = os.path.join(
            venv_path, "Scripts" if os.name == "nt" else "bin", "python"
        )
        out = subprocess.check_output(
            [python_executable, "--version"],
            text=True,
        )
        out = out.strip()
        logger.info(f"Python version in venv: {out}")
        logger.info(f"Required Python version: {python_version}")

        # now comes the resolution step
        # see docs; https://docs.astral.sh/uv/concepts/resolution/
        # python -m uv pip compile pyproject.toml --resolution lowest-direct
        # --universal
        # store all stdout and err to a variable which is then returned
        try:
            out = subprocess.check_output(["which", "uv"], text=True)
            logger.info(f"Using uv executable at: {out.strip()}")
            # store the output, if good or bad
            command = [
                "uv",
                "pip",
                "compile",
                temp_toml_path,
                "--resolution",
                resolution_strategy,
                "--python-version",
                python_version,
            ]
            if universal:
                command.append("--universal")
            else:
                command.extend(
                    [
                        "--python-platform",
                        python_platform,
                    ]
                )

            logger.info(f"Running uv pip compile command: {' '.join(command)}")
            out = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
            returncode = 0

        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            out = e.output
            logger.error(
                f"Error running uv pip compile: {e}\nOutput was: {out}\nReturn code: {returncode}"
            )
            errored = True

        logger.info(f"Ran uv pip compile command to get output:\n{out}")

        result = {
            "python_version": python_version,
            "uv_version": UV_VERSION,
            "output": parse_resolved_deps(out).model_dump()
            if not errored
            else ResolveResult(
                deps={"NA": ResolvedDep(name="", version="", via=[])}
            ).model_dump(),
            "errored": errored,
            "logs": out,
        }
        logger.info(f"Raw resolution result: {result}")
        # type
        logger.info(f"Result type: {type(result)}")
        # validate the result schema
        # result is json, so parse it
        result_schema = UVResolutionResultSchema(
            output=result["output"],
            errored=result["errored"],
            logs=result["logs"],
            python_version=result["python_version"],
            uv_version=result["uv_version"],
        )
        logger.info(f"Environment resolution result: {result_schema}")
        return result_schema.model_dump()


if __name__ == "__main__":
    # Example usage
    toml_path = "tests/test.toml"
    result = resolve_environment(toml_path)
    print(result)
