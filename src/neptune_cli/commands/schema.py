"""Schema command - Fetch and display API schemas."""

from __future__ import annotations

import json

import click

from neptune_cli.types import OutputMode
from neptune_cli.ui import NeptuneUI


@click.command("schema")
@click.pass_context
def schema_command(ctx: click.Context) -> None:
    """Fetch the JSON schema that defines valid neptune.json configurations.

    This schema is the authoritative reference for creating neptune.json files.
    It defines the exact structure, required fields, valid resource types,
    and allowed values for project configurations.

    Use this schema to ensure your neptune.json is valid before running
    'neptune deploy' or 'neptune init'.
    """
    from neptune_cli.services.schema import get_project_schema

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    ui = NeptuneUI(output_mode, verbose=verbose)

    try:
        schema = get_project_schema()
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed to fetch schema: {e}")
            ui.info("Make sure you're logged in with 'neptune login'")
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        # In JSON mode, just output the schema directly
        ui.print_json(schema)
    else:
        # In normal mode, pretty-print the schema
        ui.header("Project Schema")
        ui.step("", "JSON Schema defining valid neptune.json configurations:")
        click.echo()
        click.echo(json.dumps(schema, indent=2))
