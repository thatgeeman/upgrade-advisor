import re

from smolagents import tool


@tool
def resolve_repo_from_url(url: str) -> dict:
    """Given a GitHub repository URL, return the owner and repo name.

    Args:
        url (str): The GitHub repository URL.
    """
    pattern = r"https?://github\.com/([^/]+)/([^/]+)(?:\.git)?/?"
    match = re.match(pattern, url)
    if match:
        owner, repo = match.groups()
        # Remove .git suffix if present
        if repo.endswith(".git"):
            repo = repo[:-4]
        return {"owner": owner, "repo": repo}
    else:
        raise ValueError("Invalid GitHub repository URL.")


@tool
def resolve_repo_from_name(name: str) -> dict:
    """Given a GitHub repository name, return the owner and repo name.

    Args:
        name (str): The GitHub repository name.
    """
    raise NotImplementedError("This tool is not yet implemented.")


@tool
def pypi_search(package: str, version: str) -> dict:
    """
    Lookup the PyPI repository for package information given its name and version.

    Args:
        package (str): Name of the package to lookup
        version (str): Version number of the package
    """
    raise NotImplementedError
