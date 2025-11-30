import logging

from upgrade_advisor.schema import (
    PackageInfoSchema,
    PackageReleaseSchema,
    PackageSearchResponseSchema,
    PackageVersionResponseSchema,
    ResolvedDep,
    ResolveResult,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def parse_response_pypi_search(
    data: dict, cutoff: int = 10
) -> PackageSearchResponseSchema:
    """
    Parse the JSON response from the PyPI search API into a Pydantic model.

    Args:
        data (dict): The JSON response from the PyPI search API.
        cutoff (int): The maximum number of releases to include in the response. Defaults to 10.
    Returns:
        PackageSearchResponseSchema: A Pydantic model containing metadata about the package.
    """
    info = data.get("info", {})
    releases = dict(list(data.get("releases", {}).items())[-cutoff:])
    last_serial = data.get("last_serial", 0)

    # create the info
    info = PackageInfoSchema(**info)
    # create the releases
    parsed_releases = {}
    for version, release_list in releases.items():
        # the whl and tar.gz contain the same info and are placed in a list
        try:
            release = release_list[0]
        except IndexError:
            release = {}
        parsed_release_list = PackageReleaseSchema(version=version, **release)
        parsed_releases[version] = parsed_release_list

    # create the final response model
    parsed_response = PackageSearchResponseSchema(
        info=info,
        releases=parsed_releases,
        last_serial=last_serial,
    )
    return parsed_response


def parse_response_version_search(
    data: dict, cutoff: int = 10
) -> PackageVersionResponseSchema:
    """
    Parse the JSON response from the PyPI version search API.

    Args:
        data (dict): The JSON response from the PyPI version search API.
        cutoff (int): The maximum number of URLs to include in the response from the end of the list. Defaults to the last 10.
    Returns:
        PackageVersionResponseSchema: A Pydantic model containing metadata about the specific version of the package.
    """
    info = data.get("info", {})
    urls = data.get("urls", [])[-cutoff:]  # get only the last `cutoff` entries
    last_serial = data.get("last_serial", 0)
    # create the info
    info = PackageInfoSchema(**info)
    # create the urls
    parsed_urls = []
    for url_info in urls:
        parsed_url = PackageReleaseSchema(
            version=url_info.get("version", ""),  # this is empty in the url info
            **url_info,
        )
        parsed_urls.append(parsed_url)
    parsed_response = PackageVersionResponseSchema(
        info=info,
        urls=parsed_urls,
        last_serial=last_serial,
    )
    return parsed_response


def parse_resolved_deps(data: str) -> ResolveResult:
    """
    Parse the resolved dependencies from the output string of a uv resolution command.

    Args:
        data (str): The output string containing resolved dependencies.
    Returns:
        ResolveResult: A ResolveResult model containing resolved dependencies.
    """
    resolved_deps = []
    current_dep = None
    lines = data.splitlines()
    for line_number, line in enumerate(lines):
        # skip 2 lines
        if line_number < 2:
            continue
        # one liner:
        #    # via pydantic
        # could also be:
        #    # via
        #    #    pydantic=1.10.7
        #    #    packaging=23.1
        # if begins with ascii character
        if not line.lower().strip().startswith("#"):
            direct_dep = line.strip()
            # pycparser==2.23 ; implementation_name != 'PyPy' and platform_python_implementation != 'PyPy'
            direct_dep_metainfo = direct_dep.rsplit(";", 1)
            direct_dep = direct_dep_metainfo[0].strip().split("==")
            direct_dep_name = direct_dep[0] if len(direct_dep) > 0 else direct_dep
            direct_dep_version = direct_dep[1] if len(direct_dep) > 1 else ""
            logger.info(
                f"Parsed direct dependency: {direct_dep_name}=={direct_dep_version}"
            )
            resolved_dep = ResolvedDep(
                name=direct_dep_name,
                version=direct_dep_version,
                via=[],  # will be filled later
                metainfo=direct_dep_metainfo[1].strip()
                if len(direct_dep_metainfo) > 1
                else "",
            )
            resolved_deps.append(resolved_dep)
            current_dep = direct_dep_name
            continue
        else:
            if line.replace("    #", "").strip() == "via":
                continue
            indirect_dep = line.replace("    #", "").replace("via", "").strip()
            if current_dep is not None:
                resolved_deps[-1].update_indirect_dep(indirect_dep)
                logger.info(
                    f"Updated indirect dependency for {current_dep}: {indirect_dep}"
                )
    logger.info(f"Total resolved dependencies parsed: {len(resolved_deps)}")
    logger.debug(f"Resolved dependencies details: {resolved_deps}")
    return ResolveResult(deps={dep.name: dep for dep in resolved_deps})
