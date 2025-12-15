# Development guidelines

## Prerequisites

Required:

- Python 3.13 or later
- [uv][1] 0.9.x

Optional:

- [mise][2] to set up local tooling
- [pre-commit][3] hooks to ensure consistent code style

## Getting Started

Run `uv sync` to download the dependencies and set up a virtual environment.

To test local changes to the MCP server, update your MCP config to point to your
local repo:

```json
{
  "mcpServers": {
    "neptune": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/neptune-mcp",
        "neptune",
        "mcp"
      ]
    }
  }
}
```

Replace `/path/to/neptune-mcp` with the absolute path to your local clone.

After updating the config, restart Cursor (or reload the MCP server) for changes
to take effect.

You can also verify the MCP server starts correctly from the terminal:

```shell
uv run neptune mcp
```

You can also run the MCP server with HTTP transport and let your local IDE
connect to it:

```shell
uv run neptune mcp --transport=http
```

By default, the server will be available on http://0.0.0.0:8001/mcp, and the MCP
configuration for Cursor will be:

```json
{
  "mcpServers": {
    "neptune": {
      "url": "http://0.0.0.0:8001/mcp"
    }
  }
}
```

If you want to run it in the [MCP Inspector][4], execute the following command:

```shell
npx @modelcontextprotocol/inspector uv run neptune mcp
```

<!-- External links -->

[1]: https://docs.astral.sh/uv/

[2]: https://mise.jdx.dev/

[3]: https://pre-commit.com/

[4]: https://modelcontextprotocol.io/docs/tools/inspector
