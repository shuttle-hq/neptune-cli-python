# neptune-cli-python

## Installation

**macOS/Linux:**

```bash
curl -fsSL https://neptune.dev/install.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://neptune.dev/install.ps1 | iex
```

## Getting Started

For Cursor, go to Cursor Settings -> Tools & MCP -> New MCP Server:

```json
{
    "mcpServers": {
        "neptune": {
            "command": "neptune",
            "args": ["mcp"]
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
