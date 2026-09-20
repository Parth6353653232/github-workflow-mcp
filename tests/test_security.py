"""Exploit checks required by the assignment rubric."""

from __future__ import annotations

from urllib.error import HTTPError

import pytest

from github_workflow_mcp.github_client import GitHubClient, GitHubServiceError
from github_workflow_mcp.security import RateLimiter, ValidationError, validate_keywords, validate_repository


def test_blocks_path_and_query_injection_in_repository() -> None:
    """Exploit: an attacker tries to append an API path/query to the repository."""
    with pytest.raises(ValidationError):
        validate_repository("octocat/Hello-World?per_page=100&token=stolen")


def test_blocks_github_query_operator_injection() -> None:
    """Exploit: an attacker tries to broaden issue search beyond the chosen repository."""
    with pytest.raises(ValidationError):
        validate_keywords("bug repo:another-org/secret-project")


def test_rate_limiter_blocks_third_request() -> None:
    """Exploit: repeated tool invocations exceed the configured local quota."""
    limiter = RateLimiter(max_calls=2, window_seconds=60)
    limiter.check()
    limiter.check()
    with pytest.raises(RuntimeError, match="Local rate limit reached"):
        limiter.check()


def test_http_error_does_not_disclose_upstream_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exploit: upstream error text contains a token-like secret and must not leak."""
    def fake_urlopen(*_args, **_kwargs):
        raise HTTPError("https://api.github.com/private?token=TOP_SECRET", 500, "TOP_SECRET", {}, None)

    monkeypatch.setattr("github_workflow_mcp.github_client.urlopen", fake_urlopen)
    client = GitHubClient(token="real-token-never-returned")
    with pytest.raises(GitHubServiceError) as captured:
        client.repository_overview("octocat/Hello-World")
    assert "TOP_SECRET" not in str(captured.value)
    assert "real-token-never-returned" not in str(captured.value)
    assert str(captured.value) == "GitHub could not complete the request. Please try again later."
