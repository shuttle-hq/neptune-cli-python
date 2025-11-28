# neptune-cli-python

## Prerequisites

* Python 3.13 or later
* [uv][uv] 0.9.x

## Getting Started

Make sure you are also running the `neptune-aws-platform` locally (by default this will look for it at
`localhost:8000`).

1. Usual steps to setup a uv-managed env.
2. `uv run neptune login` - follow the flow through GH to get an access token. It will be saved and used by the MCP tool
   calls.
3. Install the MCP server in a workspace using your IDE's doc. The command you need to have run is `neptune ai mcp`. You
   might need to restart the server if you've logged in after setting the MCP server up.

For example, for VSCode:

```json
{
  "servers": {
    "neptune": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--project",
        "PATH_TO_NEPTUNE_CLI",
        "neptune",
        "ai",
        "mcp"
      ]
    }
  },
  "inputs": []
}
```

Alternatively, you can run the MCP server with HTTP transport and let your local IDE connect to it:

```shell
uv run neptune ai mcp --transport=http
```

By default, the server will be available on http://0.0.0.0:8001/mcp, and the MCP configuration for Cursor will be:

```json
{
  "mcpServers": {
    "neptune": {
      "url": "http://0.0.0.0:8001/mcp"
    }
  }
}
```

[uv]: https://docs.astral.sh/uv/
