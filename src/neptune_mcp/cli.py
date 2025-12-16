import click

from neptune_mcp.auth import serve_callback_handler
from neptune_mcp.config import SETTINGS
from neptune_mcp.mcp import mcp as mcp_server


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Start a Neptune MCP server (stdio) for the current project"""
    if ctx.invoked_subcommand is None:
        mcp_server.run()


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


if __name__ == "__main__":
    cli()
