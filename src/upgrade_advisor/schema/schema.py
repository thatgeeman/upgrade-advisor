from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PackageInfoSchema(BaseModel):
    name: str = Field(..., description="Name of the package")
    version: str = Field(..., description="Current version of the package")
    author: Optional[str] = Field(None, description="Author of the package")
    author_email: Optional[str] = Field(None, description="Author's email address")
    description: Optional[str] = Field(None, description="Package description")
    home_page: Optional[str] = Field(None, description="Homepage URL of the package")
    requires_python: Optional[str] = Field(
        None, description="Python version requirements for the package"
    )
    requires_dist: Optional[List[str]] = Field(
        None, description="List of package dependencies"
    )
    summary: Optional[str] = Field(None, description="Short summary of the package")
    license: Optional[str] = Field(None, description="License of the package")
    keywords: Optional[str] = Field(
        None, description="Keywords associated with the package"
    )
    project_urls: Optional[Dict[str, str]] = Field(
        None, description="Additional project URLs"
    )


class PackageReleaseSchema(BaseModel):
    version: str = Field(..., description="Version of the release")
    upload_time: Optional[str] = Field(None, description="Upload time of the release")
    python_version: Optional[str] = Field(
        None, description="Python version for the release"
    )
    url: Optional[str] = Field(None, description="Download URL for the release")
    filename: Optional[str] = Field(None, description="Filename of the release package")


class PackageSearchResponseSchema(BaseModel):
    """Follows the response from the PyPI search API."""

    info: PackageInfoSchema = Field(
        ..., description="Metadata information about the package"
    )
    releases: Dict[str, PackageReleaseSchema] = Field(
        ..., description="Dictionary of releases with version as key"
    )
    last_serial: Optional[int] = Field(
        None, description="The last serial number for the package"
    )


class PackageVersionResponseSchema(BaseModel):
    info: PackageInfoSchema = Field(
        ..., description="Metadata information about the package"
    )
    urls: List[PackageReleaseSchema] = Field(
        ..., description="List of release files for the specific version"
    )
    last_serial: Optional[int] = Field(
        None, description="The last serial number for the package"
    )


class GithubRepoSchema(BaseModel):
    owner: Optional[str] = Field(None, description="Owner of the GitHub repository")
    repo: Optional[str] = Field(None, description="Name of the GitHub repository")


class PackageGitHubandReleasesSchema(BaseModel):
    name: str = Field(..., description="Name of the package")
    url: Optional[str] = Field(None, description="GitHub repository URL of the package")
    releases: Optional[List[str]] = Field(
        None, description="List of release versions of the package"
    )


class ErrorResponseSchema(BaseModel):
    error: str = Field(..., description="Error message")
