# Neptune CLI

Command-line interface for Neptune - deploy your backend to the cloud.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install -e .
```

## Quick Start

```bash
# Login to Neptune
neptune login

# Initialize a new project
neptune init

# Deploy
neptune deploy

# Check status
neptune status
```

## MCP Server

For AI assistants (Cursor, VS Code, etc.):

```bash
neptune mcp
```

### Cursor/VS Code Configuration

```json
{
  "servers": {
    "neptune": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "PATH_TO_NEPTUNE_CLI", "neptune", "mcp"]
    }
  },
  "inputs": []
}
```

Or with HTTP transport:

```bash
neptune mcp --transport http --port 8001
```

```json
{
  "mcpServers": {
    "neptune": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

## Architecture

```
┌─────────────┐     ┌─────────────┐
│     CLI     │     │     MCP     │
│  (click)    │     │  (fastmcp)  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 │
         ┌───────▼───────┐
         │   Services    │
         │ (business     │
         │  logic)       │
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │    Client     │
         │  (API calls)  │
         └───────────────┘
```

- **Services** (`src/neptune_cli/services/`) contain all business logic
- **CLI** commands handle user interaction and output formatting
- **MCP** tools expose the same functionality to AI assistants
- Both CLI and MCP call the shared service layer, ensuring consistent behavior

## Commands

| Command      | Description                            |
| ------------ | -------------------------------------- |
| `login`      | Authenticate with Neptune              |
| `logout`     | Log out                                |
| `init`       | Initialize a new project               |
| `deploy`     | Build and deploy                       |
| `status`     | Show deployment status                 |
| `logs`       | View deployment logs                   |
| `wait`       | Wait for deployment to complete        |
| `list`       | List all projects                      |
| `delete`     | Delete a project                       |
| `resource`   | Manage databases, buckets, secrets     |
| `generate`   | Generate specs, shell completions, etc |
| `lint`       | Run AI linter on project               |
| `dockerfile` | Get Dockerfile guidance                |
| `schema`     | Show neptune.json schema               |
| `mcp`        | Start MCP server for AI assistants     |
