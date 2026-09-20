"""Configuration loading for the GitHub Workflow MCP server."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is unavailable."""


def load_github_token() -> str:
    """Load the GitHub token from a project-local .env file or environment.

    ``Path`` keeps the configuration location independent of the terminal's
    current directory.  ``.env`` is intentionally excluded from Git.
    """
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token or token == "replace_with_your_github_token":
        raise ConfigurationError(
            "GitHub authentication is not configured. Add GITHUB_TOKEN to .env."
        )
    return token

