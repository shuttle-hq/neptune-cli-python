"""Generate commands - Generate completions, specs, etc."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from neptune_cli.types import OutputMode, GenerateResult
from neptune_cli.ui import (
    NeptuneUI,
    assess_lint_gate,
    print_lint_report,
    spinner,
)
from neptune_cli.utils import resolve_project_name


@click.group("generate")
def generate_group() -> None:
    """Generate AI instructions, shell completions, specs, etc."""
    pass


@generate_group.command("shell")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish", "powershell"]))
@click.option(
    "-o",
    "--output-file",
    type=click.Path(),
    help="Output to a file (stdout by default)",
)
@click.pass_context
def generate_shell(ctx: click.Context, shell: str, output_file: str | None) -> None:
    """Generate shell completions."""
    import subprocess
    import os

    # Use click's built-in completion generation
    shell_map = {
        "bash": "_NEPTUNE_COMPLETE=bash_source",
        "zsh": "_NEPTUNE_COMPLETE=zsh_source",
        "fish": "_NEPTUNE_COMPLETE=fish_source",
        "powershell": "_NEPTUNE_COMPLETE=powershell_source",
    }

    env_var = shell_map.get(shell)
    if not env_var:
        click.echo(f"Unsupported shell: {shell}", err=True)
        ctx.exit(1)

    # Generate completions by invoking the CLI with the completion env var
    env = os.environ.copy()
    key, value = env_var.split("=")
    env[key] = value

    result = subprocess.run(
        [sys.executable, "-m", "neptune_cli.cli"],
        env=env,
        capture_output=True,
        text=True,
    )

    output = result.stdout

    if output_file:
        Path(output_file).write_text(output)
        click.echo(f"Completions written to {output_file}")
    else:
        click.echo(output)


@generate_group.command("agents")
@click.pass_context
def generate_agents(ctx: click.Context) -> None:
    """Generate AGENTS.md, Neptune-tailored instructions for AI coding agents."""
    from neptune_cli.services.generate import get_agents_md

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    ui.header("AGENTS.md")

    agents_file = working_dir / "AGENTS.md"
    ui.step("", f"Generating/updating {agents_file}")
    ui.step("", "Fetching latest Neptune agent instructions...")

    try:
        agents_content = get_agents_md()
    except Exception as e:
        ui.error(f"Failed to fetch AGENTS.md: {e}")
        ctx.exit(1)

    # Extract version from content
    version_pattern = r"<!-- neptune: agents\.md version ([^>]+) -->.*?<!-- neptune end -->"
    match = re.search(version_pattern, agents_content, re.DOTALL)

    if not match:
        ui.error("Could not detect AGENTS.md version in fetched content")
        ctx.exit(1)

    remote_version = match.group(1)

    changed = False

    if agents_file.exists():
        ui.step("", f"Found existing {agents_file}")
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
            changed = True
        else:
            # Append to existing file
            ui.step("", "Appending Neptune instructions to AGENTS.md")
            new_content = existing_content + "\n\n" + agents_content
            changed = True
    else:
        ui.step("", f"Creating {agents_file}")
        new_content = agents_content
        changed = True

    if changed:
        agents_file.write_text(new_content)
        ui.success("✅ AGENTS.md updated")


@generate_group.command("spec")
@click.pass_context
def generate_spec(ctx: click.Context) -> None:
    """Generate neptune.json project specification."""
    from neptune_cli.services.generate import (
        generate_spec as do_generate_spec,
        SpecGenerationError,
    )

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    ui.header("neptune.json")

    # Resolve project name
    try:
        project_name = resolve_project_name(working_dir)
    except Exception:
        project_name = working_dir.name

    # Initialize JSON output
    json_out = None
    if output_mode == OutputMode.JSON:
        json_out = GenerateResult(
            ok=True,
            spec_path="",
            next_action_command="",
        )

    # Generate spec using service
    try:
        with spinner("Analyzing project and generating configuration...", output_mode):
            result = do_generate_spec(working_dir, project_name)
    except SpecGenerationError as e:
        if json_out:
            json_out.ok = False
            json_out.messages = [str(e)]
            json_out.next_action_command = "neptune generate spec"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error(str(e))
            ctx.exit(1)
    except Exception as e:
        if json_out:
            json_out.ok = False
            json_out.messages = [f"Failed to generate spec: {e}"]
            json_out.next_action_command = "neptune generate spec"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error(f"Failed to generate spec: {e}")
            ctx.exit(1)

    spec_path = result.spec_path

    # Show status based on whether file changed
    if not result.changed:
        ui.success("✅ neptune.json up to date")
    else:
        if output_mode != OutputMode.JSON:
            if spec_path.exists():
                # Read the file we just wrote to show what changed
                # (the service already wrote it, so we show the result)
                ui.step("", "Updated neptune.json")
            else:
                ui.step("", "Created neptune.json")
        ui.success("✅ Generated neptune.json")

    if json_out:
        json_out.spec_path = str(spec_path)
        if result.changed:
            json_out.messages = [
                f"Created or updated neptune.json at {spec_path}",
                "Review the generated configuration to ensure it matches your project.",
            ]
        json_out.next_action_command = "neptune deploy"

        if result.ai_lint_report:
            json_out.ai_lint_report = result.ai_lint_report

        ui.print_json(json_out.model_dump(mode="json"))
        return

    # Human-readable: show lint report
    if result.ai_lint_report:
        print_lint_report(ui, result.ai_lint_report, output_mode)

        assessment = assess_lint_gate(result.ai_lint_report, False, False)
        if assessment.blocking:
            for reason in assessment.reasons:
                ui.warn(f"Blocking: {reason}")
            ui.info("Use --allow-ai-errors / --allow-ai-warnings to override during deploy.")
