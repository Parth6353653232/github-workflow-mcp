# GitHub Workflow MCP Server

A small, read-only **Development Workflow** MCP server that connects an MCP host (such as Claude Desktop) to the GitHub REST API. It offers two model-controlled tools and one user-controlled prompt:

| MCP primitive | Name | Purpose |
| --- | --- | --- |
| Tool | `get_repository_overview` | Return a compact repository-health snapshot. |
| Tool | `search_open_issues` | Search open issues in one repository. |
| Prompt | `triage_repository` | Guide Claude through a focused repository triage. |

## Why this design

The two tools are deliberately separate: the overview is a low-cost metadata lookup, while issue search has a separate query and returns a different kind of information. Neither tool writes to GitHub, which makes the demo safer and keeps the server narrowly scoped. The prompt coordinates them without granting the model any additional capability.

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)
- A GitHub fine-grained personal access token with **read-only** access to the repositories you intend to demo

## Setup with uv

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and replace the placeholder with your GitHub token. `.env` is in `.gitignore`; do not commit it or paste the token into Claude Desktop screenshots. The program finds the project-local `.env` with `pathlib.Path`, so it works even when launched from another working directory.

## Run and test

Run the exploit checks before the demo:

```bash
uv run pytest -q
```

Start the server through the MCP Inspector:

```bash
uv run mcp dev github_workflow_mcp/server.py
```

For a direct stdio run, use:

```bash
uv run python github_workflow_mcp/server.py
```

Try `get_repository_overview` with `octocat/Hello-World`, and `search_open_issues` with `octocat/Hello-World`, `bug`, and `5`. Use a repository accessible to your token for the final demo.

## Claude Desktop configuration

`claude_desktop_config.json` is the complete configuration for this workspace. Copy its `github-workflow` server object into Claude Desktop's MCP configuration location. It starts the server as a Python module and supplies the project import path; the project-local `.env` supplies the token, so it is not duplicated in Claude Desktop's settings. If you relocate the repository, use `claude_desktop_config.example.json` as a template and replace the absolute paths. Restart Claude Desktop after saving.

Example with this workspace's current location:

```json
{
  "mcpServers": {
    "github-workflow": {
      "command": "/Users/parthchandak/Documents/Codex/2026-09-20/this-course-involves-a-lot-of-2/.venv/bin/python",
      "args": ["-m", "github_workflow_mcp.server"]
    }
  }
}
```

## Security and best-practice evidence

### 1. Input sanitization

- Repository inputs must exactly match `owner/repository`; a strict allowlist blocks paths, query strings, and URL fragments.
- Search terms have a narrow character allowlist, so GitHub query operators such as `repo:` cannot override the repository chosen by the caller.
- `urllib.parse.urlencode` safely encodes the final GitHub query parameter.

**Exploit demonstration:** `pytest` runs `test_blocks_path_and_query_injection_in_repository` using `octocat/Hello-World?per_page=100&token=stolen`, and `test_blocks_github_query_operator_injection` using `bug repo:another-org/secret-project`. Both inputs raise `ValidationError` before any network request.

### 2. Rate limiting

`RateLimiter` permits 12 server-side GitHub requests per 60-second sliding window. It is lock-protected so concurrent requests cannot bypass the count. The tool returns a safe message instead of reaching GitHub after the quota is exhausted.

**Exploit demonstration:** `test_rate_limiter_blocks_third_request` configures a two-call window, makes two allowed calls, and proves that the third raises `Local rate limit reached`.

### Also included: safe error disclosure

The HTTP wrapper logs technical detail locally but sends only a concise user-facing message to the MCP client. The test `test_http_error_does_not_disclose_upstream_secret` places `TOP_SECRET` in a simulated upstream error and verifies that it never reaches the tool result.

## Code sources and attribution

- The MCP decorator structure (`MCPServer`, `@mcp.tool()`, and `@mcp.prompt()`) follows the official [MCP Python SDK first-steps guide](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/). The relevant source citation is also included beside the decorators in `github_workflow_mcp/server.py`.
- GitHub request headers and the REST endpoint conventions follow the [GitHub REST API documentation](https://docs.github.com/en/rest). This project writes its own request, validation, rate-limiting, and error-handling logic.

## Demo checklist

1. Activate `.venv`, show `uv run pytest -q` passing.
2. Briefly show the two exploit tests and their blocked input/rate-limit behavior.
3. Launch `uv run mcp dev github_workflow_mcp/server.py`.
4. In Claude Desktop, show the two tools and `triage_repository` prompt; invoke the prompt with an accessible repository.
5. Confirm that no token is visible on screen.

The assignment table, architecture diagram, and reflections are intentionally in the separate Canvas submission file, not this repository.
