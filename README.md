# neptune-cli-python

## Prerequisites

* Python 3.13 or later
* [uv][uv] 0.9.x

## Getting Started


For example, for Cursor, you can go to Cursor Settings -> Tools & MCP -> New MCP Server:

```json
{
  "mcpServers": {
    "neptune": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--isolated", "--from", "git+https://github.com/shuttle-hq/neptune-cli-python.git", "neptune", "mcp"]
    }
  }
}
```

Alternatively, you can run the MCP server with HTTP transport and let your local IDE connect to it:

```shell
uv run neptune mcp --transport=http
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
