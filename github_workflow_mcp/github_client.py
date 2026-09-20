"""Small, read-only wrapper around the GitHub REST API."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import load_github_token
from .security import RateLimiter, validate_keywords, validate_repository

LOGGER = logging.getLogger(__name__)
API_URL = "https://api.github.com"


class GitHubServiceError(RuntimeError):
    """A safe, user-facing error that never contains a token or raw response."""


class GitHubClient:
    """Make authenticated, read-only GitHub requests with local controls."""

    def __init__(self, token: str | None = None, limiter: RateLimiter | None = None) -> None:
        self._token = token if token is not None else load_github_token()
        self._limiter = limiter or RateLimiter()

    def _get(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        """GET JSON while translating upstream failures into safe messages."""
        self._limiter.check()
        url = f"{API_URL}{path}"
        if query:
            # urlencode is deliberate: it prevents query-string injection.
            url = f"{url}?{urlencode(query)}"
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "github-workflow-mcp",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=10) as response:  # nosec B310: fixed GitHub API host
                return json.load(response)
        except HTTPError as error:
            LOGGER.warning("GitHub API returned HTTP %s for %s", error.code, path)
            if error.code in {401, 403}:
                raise GitHubServiceError(
                    "GitHub rejected this request. Check that the token has read-only repository access."
                ) from None
            if error.code == 404:
                raise GitHubServiceError(
                    "Repository or issue data was not found or is not accessible to this token."
                ) from None
            raise GitHubServiceError("GitHub could not complete the request. Please try again later.") from None
        except (URLError, TimeoutError, json.JSONDecodeError):
            LOGGER.exception("GitHub request failed for %s", path)
            raise GitHubServiceError(
                "Unable to contact GitHub right now. Please try again later."
            ) from None

    def repository_overview(self, repository: str) -> dict[str, Any]:
        """Return a compact, intentionally non-sensitive repository snapshot."""
        owner, name = validate_repository(repository).split("/", maxsplit=1)
        data = self._get(f"/repos/{owner}/{name}")
        return {
            "repository": data["full_name"],
            "description": data.get("description"),
            "default_branch": data.get("default_branch"),
            "visibility": "private" if data.get("private") else "public",
            "open_issues": data.get("open_issues_count", 0),
            "stars": data.get("stargazers_count", 0),
            "primary_language": data.get("language"),
            "updated_at": data.get("updated_at"),
            "url": data.get("html_url"),
        }

    def search_issues(self, repository: str, keywords: str, limit: int) -> dict[str, Any]:
        """Search open issues in one validated repository, excluding pull requests."""
        owner, name = validate_repository(repository).split("/", maxsplit=1)
        phrase = validate_keywords(keywords)
        bounded_limit = max(1, min(limit, 10))
        query = f"repo:{owner}/{name} is:issue is:open {phrase}"
        data = self._get("/search/issues", {"q": query, "per_page": str(bounded_limit)})
        items = [
            {
                "number": item["number"],
                "title": item["title"],
                "author": item["user"]["login"],
                "labels": [label["name"] for label in item.get("labels", [])],
                "created_at": item["created_at"],
                "url": item["html_url"],
            }
            for item in data.get("items", [])
            if "pull_request" not in item
        ]
        return {"repository": f"{owner}/{name}", "query": phrase, "issues": items}

