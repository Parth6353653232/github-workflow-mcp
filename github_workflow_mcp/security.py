"""Validation, rate-limiting, and safe error helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
import re


class ValidationError(ValueError):
    """Raised for input that is outside this server's narrow allowlist."""


REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,38})/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})$"
)
KEYWORDS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._+#-]{0,117}$")


def validate_repository(repository: str) -> str:
    """Accept exactly a GitHub ``owner/repository`` identifier.

    An allowlist rejects path traversal, URL fragments, and query modifiers
    before a value can be incorporated into a GitHub API path.
    """
    candidate = repository.strip()
    if not REPOSITORY_PATTERN.fullmatch(candidate):
        raise ValidationError(
            "Repository must use the form 'owner/repository' with GitHub-safe characters."
        )
    return candidate


def validate_keywords(keywords: str) -> str:
    """Allow a small, human-readable search phrase, not GitHub query operators."""
    candidate = keywords.strip()
    if not KEYWORDS_PATTERN.fullmatch(candidate):
        raise ValidationError(
            "Keywords may contain letters, numbers, spaces, '.', '_', '+', '#', or '-'."
        )
    return candidate


@dataclass
class RateLimiter:
    """A process-local sliding-window rate limiter for model-initiated calls."""

    max_calls: int = 12
    window_seconds: float = 60.0
    _calls: deque[float] = field(default_factory=deque, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def check(self) -> None:
        """Record a request or raise without contacting GitHub."""
        now = monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] >= self.window_seconds:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls:
                raise RuntimeError(
                    "Local rate limit reached. Wait one minute before making more requests."
                )
            self._calls.append(now)

