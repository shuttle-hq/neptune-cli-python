# neptune-cli-python

## Prerequisites

-   Python 3.13 or later
-   [uv][uv] 0.9.x

## Getting Started

For example, for Cursor, you can go to Cursor Settings -> Tools & MCP -> New MCP Server:

```json
{
    "mcpServers": {
        "neptune": {
            "type": "stdio",
            "command": "uvx",
            "args": [
                "--isolated",
                "--from",
                "git+https://github.com/shuttle-hq/neptune-cli-python.git",
                "neptune",
                "mcp"
            ]
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

## Local Development

To test local changes to the MCP server, update your MCP config to point to your local repo:

```json
{
    "mcpServers": {
        "neptune": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/path/to/neptune-cli-python",
                "neptune",
                "mcp"
            ]
        }
    }
}
```

Replace `/path/to/neptune-cli-python` with the absolute path to your local clone.

After updating the config, restart Cursor (or reload the MCP server) for changes to take effect.

You can also verify the MCP server starts correctly from the terminal:

```shell
uv run neptune mcp
```

[uv]: https://docs.astral.sh/uv/
