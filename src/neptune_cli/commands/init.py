"""Init command - Initialize a new Neptune project."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.client import get_client
from neptune_cli.types import OutputMode, TEMPLATES
from neptune_cli.ui import NeptuneUI, confirm, prompt_input, prompt_select
from neptune_cli.utils import clone_repo, write_project_metadata


@click.command("init")
@click.option(
    "--from",
    "from_url",
    help="Clone a template from a git repository URL",
)
@click.option(
    "--subfolder",
    help="Path to the template in the source (used with --from)",
)
@click.option(
    "--no-git",
    is_flag=True,
    help="Don't initialize a new git repository",
)
@click.argument("path", default=".", type=click.Path())
@click.pass_context
def init_command(
    ctx: click.Context,
    from_url: str | None,
    subfolder: str | None,
    no_git: bool,
    path: str,
) -> None:
    """Initialize a new Neptune project.

    Creates a new project from a template or initializes the current directory.
    """
    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    ui = NeptuneUI(output_mode, verbose=ctx.obj.get("verbose", False))

    ui.header("Init")

    # Get project name
    project_name = prompt_input("Project name")
    if not project_name:
        ui.error("Project name is required")
        raise click.Abort()

    target_dir = Path(path).resolve()

    # If --from was provided, use that template
    if from_url:
        # Determine target directory
        if path == ".":
            default_path = Path.cwd() / project_name
            target_dir = Path(prompt_input("Directory", default=str(default_path))).resolve()
        else:
            target_dir = Path(path).resolve()

        # Check if directory is not empty
        if target_dir.exists() and any(target_dir.iterdir()):
            if not confirm("Target directory is not empty. Are you sure?"):
                ui.step("", "Aborted")
                return

        ui.step("", f"Cloning template into {target_dir}")

        try:
            clone_repo(from_url, target_dir, subfolder, remove_git=not no_git)
        except Exception as e:
            ui.error(f"Failed to clone template: {e}")
            raise click.Abort()

        write_project_metadata(target_dir, project_name)

        # Generate AGENTS.md
        _generate_agents_md(target_dir, ui, output_mode)

        ui.success("✅ Project initialized")
        ui.step("", f"Path: {target_dir}")

        if Path.cwd() != target_dir:
            click.echo("You can `cd` to the directory, then:")
        click.echo("Run `neptune deploy` to deploy it.")
        return

    # Interactive template selection
    choices = ["Current working directory", "Choose from templates"]
    choice = prompt_select("Where do you want to initialize?", choices)

    if choice == 0:
        # Initialize in current directory
        cwd = Path.cwd()
        ui.step("", f"Initializing in {cwd}")
        write_project_metadata(cwd, project_name)
        _generate_agents_md(cwd, ui, output_mode)

        ui.success("✅ Project initialized in current directory")
        click.echo("Run `neptune deploy` to deploy it.")
    else:
        # Choose from templates
        template_items = [f"{t.name}  ({t.url})" for t in TEMPLATES]
        idx = prompt_select("Choose a template", template_items)
        selected = TEMPLATES[idx]

        # Target directory
        target_dir = Path.cwd() / project_name

        # Check if directory exists and is not empty
        if target_dir.exists() and any(target_dir.iterdir()):
            if not confirm("Target directory is not empty. Are you sure?"):
                click.echo("Aborted.")
                return

        ui.step("", f"Cloning template '{selected.name}' into {target_dir}")

        try:
            clone_repo(selected.url, target_dir, remove_git=not no_git)
        except Exception as e:
            ui.error(f"Failed to clone template: {e}")
            raise click.Abort()

        write_project_metadata(target_dir, project_name)
        _generate_agents_md(target_dir, ui, output_mode)

        ui.success("✅ Project initialized")
        ui.step("", f"Path: {target_dir}")

        if Path.cwd() != target_dir:
            click.echo("You can `cd` to the directory, then:")
        click.echo("Run `neptune deploy` to deploy it.")


def _generate_agents_md(directory: Path, ui: NeptuneUI, output_mode: OutputMode) -> None:
    """Generate or update AGENTS.md in the project directory."""
    import re

    try:
        client = get_client()
        agents_content = client.get_agents_md()
    except Exception as e:
        ui.warn(f"Could not fetch AGENTS.md content: {e}")
        return

    agents_file = directory / "AGENTS.md"

    # Extract version from content
    version_pattern = r"<!-- neptune: agents\.md version ([^>]+) -->.*?<!-- neptune end -->"
    match = re.search(version_pattern, agents_content, re.DOTALL)
    if not match:
        ui.warn("Could not detect AGENTS.md version")
        return

    remote_version = match.group(1)

    if agents_file.exists():
        existing_content = agents_file.read_text()
        existing_match = re.search(version_pattern, existing_content, re.DOTALL)

        if existing_match:
            existing_version = existing_match.group(1)
            if existing_version >= remote_version:
                ui.success("✅ AGENTS.md up to date")
                return

            # Update the Neptune section
            ui.step(
                "",
                f"Updating Neptune instructions (v{existing_version} → v{remote_version})",
            )
            new_content = re.sub(version_pattern, agents_content, existing_content, flags=re.DOTALL)
        else:
            # Append to existing file
            ui.step("", "Appending Neptune instructions to AGENTS.md")
            new_content = existing_content + "\n\n" + agents_content
    else:
        ui.step("", f"Creating {agents_file}")
        new_content = agents_content

    agents_file.write_text(new_content)
    ui.success("✅ AGENTS.md updated")
