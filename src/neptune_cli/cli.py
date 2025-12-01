"""Neptune CLI - AI-native cloud platform for your backend.

This is the main entry point for the Neptune CLI.
"""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.config import (
    SETTINGS,
    NeptuneConfig,
    clear_auth,
    load_config,
    save_global_config,
)
from neptune_cli.types import OutputMode

# Import commands (at top level to satisfy E402)
from neptune_cli.commands.init import init_command
from neptune_cli.commands.deploy import deploy_command
from neptune_cli.commands.status import status_command
from neptune_cli.commands.list import list_command
from neptune_cli.commands.delete import delete_command
from neptune_cli.commands.lint import lint_command
from neptune_cli.commands.generate import generate_group
from neptune_cli.commands.logs import logs_command
from neptune_cli.commands.schema import schema_command
from neptune_cli.commands.resource import resource_group
from neptune_cli.commands.wait import wait_command
from neptune_cli.commands.dockerfile_cmd import dockerfile_command


# ==============================================================================
# Version
# ==============================================================================

__version__ = "0.1.0"


# ==============================================================================
# Main CLI Group
# ==============================================================================


@click.group()
@click.version_option(version=__version__, prog_name="neptune")
@click.option(
    "--debug",
    is_flag=True,
    envvar="NEPTUNE_DEBUG",
    help="Enable debug output",
)
@click.option(
    "--output",
    type=click.Choice(["normal", "json"]),
    default="normal",
    envvar="NEPTUNE_OUTPUT_MODE",
    help="Output format",
)
@click.option(
    "--working-directory",
    "--wd",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=".",
    help="Working directory for the command",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    envvar="NEPTUNE_VERBOSE",
    help="Enable verbose output",
)
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    output: str,
    working_directory: str,
    verbose: bool,
) -> None:
    """Neptune CLI - AI-native cloud platform for your backend.

    Deploy your projects to Neptune with ease.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store global options in context
    ctx.obj["debug"] = debug
    ctx.obj["output_mode"] = OutputMode(output)
    ctx.obj["working_directory"] = Path(working_directory)
    ctx.obj["verbose"] = verbose

    # Reload settings with working directory
    SETTINGS.reload(Path(working_directory))


@cli.command("mcp")
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport to use for MCP",
)
@click.option("--host", "-h", default="0.0.0.0", help="Host for HTTP transport")
@click.option("--port", "-p", default=8001, type=int, help="Port for HTTP transport")
def mcp_command(transport: str, host: str, port: int) -> None:
    """Start an MCP server for AI assistants."""
    from neptune_cli.mcp import mcp as mcp_server

    if transport == "stdio":
        mcp_server.run()
    elif transport == "http":
        mcp_server.run(transport=transport, host=host, port=port)


# ==============================================================================
# Authentication Commands
# ==============================================================================


@cli.command("login")
@click.option("--api-key", help="Log in with this API key")
@click.pass_context
def login(ctx: click.Context, api_key: str | None) -> None:
    """Authenticate with Neptune.

    Opens a browser for OAuth login, or accepts an API key directly.
    """
    from neptune_cli.ui import NeptuneUI

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    ui = NeptuneUI(output_mode)

    ui.header("Login")

    if api_key:
        # Direct API key login
        ui.step("", "Validating API key...")

        from neptune_cli.client import Client

        config_with_key = load_config(cli_overrides=NeptuneConfig(api_key=api_key))

        try:
            temp_client = Client(config=config_with_key)
            user_info = temp_client.get_current_user()
        except Exception as e:
            ui.error(f"Login failed: {e}")
            ctx.exit(1)

        # Save API key
        save_global_config(NeptuneConfig(api_key=api_key))
        SETTINGS.reload()

        user_id = user_info.get("id", "unknown")
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": True, "user_id": user_id})
        else:
            ui.success(f"✅ Logged in as {user_id}")
    else:
        # OAuth browser login
        from neptune_cli.auth import serve_callback_handler
        import webbrowser
        from urllib.parse import urlencode

        port, httpd, thread = serve_callback_handler()

        params = urlencode({"redirect_uri": f"http://localhost:{port}/callback"})
        login_url = f"{SETTINGS.api_base_url}/auth/login?{params}"

        if not webbrowser.open(login_url):
            click.echo("Please open the following URL in a browser to log in:")
            click.echo()
            click.echo(f"    {login_url}")
            click.echo()

        thread.join()

        if httpd.access_token is not None:
            save_global_config(NeptuneConfig(access_token=httpd.access_token))
            SETTINGS.reload()

            if output_mode == OutputMode.JSON:
                ui.print_json({"ok": True})
            else:
                ui.success("✅ Login successful!")
        else:
            if output_mode == OutputMode.JSON:
                ui.print_json({"ok": False, "error": "Login failed"})
            else:
                ui.error("Login failed")
            ctx.exit(1)


@cli.command("logout")
@click.pass_context
def logout(ctx: click.Context) -> None:
    """Log out of the Neptune platform."""
    from neptune_cli.ui import NeptuneUI

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    ui = NeptuneUI(output_mode)

    ui.header("Logout")

    clear_auth()
    SETTINGS.reload()

    if output_mode == OutputMode.JSON:
        ui.print_json({"ok": True})
    else:
        ui.success("Successfully logged out.")
        ui.info("Use `neptune login` to log in again.")


# ==============================================================================
# Register commands
# ==============================================================================


cli.add_command(init_command, name="init")
cli.add_command(deploy_command, name="deploy")
cli.add_command(status_command, name="status")
cli.add_command(list_command, name="list")
cli.add_command(delete_command, name="delete")
cli.add_command(lint_command, name="lint")
cli.add_command(generate_group, name="generate")
cli.add_command(logs_command, name="logs")
cli.add_command(schema_command, name="schema")
cli.add_command(resource_group, name="resource")
cli.add_command(wait_command, name="wait")
cli.add_command(dockerfile_command, name="dockerfile")


# ==============================================================================
# Entry Point
# ==============================================================================


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
