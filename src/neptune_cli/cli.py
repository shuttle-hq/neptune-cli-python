import sys

import click

from neptune_cli.auth import serve_callback_handler
from neptune_cli.config import SETTINGS
from neptune_cli.mcp import mcp as mcp_server
from neptune_cli.version import check_for_update, get_current_version, is_running_as_binary


@click.group()
def cli():
    """AI-native cloud platform for your backend"""
    pass


@cli.command()
@click.option("--transport", "-t", help="Transport to use for MCP", default="stdio")
@click.option("--host", "-h", help="Host to use for MCP for HTTP transport", default="0.0.0.0")
@click.option("--port", "-p", help="Port to use for MCP for HTTP transport", default=8001)
def mcp(transport: str | None, host: str | None, port: int | None):
    """Start an MCP session for the current project"""
    if transport == "stdio":
        mcp_server.run()
    elif transport == "http":
        mcp_server.run(transport=transport, host=host, port=port)


@cli.command()
def login():
    """Authenticate with Neptune"""
    port, httpd, thread = serve_callback_handler()

    from urllib.parse import urlencode
    import webbrowser

    params = urlencode({"redirect_uri": f"http://localhost:{port}/callback"})

    login_url = f"{SETTINGS.api_base_url}/auth/login?{params}"
    if not webbrowser.open(login_url):
        print("Please open the following URL in a browser to log in:")
        print()
        print(f"    {login_url}")
        print()

    thread.join()

    if httpd.access_token is not None:
        SETTINGS.access_token = httpd.access_token
        SETTINGS.save_to_file()

    print(httpd.callback_received and "Login successful!" or "Login failed.")


@cli.command()
def version():
    """Display the current version of Neptune CLI"""
    version = get_current_version()
    print(f"neptune {version}")


@cli.command()
@click.option("--check", is_flag=True, help="Check for updates without installing")
def upgrade(check: bool):
    """Check for and install updates to Neptune CLI"""
    from neptune_cli.upgrade import perform_upgrade

    current = get_current_version()
    print(f"Current version: {current}")

    print("Checking for updates...")
    update_info = check_for_update()

    if update_info is None:
        print("Failed to check for updates. Please check your network connection.")
        sys.exit(1)

    if not update_info.update_available:
        print("You are running the latest version")
        return

    print(f"New version available: {update_info.latest_version}")

    if check:
        print("Run 'neptune upgrade' to install the update")
        return

    if not is_running_as_binary():
        print("Not running as a compiled binary")
        return

    if perform_upgrade(update_info, silent=False):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    cli()
