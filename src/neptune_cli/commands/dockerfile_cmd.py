"""Dockerfile command - Get Dockerfile guidance."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode
from neptune_cli.ui import NeptuneUI


@click.command("dockerfile")
@click.pass_context
def dockerfile_command(ctx: click.Context) -> None:
    """Get guidance for creating a Dockerfile.

    Analyzes the current project to detect its type and provides an
    appropriate Dockerfile template with best practices.

    This is useful when you need to create a Dockerfile for deployment
    but aren't sure how to structure it for your project type.
    """
    from neptune_cli.services.deploy import get_dockerfile_guidance

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode)

    guidance = get_dockerfile_guidance(working_dir)

    if output_mode == OutputMode.JSON:
        result = guidance.to_dict()
        result["ok"] = True
        if guidance.dockerfile_exists:
            result["status"] = "dockerfile_found"
            result["message"] = "A Dockerfile already exists. You can proceed with 'neptune deploy'."
            result["next_action_command"] = "neptune deploy"
        else:
            result["status"] = "dockerfile_needed"
            result["message"] = "No Dockerfile found. Create one using the example provided."
            result["next_action_command"] = "Create Dockerfile, then: neptune deploy"
        ui.print_json(result)
        return

    # Human-readable output
    ui.header("Dockerfile Guidance")

    if guidance.dockerfile_exists:
        ui.success("✅ Dockerfile already exists")
        ui.info("You can proceed with 'neptune deploy'")
        return

    ui.step("", f"Detected project type: {guidance.project_type}")
    if guidance.detected_files:
        ui.step("", f"Detected files: {', '.join(guidance.detected_files)}")

    if guidance.start_command:
        ui.step("", f"Detected start command: {guidance.start_command}")

    click.echo()
    ui.step("📝", "Example Dockerfile:")
    click.echo()
    for line in guidance.dockerfile_example.split("\n"):
        click.echo(f"    {line}")

    click.echo()
    ui.step("📋", "Requirements:")
    for req in guidance.requirements:
        ui.step("  •", req)

    click.echo()
    ui.step("💡", "Best Practices:")
    for practice in guidance.best_practices:
        ui.step("  •", practice)

    click.echo()
    ui.info("Create a Dockerfile in your project root, then run 'neptune deploy'")
