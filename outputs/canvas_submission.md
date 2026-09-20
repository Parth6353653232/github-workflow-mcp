# Canvas submission: GitHub Workflow MCP Server

> Replace the GitHub URL placeholder below after creating a **private** repository and granting the instructor/TA access. Submit this document to Canvas; do not commit it to the repository.

| GitHub link | Domain choice | Two implemented best practices |
| --- | --- | --- |
| `https://github.com/Parth6353653232/github-workflow-mcp` | Development Workflow | Input sanitization; rate limiting |

## Architecture diagram

```text
┌──────────────────┐     stdio / MCP      ┌────────────────────────────────────┐
│ Claude Desktop   │ ───────────────────▶ │ GitHub Workflow MCP Server (Python)│
│ (MCP host/client)│ ◀─────────────────── │                                    │
└──────────────────┘   tool results/prompt │  ┌──────────────┐                 │
                                             │  │ MCP handlers │                 │
                                             │  │ • overview   │                 │
                                             │  │ • issue search│                │
                                             │  │ • triage prompt│               │
                                             │  └──────┬───────┘                 │
                                             │         ▼                          │
                                             │  ┌─────────────────────────────┐  │
                                             │  │ Security boundary           │  │
                                             │  │ allowlist validation        │  │
                                             │  │ 12 calls / 60 sec limiter   │  │
                                             │  │ safe error translation      │  │
                                             │  └──────┬──────────────────────┘  │
                                             │         ▼                          │
                                             │  ┌─────────────────────────────┐  │
                                             │  │ GitHubClient                │  │
                                             │  │ • loads GITHUB_TOKEN from   │  │
                                             │  │   ignored .env via pathlib  │  │
                                             │  │ • HTTPS GET only            │  │
                                             │  └──────────────┬──────────────┘  │
                                             └────────────────┼─────────────────┘
                                                              ▼
                                                   ┌──────────────────┐
                                                   │ GitHub REST API  │
                                                   └──────────────────┘
```

## Reflection

### What challenges did you encounter?

The main challenge was connecting a useful external service without giving an LLM more power than the assignment needed. GitHub’s API has many write endpoints, but using them would require much stronger confirmation and permission design. I also needed to decide how errors should behave: raw GitHub failures can include implementation details or sensitive request information, but a vague error makes the server hard to use. I addressed this by logging technical failures locally and returning a clear, generic message to the MCP client. Finally, authentication required care because the token must be available to the server but must never be committed or shown during the demo.

### How did you decide the level of abstraction? How did you decide what should be a single tool vs. multiple tools?

I chose repository overview and open-issue search as separate tools because they answer different questions and have different inputs. An overview is a bounded metadata lookup that is useful as the first step of almost any repository conversation. Issue search needs keywords, builds a constrained query, and returns a list that can be analyzed. Combining them would force every overview to run a search and would make the tool’s inputs and output harder for the model to understand. The `triage_repository` prompt is not a third action; it is a user-invoked workflow that tells the model how to sequence the two smaller tools. This keeps each tool focused and makes the server easier to test and explain.

### What are the limitations of your server, and how would you improve it?

The server is read-only and focuses only on repository metadata and open issues; it does not inspect pull-request diffs, commits, workflow runs, or private organizations unless the token permits access. Its rate limit is process-local, so it resets whenever the server restarts and does not coordinate between multiple server instances. Search syntax is intentionally limited, which protects the chosen repository but makes advanced GitHub searches unavailable. In a production version, I would add per-user identity-aware limits, durable audit logs that avoid storing secrets, token rotation, more granular permissions, pagination, and an explicit confirmation flow for any future write operation. I would also add integration tests against a dedicated test repository and provide observability metrics for failures and quota usage.
