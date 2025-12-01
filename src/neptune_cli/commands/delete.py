"""Delete command - Delete a project."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode, CommandResult
from neptune_cli.ui import NeptuneUI, confirm, spinner
from neptune_cli.utils import resolve_project_name


@click.command("delete")
@click.option(
    "--project-name",
    help="Explicit project name to delete",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def delete_command(ctx: click.Context, project_name: str | None, yes: bool) -> None:
    """Delete a project and all its resources."""
    from neptune_cli.services.project import (
        delete_project,
        get_project_status,
        ProjectNotFoundError,
    )

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    ui.header("Delete")

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                result = CommandResult(
                    ok=False,
                    messages=["Could not determine project name"],
                    next_action_command="neptune delete --project-name <name>",
                )
                ui.print_json(result.model_dump())
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            return

    # Check if project exists and get info for confirmation
    try:
        status = get_project_status(project_name)
    except ProjectNotFoundError:
        if output_mode == OutputMode.JSON:
            result = CommandResult(
                ok=False,
                messages=[f"Project '{project_name}' not found"],
                next_action_command="neptune list projects",
            )
            ui.print_json(result.model_dump())
        else:
            ui.warn(f"Project '{project_name}' not found")
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            result = CommandResult(
                ok=False,
                messages=[f"Failed to get project info: {e}"],
                next_action_command="neptune delete",
            )
            ui.print_json(result.model_dump())
        else:
            ui.error(f"Failed to get project info: {e}")
        return

    # Confirm deletion
    if not yes and output_mode != OutputMode.JSON:
        ui.step("", f"Project: {project_name}")
        ui.step("", f"Resources: {len(status.resources)}")
        ui.warn("This will permanently delete the project and all its resources!")

        if not confirm("Are you sure you want to delete this project?", default=False):
            ui.step("", "Aborted")
            return

    # Delete the project
    try:
        with spinner(f"Deleting project '{project_name}'...", output_mode):
            delete_project(project_name)
    except ProjectNotFoundError:
        if output_mode == OutputMode.JSON:
            result = CommandResult(
                ok=False,
                messages=[f"Project '{project_name}' not found"],
                next_action_command="neptune list projects",
            )
            ui.print_json(result.model_dump())
        else:
            ui.warn(f"Project '{project_name}' not found")
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            result = CommandResult(
                ok=False,
                messages=[f"Failed to delete project: {e}"],
                next_action_command="neptune delete",
            )
            ui.print_json(result.model_dump())
        else:
            ui.error(f"Failed to delete project: {e}")
        return

    if output_mode == OutputMode.JSON:
        result = CommandResult(
            ok=True,
            messages=[f"Project '{project_name}' deleted successfully"],
            next_action_command="neptune list projects",
        )
        ui.print_json(result.model_dump())
    else:
        ui.success(f"✅ Project '{project_name}' deleted successfully")
