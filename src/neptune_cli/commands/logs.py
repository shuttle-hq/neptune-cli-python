"""Logs command - Show project logs."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode, CommandResult
from neptune_cli.ui import NeptuneUI, spinner
from neptune_cli.utils import resolve_project_name


@click.command("logs")
@click.option(
    "--project-name",
    help="Explicit project name to fetch logs for",
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output (not yet implemented)",
)
@click.pass_context
def logs_command(ctx: click.Context, project_name: str | None, follow: bool) -> None:
    """Show logs for the current deployment."""
    from neptune_cli.services.logs import get_logs

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    ui.header("Logs")

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                result = CommandResult(
                    ok=False,
                    messages=["Could not determine project name"],
                    next_action_command="neptune logs --project-name <name>",
                )
                ui.print_json(result.model_dump())
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            return

    # Get logs using service
    try:
        with spinner(f"Fetching logs for '{project_name}'...", output_mode):
            logs_result = get_logs(project_name)
    except Exception as e:
        if output_mode == OutputMode.JSON:
            result = CommandResult(
                ok=False,
                messages=[f"Failed to fetch logs: {e}"],
                next_action_command="neptune logs",
            )
            ui.print_json(result.model_dump())
        else:
            ui.error(f"Failed to fetch logs: {e}")
        return

    if output_mode == OutputMode.JSON:
        ui.print_json(
            {
                "ok": True,
                "project": project_name,
                "logs": logs_result.logs,
            }
        )
        return

    # Print logs
    if not logs_result.logs:
        ui.info("No logs available")
        return

    ui.step("", f"Project: {project_name}")
    click.echo()

    for line in logs_result.logs:
        click.echo(line)
