"""Status command - Show project deployment status."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode, StatusResult
from neptune_cli.ui import NeptuneUI
from neptune_cli.utils import resolve_project_name


@click.command("status")
@click.option(
    "--project-name",
    help="Explicit project name to fetch status for",
)
@click.pass_context
def status_command(ctx: click.Context, project_name: str | None) -> None:
    """Show status of the current deployment."""
    from neptune_cli.services.project import get_project_status, ProjectNotFoundError

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    ui.header("Status")

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                result = StatusResult(
                    ok=False,
                    project="",
                    messages=["Could not determine project name"],
                    next_action_command="neptune init",
                )
                ui.print_json(result.model_dump())
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            return

    # Get project status using service
    try:
        status = get_project_status(project_name)
    except ProjectNotFoundError:
        if output_mode == OutputMode.JSON:
            result = StatusResult(
                ok=False,
                project=project_name,
                messages=[
                    "Project not found",
                    f"Project: {project_name}",
                    "Run 'neptune deploy' to create and deploy this project",
                ],
                next_action_command="neptune deploy",
            )
            ui.print_json(result.model_dump())
        else:
            ui.warn("Project not found")
            ui.step("", f"Project: {project_name}")
            ui.info("Run 'neptune deploy' to build and deploy this project")
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            result = StatusResult(
                ok=False,
                project=project_name,
                messages=[f"Failed to fetch project status: {e}"],
                next_action_command="neptune login",
            )
            ui.print_json(result.model_dump())
        else:
            ui.error(f"Failed to fetch project status: {e}")
            ui.info("Make sure you're logged in with 'neptune login'")
        return

    if output_mode == OutputMode.JSON:
        result = StatusResult(
            ok=True,
            project=project_name,
            condition={
                "provisioning_state": status.provisioning_state,
                "running_status": status.running_status,
                "resources": status.resources,
            },
            url=status.url,
            next_action_command="neptune status",
        )
        ui.print_json(result.model_dump())
        return

    # Human-readable output
    ui.step("", f"Project: {status.name}")
    ui.step("", f"Kind: {status.kind}")

    # Provisioning state
    state = status.provisioning_state
    if state == "Ready":
        ui.success(f"✅ Infrastructure: {state}")
    else:
        ui.step("", f"Infrastructure: {state}")

    # Running status
    running = status.running_status.get("current", "Unknown")
    if running == "Running":
        ui.success(f"✅ Service: {running}")
    elif running in ["Stopped", "Error"]:
        ui.warn(f"Service: {running}")
    else:
        ui.step("", f"Service: {running}")

    # Resources
    if status.resources:
        ui.step("", "Resources:")
        for resource in status.resources:
            res_status = resource.get("status", "Unknown")
            status_icon = "✅" if res_status == "Available" else "⏳"
            ui.step(
                "",
                f"  {status_icon} {resource.get('name')} ({resource.get('kind')}): {res_status}",
            )
            if resource.get("aws_id"):
                ui.step("", f"       AWS ID: {resource.get('aws_id')}")

    # URL if available
    if status.url:
        ui.step("", f"URL: {status.url}")

    # Overall status
    if state == "Ready" and running == "Running":
        ui.success("✅ All systems operational")
