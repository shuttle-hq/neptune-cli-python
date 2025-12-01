"""List command - List projects."""

from __future__ import annotations

import click

from neptune_cli.types import OutputMode, ListResult
from neptune_cli.ui import NeptuneUI, spinner


@click.command("list")
@click.argument("what", type=click.Choice(["projects"]), default="projects")
@click.pass_context
def list_command(ctx: click.Context, what: str) -> None:
    """List things in your Neptune account.

    Currently supports: projects
    """
    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    ui = NeptuneUI(output_mode, verbose=verbose)

    if what == "projects":
        _list_projects(ui, output_mode)


def _list_projects(ui: NeptuneUI, output_mode: OutputMode) -> None:
    """List all projects."""
    from neptune_cli.services.project import list_projects

    ui.header("Projects")

    try:
        with spinner("Fetching projects...", output_mode):
            projects = list_projects()
    except Exception as e:
        if output_mode == OutputMode.JSON:
            result = ListResult(
                ok=False,
                projects=[],
                messages=["Failed to fetch projects", str(e)],
                next_action_command="neptune list projects",
            )
            ui.print_json(result.model_dump())
        else:
            ui.warn("Failed to fetch projects")
            ui.step("", f"Error: {e}")
        return

    if output_mode == OutputMode.JSON:
        result = ListResult(
            ok=True,
            projects=[p.to_dict() for p in projects],
            messages=["For more details, run 'neptune status --project-name <name>'"],
            next_action_command="neptune status --project-name <name>",
        )
        ui.print_json(result.model_dump())
        return

    if not projects:
        ui.info("No projects found")
        ui.info("Run 'neptune deploy' to create and deploy your first project")
        return

    for project in projects:
        click.echo()
        ui.step("", f"Project: {project.name}")
        ui.step("", f"  Kind: {project.kind}")
        ui.step("", f"  Resources: {project.resource_count}")

        if project.url:
            ui.step("", f"  URL: {project.url}")
        else:
            ui.step("", "  URL: -")

        # Status overview
        state = project.provisioning_state
        running = project.running_status

        if state == "Ready":
            ui.success(f"  ✅ Infrastructure: {state}")
        else:
            ui.step("", f"  Infrastructure: {state}")

        if running == "Running":
            ui.success(f"  ✅ Service: {running}")
        elif running in ["Stopped", "Error"]:
            ui.warn(f"  Service: {running}")
        else:
            ui.step("", f"  Service: {running}")

        ui.step("", f"  Tip: run 'neptune status --project-name {project.name}' for details")

    click.echo()
