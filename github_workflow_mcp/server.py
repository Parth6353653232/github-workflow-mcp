"""MCP entry point for safe GitHub development-workflow assistance."""

from __future__ import annotations

import logging
from typing import Annotated

from mcp.server import MCPServer
from pydantic import Field

from github_workflow_mcp.github_client import GitHubClient, GitHubServiceError
from github_workflow_mcp.security import ValidationError

# Decorator registration follows the official Python SDK tutorial:
# https://py.sdk.modelcontextprotocol.io/get-started/first-steps/
mcp = MCPServer("GitHub Workflow")
client = GitHubClient()


def _tool_error(action):
    """Convert expected failures into concise, non-sensitive tool responses."""
    try:
        return action()
    except (ValidationError, GitHubServiceError, RuntimeError) as error:
        logging.getLogger(__name__).info("Safe tool failure: %s", error)
        return {"error": str(error)}


@mcp.tool()
def get_repository_overview(
    repository: Annotated[str, Field(description="A repository in owner/repository form")],
) -> dict:
    """Get read-only repository health details from GitHub for one repository."""
    return _tool_error(lambda: client.repository_overview(repository))


@mcp.tool()
def search_open_issues(
    repository: Annotated[str, Field(description="A repository in owner/repository form")],
    keywords: Annotated[str, Field(description="Plain-language issue search words; query operators are not allowed")],
    limit: Annotated[int, Field(ge=1, le=10, description="Maximum issues to return (1-10)")] = 5,
) -> dict:
    """Search a repository's open issues using a bounded, sanitized query."""
    return _tool_error(lambda: client.search_issues(repository, keywords, limit))


@mcp.prompt()
def triage_repository(
    repository: Annotated[str, Field(description="Repository in owner/repository form")],
    focus: Annotated[str, Field(description="What to prioritize, such as bugs or onboarding")] = "bugs",
) -> str:
    """Create a reusable workflow for triaging an accessible GitHub repository."""
    return (
        f"Triage the GitHub repository {repository} with a focus on {focus}. "
        "First call get_repository_overview. Then call search_open_issues with a short, "
        "plain-language search phrase related to the focus. Summarize risks, identify up to "
        "three follow-up issues, and clearly distinguish GitHub facts from recommendations."
    )


if __name__ == "__main__":
    mcp.run()

