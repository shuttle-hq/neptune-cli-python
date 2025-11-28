# neptune-cli-python

## Getting Started

Make sure you are also running the `neptune-aws-platform` locally (by default this will look for it at `localhost:8000`).

1. Usual steps to setup a uv-managed env.
2. `uv run neptune login` - follow the flow through GH to get an access token. It will be saved and used by the MCP tool calls.
3. Install the MCP server in a workspace using your IDE's doc. The command you need to have run is `neptune ai mcp`. You might need to restart the server if you've logged in after setting the MCP server up.

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