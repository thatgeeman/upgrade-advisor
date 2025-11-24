import re
from typing import Optional

import requests
from requests import HTTPError

from src.upgrade_advisor.schema import (
    ErrorResponseSchema,
    GithubRepoSchema,
    PackageGitHubandReleasesSchema,
)

from .parse_response import (
    parse_response_pypi_search,
    parse_response_version_search,
)


async def pypi_search(
    package: str,
    cutoff: int = 10,
) -> dict:
    """
    Get metadata about the PyPI package from the PyPI Index provided the package name.

    Args:
        package (str): Name of the package to look up.
        cutoff (int): The maximum number of releases to include in the response. Defaults to 10.

    Returns:
        dict: Parsed package metadata or an error payload.
    """
    REQUEST_URL = f"https://pypi.python.org/pypi/{package}/json"
    response = requests.get(REQUEST_URL, timeout=10)
    if response.ok:
        result = parse_response_pypi_search(response.json(), cutoff=cutoff)
        return result.model_dump()

    e = HTTPError(str(response.status_code))
    return ErrorResponseSchema(error=str(e)).model_dump()


async def pypi_search_version(package: str, version: str, cutoff: int = 10) -> dict:
    """
    Get metadata about the PyPI package from the PyPI Index provided the
    package name and version.

    Args:
        package (str): Name of the package to look up.
        version (str): Version number of the released package.

    Returns:
        dict: A dictionary containing metadata about the specific
              version of the package. Returns an error message in dictionary
              form if fetching fails.
    """
    REQUEST_URL = f"https://pypi.python.org/pypi/{package}/{version}/json"
    response = requests.get(REQUEST_URL, timeout=10)
    if response.ok:
        result = parse_response_version_search(response.json(), cutoff=cutoff)
        return result.model_dump()

    e = HTTPError(str(response.status_code))
    return ErrorResponseSchema(error=str(e)).model_dump()


def resolve_repo_from_url(url: str) -> dict:
    """
    Given a GitHub repository URL, return the owner and repo name using regex.

    Args:
        url (str): The GitHub repository URL.

    Returns:
        dict: A dictionary containing the owner and repository name.
             Returns an error message if the URL is invalid.

    Example output:
        {
            "owner": "username",
            "repo": "repository-name"
        }
    """
    # add slash at end of string
    if not url.endswith("/"):
        url = f"{url}/"
    # add https if not starting with that
    if not url.startswith("http"):
        url = f"https://{url}"
    # match in groups the username and repo name -> https://regex101.com/
    pattern = r"https?://(:?www\.)?github\.com/([^/]+)/([^/]+)(?:\.git)?/?"
    matches = re.match(pattern, url)
    if matches:
        owner, repo = matches.groups()[-2:]  # take the last two matches
        # Remove .git suffix if matched
        if repo.endswith(".git"):
            repo = repo[:-4]
        return GithubRepoSchema(owner=owner, repo=repo).model_dump()

    return ErrorResponseSchema(error="Invalid GitHub repository URL.").model_dump()


async def github_repo_and_releases(
    name: str,
    cutoff: int = 10,
) -> dict:
    """Lookup the PyPI index with the package name to find the
    Github repository URL of the project and all releases published to PyPI.

    Args:
        name (str): The package name
        cutoff (int): The maximum number of releases to include in the response. Defaults to 10.
    Returns:
        dict: GitHub repository URL and releases for the package or an error payload.
    """
    result = await pypi_search(name, cutoff=cutoff)
    if result.get("error"):
        return result

    try:
        # first attempt to extract from project_urls field
        gh_url = extract_github_url(result.get("info", {}))
        if gh_url is None:
            # second attempt to extract from description field
            gh_url = extract_github_url_description(result.get("info", {}))
        # if still none, return error
        if gh_url is None:
            return ErrorResponseSchema(
                error="Could not find Github URL from PyPI metadata."
            ).model_dump()
        # get all releases
        releases = list(result.get("releases", {}).keys())
    except Exception as e:
        return ErrorResponseSchema(
            error=f"Error processing PyPI data: {str(e)}"
        ).model_dump()
    return PackageGitHubandReleasesSchema(
        name=name, url=gh_url, releases=releases
    ).model_dump()


def extract_github_url(info: dict) -> Optional[str]:
    """Extract the GitHub repository URL from the package info dictionary.

    Args:
        info (dict): The 'info' section of the PyPI package metadata.
    Returns:
        Union[str, None]: The GitHub repository URL if found, otherwise None.
    """
    gh_url = None
    gh_urls = info.get("project_urls", {})
    # candidate keys to find the URL in the dict
    keys = [
        "Source",
        "source",
        "Repository",
        "repository",
        "Homepage",
        "homepage",
        "Home",
        "home",
    ]
    for key in keys:
        url = gh_urls.get(key, "")
        if "github" in url:
            gh_url = url
            break

    return gh_url


def extract_github_url_description(info: dict) -> Optional[str]:
    """Extract the GitHub repository URL from the package description field.
    Args:
        info (dict): The 'info' section of the PyPI package metadata.
    Returns:
        Union[str, None]: The GitHub repository URL if found, otherwise None.
    """
    description = info.get("description", "")
    pattern = r"https?://(:?www\.)?github\.com/[^/\s]+/[^/\s]+(?:\.git)?/?"
    matches = re.findall(pattern, description)
    if matches:
        # Return the first matched URL
        return matches[0]
    return None
