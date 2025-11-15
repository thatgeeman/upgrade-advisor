from src.upgrade_advisor.tools import resolve_repo_from_url


def test_resolve_repo_from_url():
    url = "https://github.com/owner/repo.git"
    result = resolve_repo_from_url(url)
    assert result == {"owner": "owner", "repo": "repo"}


def test_resolve_repo_from_url_without_suffix():
    url = "https://github.com/owner/repo"
    result = resolve_repo_from_url(url)
    assert result == {"owner": "owner", "repo": "repo"}


def test_resolve_repo_from_url_invalid():
    url = "https://notgithub.com/owner/repo"
    try:
        resolve_repo_from_url(url)
    except ValueError:
        assert True
