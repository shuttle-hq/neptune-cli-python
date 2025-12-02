# Neptune MCP Installation Guide

This guide covers how to install and configure the Neptune MCP (Model Context Protocol) server across different operating systems and IDEs.

## Prerequisites

Before installing the Neptune MCP, ensure you have the following installed:

-   **Python 3.13+**
-   **[uv](https://docs.astral.sh/uv/)** (v0.9.x or later) - A fast Python package installer

### Installing uv

| OS          | Command                                                                               |
| ----------- | ------------------------------------------------------------------------------------- |
| **macOS**   | `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh`               |
| **Linux**   | `curl -LsSf https://astral.sh/uv/install.sh \| sh`                                    |
| **Windows** | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

---

## Version Pinning

By default, the configurations below install from the latest `main` branch. To pin to a specific release tag (recommended for testers), append `@<tag>` to the git URL.

### Examples

| Version         | Git URL                                                            |
| --------------- | ------------------------------------------------------------------ |
| Latest (main)   | `git+https://github.com/shuttle-hq/neptune-cli-python.git`         |
| Tag v0.1        | `git+https://github.com/shuttle-hq/neptune-cli-python.git@v0.1`    |
| Specific commit | `git+https://github.com/shuttle-hq/neptune-cli-python.git@abc1234` |

Simply replace the `--from` argument value in any configuration below. For example:

```json
"args": [
    "--isolated",
    "--from",
    "git+https://github.com/shuttle-hq/neptune-cli-python.git@v0.1",
    "neptune",
    "mcp"
]
```

> **For Testers**: Always use the specific tag version provided by the development team to ensure consistent testing results.

---

## Configuration by IDE

### Cursor

<details>
<summary><strong>macOS / Linux</strong></summary>

1. Open **Cursor Settings** → **Tools & MCP** → **New MCP Server**
2. Add the following configuration:

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

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Open **Cursor Settings** → **Tools & MCP** → **New MCP Server**
2. Add the following configuration:

```json
{
    "mcpServers": {
        "neptune": {
            "type": "stdio",
            "command": "cmd",
            "args": [
                "/c",
                "uvx",
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

**Alternative (PowerShell):**

```json
{
    "mcpServers": {
        "neptune": {
            "type": "stdio",
            "command": "powershell",
            "args": [
                "-Command",
                "uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp"
            ]
        }
    }
}
```

</details>

---

### Claude Desktop (Claude Code)

<details>
<summary><strong>macOS</strong></summary>

1. Open the config file at `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add the Neptune MCP configuration:

```json
{
    "mcpServers": {
        "neptune": {
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

3. Restart Claude Desktop

</details>

<details>
<summary><strong>Linux</strong></summary>

1. Open the config file at `~/.config/Claude/claude_desktop_config.json`
2. Add the Neptune MCP configuration:

```json
{
    "mcpServers": {
        "neptune": {
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

3. Restart Claude Desktop

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Open the config file at `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the Neptune MCP configuration:

```json
{
    "mcpServers": {
        "neptune": {
            "command": "cmd",
            "args": [
                "/c",
                "uvx",
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

3. Restart Claude Desktop

</details>

---

### VS Code (with Cline Extension)

<details>
<summary><strong>macOS / Linux</strong></summary>

1. Install the [Cline extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev) from VS Code Marketplace
2. Open VS Code Settings (`Cmd+,` on macOS, `Ctrl+,` on Linux)
3. Search for "Cline MCP" and click "Edit in settings.json"
4. Add the Neptune configuration:

```json
{
    "cline.mcpServers": {
        "neptune": {
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

5. Reload VS Code

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Install the [Cline extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev) from VS Code Marketplace
2. Open VS Code Settings (`Ctrl+,`)
3. Search for "Cline MCP" and click "Edit in settings.json"
4. Add the Neptune configuration:

```json
{
    "cline.mcpServers": {
        "neptune": {
            "command": "cmd",
            "args": [
                "/c",
                "uvx",
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

5. Reload VS Code

</details>

---

### JetBrains IDEs (IntelliJ, PyCharm, WebStorm, etc.)

JetBrains IDEs support MCP through the **AI Assistant** plugin (requires JetBrains AI subscription) or third-party plugins.

<details>
<summary><strong>macOS / Linux</strong></summary>

1. Open **Settings** → **Tools** → **AI Assistant** → **Model Context Protocol (MCP)**
2. Click **Add** to add a new MCP server
3. Configure the server:
    - **Name**: `neptune`
    - **Command**: `uvx`
    - **Arguments**: `--isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp`

**Alternative: Using HTTP transport**

1. Start the Neptune MCP server in HTTP mode:
    ```bash
    uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp --transport=http
    ```
2. In JetBrains, configure the MCP server URL: `http://localhost:8001/mcp`

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Open **Settings** → **Tools** → **AI Assistant** → **Model Context Protocol (MCP)**
2. Click **Add** to add a new MCP server
3. Configure the server:
    - **Name**: `neptune`
    - **Command**: `cmd`
    - **Arguments**: `/c uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp`

**Alternative: Using HTTP transport**

1. Start the Neptune MCP server in HTTP mode:
    ```powershell
    uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp --transport=http
    ```
2. In JetBrains, configure the MCP server URL: `http://localhost:8001/mcp`

</details>

---

### Warp Terminal

Warp supports MCP servers through its AI features.

<details>
<summary><strong>macOS</strong></summary>

1. Open Warp Settings (`Cmd+,`)
2. Navigate to **AI** → **MCP Servers**
3. Add a new server with the following configuration:

```yaml
name: neptune
command: uvx
args:
    - --isolated
    - --from
    - git+https://github.com/shuttle-hq/neptune-cli-python.git
    - neptune
    - mcp
```

**Alternative: Using config file**

Edit `~/.warp/mcp.json`:

```json
{
    "mcpServers": {
        "neptune": {
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

</details>

<details>
<summary><strong>Linux</strong></summary>

1. Open Warp Settings
2. Navigate to **AI** → **MCP Servers**
3. Add a new server with the following configuration:

```yaml
name: neptune
command: uvx
args:
    - --isolated
    - --from
    - git+https://github.com/shuttle-hq/neptune-cli-python.git
    - neptune
    - mcp
```

**Alternative: Using config file**

Edit `~/.warp/mcp.json`:

```json
{
    "mcpServers": {
        "neptune": {
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

</details>

---

## Quick Reference Matrix

| IDE / Tool          |      macOS      |      Linux      |          Windows          |
| ------------------- | :-------------: | :-------------: | :-----------------------: |
| **Cursor**          | ✅ stdio / HTTP | ✅ stdio / HTTP | ✅ stdio (via cmd) / HTTP |
| **Claude Desktop**  | ✅ stdio / HTTP | ✅ stdio / HTTP | ✅ stdio (via cmd) / HTTP |
| **VS Code (Cline)** | ✅ stdio / HTTP | ✅ stdio / HTTP | ✅ stdio (via cmd) / HTTP |
| **JetBrains**       | ✅ stdio / HTTP | ✅ stdio / HTTP | ✅ stdio (via cmd) / HTTP |
| **Warp**            | ✅ stdio / HTTP | ✅ stdio / HTTP |     ❌ Not available      |

---

## Alternative: HTTP Transport

If you experience issues with stdio transport, you can run the MCP server in HTTP mode and connect to it from any client that supports HTTP-based MCP.

### Start the HTTP Server

```bash
# macOS / Linux
uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp --transport=http

# Windows (PowerShell)
uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp --transport=http
```

The server will be available at `http://localhost:8001/mcp` by default.

### Connect via HTTP

Use this configuration in any client that supports HTTP MCP:

```json
{
    "mcpServers": {
        "neptune": {
            "url": "http://localhost:8001/mcp"
        }
    }
}
```

---

## Troubleshooting

### Common Issues

| Issue                          | Solution                                                                      |
| ------------------------------ | ----------------------------------------------------------------------------- |
| `uvx: command not found`       | Ensure `uv` is installed and in your PATH. Run `uv --version` to verify.      |
| MCP server fails to start      | Check Python version (`python --version`). Neptune requires Python 3.13+.     |
| Connection refused (HTTP mode) | Ensure the HTTP server is running before connecting. Check firewall settings. |
| Windows: Command not found     | Use `cmd /c` or `powershell -Command` wrapper as shown in Windows examples.   |
| Permissions error              | On Unix systems, ensure `uvx` is executable. Try `chmod +x $(which uvx)`.     |

### Verify Installation

Test that the MCP server starts correctly:

```bash
# Should start without errors and wait for input
uvx --isolated --from git+https://github.com/shuttle-hq/neptune-cli-python.git neptune mcp
```

Press `Ctrl+C` to stop the server.

---

## Next Steps

After installing the Neptune MCP, you can use it within your chosen coding agent - just ask!
