"""Resource commands - Manage project resources."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode
from neptune_cli.ui import NeptuneUI, spinner
from neptune_cli.utils import resolve_project_name


@click.group("resource")
def resource_group() -> None:
    """Manage project resources (databases, buckets, secrets)."""
    pass


# ==============================================================================
# Resource Info
# ==============================================================================


@resource_group.command("info")
@click.argument("kind", type=click.Choice(["Database", "StorageBucket", "Secret"]))
@click.pass_context
def resource_info(ctx: click.Context, kind: str) -> None:
    """Get information about a resource type.

    Shows documentation, neptune.json configuration examples, and code usage
    examples for the specified resource kind.

    KIND must be one of: Database, StorageBucket, Secret
    """
    from neptune_cli.services.resources import get_resource_info

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    ui = NeptuneUI(output_mode)

    try:
        info = get_resource_info(kind)
    except ValueError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(str(e))
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        result = info.to_dict()
        result["ok"] = True
        ui.print_json(result)
        return

    # Human-readable output
    ui.header(f"{kind} Resource")
    ui.step("", info.description)
    click.echo()

    ui.step("📝", "neptune.json configuration:")
    click.echo()
    for line in info.neptune_json_example.split("\n"):
        click.echo(f"  {line}")
    click.echo()

    ui.step("💻", "Code usage:")
    click.echo()
    for line in info.code_usage_example.split("\n"):
        click.echo(f"  {line}")


# ==============================================================================
# Provision Resources
# ==============================================================================


@resource_group.command("provision")
@click.pass_context
def resource_provision(ctx: click.Context) -> None:
    """Provision resources for the current project.

    Reads neptune.json and creates/updates all defined resources on Neptune's
    platform. This is automatically done during `neptune deploy`, but can be
    run separately to provision resources before deployment.
    """
    from neptune_cli.services.deploy import (
        provision_resources,
        NeptuneJsonNotFoundError,
    )

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode)

    ui.header("Provision Resources")

    try:
        with spinner("Provisioning resources...", output_mode):
            result = provision_resources(working_dir)
    except NeptuneJsonNotFoundError:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": "neptune.json not found",
                    "next_action_command": "neptune generate spec",
                }
            )
        else:
            ui.error("neptune.json not found")
            ui.info("Run 'neptune generate spec' to create it first.")
        ctx.exit(1)
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed to provision resources: {e}")
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        output = result.to_dict()
        output["ok"] = True
        output["next_action_command"] = "neptune deploy"
        ui.print_json(output)
        return

    # Human-readable output
    ui.success(f"✅ Resources provisioned for '{result.project_name}'")

    if result.resources:
        ui.step("", "Resources:")
        for resource in result.resources:
            status_icon = "✅" if resource.get("status") == "Available" else "⏳"
            ui.step(
                "",
                f"  {status_icon} {resource.get('name')} ({resource.get('kind')}): {resource.get('status')}",
            )

    ui.info("Run 'neptune deploy' to deploy your application.")


# ==============================================================================
# Secret Commands
# ==============================================================================


@resource_group.group("secret")
def secret_group() -> None:
    """Manage secrets."""
    pass


@secret_group.command("set")
@click.argument("secret_name")
@click.option("--project-name", help="Explicit project name")
@click.option("--value", help="Secret value (will prompt if not provided)")
@click.pass_context
def secret_set(
    ctx: click.Context,
    secret_name: str,
    project_name: str | None,
    value: str | None,
) -> None:
    """Set the value of a secret.

    The secret must be defined in neptune.json and provisioned first.
    If --value is not provided, you will be prompted to enter it securely.
    """
    from neptune_cli.services.resources import (
        set_secret_value,
        ResourceNotFoundError,
    )
    from neptune_cli.services.project import ProjectNotFoundError

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode)

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                ui.print_json(
                    {
                        "ok": False,
                        "error": "Could not determine project name",
                        "next_action_command": "neptune resource secret set <name> --project-name <project>",
                    }
                )
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            ctx.exit(1)
            return

    # Get secret value
    if value is None:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": "Secret value is required in JSON mode",
                    "hint": "Use --value to provide the secret value",
                }
            )
            ctx.exit(1)
            return

        value = click.prompt(
            f"Enter value for secret '{secret_name}'",
            hide_input=True,
            confirmation_prompt=True,
        )

    try:
        set_secret_value(project_name, secret_name, value)
    except ProjectNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "neptune resource provision",
                }
            )
        else:
            ui.error(str(e))
            ui.info("Make sure the project is provisioned first.")
        ctx.exit(1)
        return
    except ResourceNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "Add the secret to neptune.json and run 'neptune resource provision'",
                }
            )
        else:
            ui.error(str(e))
            ui.info("Make sure the secret is defined in neptune.json and provisioned.")
        ctx.exit(1)
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed to set secret: {e}")
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        ui.print_json(
            {
                "ok": True,
                "message": f"Secret '{secret_name}' set successfully",
                "project": project_name,
                "secret_name": secret_name,
            }
        )
    else:
        ui.success(f"✅ Secret '{secret_name}' set successfully")
        ui.info("Redeploy your application for changes to take effect.")


# ==============================================================================
# Database Commands
# ==============================================================================


@resource_group.group("database")
def database_group() -> None:
    """Manage databases."""
    pass


@database_group.command("info")
@click.argument("database_name")
@click.option("--project-name", help="Explicit project name")
@click.pass_context
def database_info(
    ctx: click.Context,
    database_name: str,
    project_name: str | None,
) -> None:
    """Get connection information for a database.

    Shows host, port, username, password, and database name for connecting
    to the database. The password token expires after 15 minutes.
    """
    from neptune_cli.services.resources import (
        get_database_connection_info,
        ResourceNotFoundError,
    )
    from neptune_cli.services.project import ProjectNotFoundError

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode)

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                ui.print_json(
                    {
                        "ok": False,
                        "error": "Could not determine project name",
                        "next_action_command": "neptune resource database info <name> --project-name <project>",
                    }
                )
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            ctx.exit(1)
            return

    try:
        with spinner(f"Fetching connection info for '{database_name}'...", output_mode):
            conn_info = get_database_connection_info(project_name, database_name)
    except ProjectNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "neptune resource provision",
                }
            )
        else:
            ui.error(str(e))
        ctx.exit(1)
        return
    except ResourceNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "Check neptune.json for database configuration",
                }
            )
        else:
            ui.error(str(e))
        ctx.exit(1)
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed to get database info: {e}")
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        result = conn_info.to_dict()
        result["ok"] = True
        result["project"] = project_name
        result["database_name"] = database_name
        ui.print_json(result)
        return

    # Human-readable output
    ui.header(f"Database: {database_name}")
    ui.step("", f"Host: {conn_info.host}")
    ui.step("", f"Port: {conn_info.port}")
    ui.step("", f"Database: {conn_info.database}")
    ui.step("", f"Username: {conn_info.username}")
    ui.step("", f"Password: {conn_info.password}")

    if conn_info.connection_string:
        click.echo()
        ui.step("", f"Connection string: {conn_info.connection_string}")

    click.echo()
    ui.warn("⚠️  The password token expires after 15 minutes.")
    ui.info("For deployed services, use environment variables instead of hardcoding.")


# ==============================================================================
# Bucket Commands
# ==============================================================================


@resource_group.group("bucket")
def bucket_group() -> None:
    """Manage storage buckets."""
    pass


@bucket_group.command("list")
@click.argument("bucket_name")
@click.option("--project-name", help="Explicit project name")
@click.pass_context
def bucket_list(
    ctx: click.Context,
    bucket_name: str,
    project_name: str | None,
) -> None:
    """List files in a storage bucket."""
    from neptune_cli.services.resources import (
        list_bucket_files,
        ResourceNotFoundError,
    )
    from neptune_cli.services.project import ProjectNotFoundError

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode)

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                ui.print_json(
                    {
                        "ok": False,
                        "error": "Could not determine project name",
                        "next_action_command": "neptune resource bucket list <name> --project-name <project>",
                    }
                )
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            ctx.exit(1)
            return

    try:
        with spinner(f"Listing files in bucket '{bucket_name}'...", output_mode):
            files = list_bucket_files(project_name, bucket_name)
    except ProjectNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "neptune resource provision",
                }
            )
        else:
            ui.error(str(e))
        ctx.exit(1)
        return
    except ResourceNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "Check neptune.json for bucket configuration",
                }
            )
        else:
            ui.error(str(e))
        ctx.exit(1)
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed to list bucket files: {e}")
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        ui.print_json(
            {
                "ok": True,
                "project": project_name,
                "bucket_name": bucket_name,
                "files": files,
                "count": len(files),
            }
        )
        return

    # Human-readable output
    ui.header(f"Bucket: {bucket_name}")

    if not files:
        ui.info("Bucket is empty")
        return

    ui.step("", f"Found {len(files)} file(s):")
    for file_key in files:
        ui.step("  📄", file_key)


@bucket_group.command("get")
@click.argument("bucket_name")
@click.argument("key")
@click.option("--project-name", help="Explicit project name")
@click.option("-o", "--output", "output_file", help="Save to file instead of stdout")
@click.pass_context
def bucket_get(
    ctx: click.Context,
    bucket_name: str,
    key: str,
    project_name: str | None,
    output_file: str | None,
) -> None:
    """Get an object from a storage bucket.

    Downloads the object with the specified KEY from the bucket.
    Use -o/--output to save to a file instead of printing to stdout.
    """
    from neptune_cli.services.resources import (
        get_bucket_object,
        ResourceNotFoundError,
    )
    from neptune_cli.services.project import ProjectNotFoundError

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode)

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            if output_mode == OutputMode.JSON:
                ui.print_json(
                    {
                        "ok": False,
                        "error": "Could not determine project name",
                        "next_action_command": "neptune resource bucket get <bucket> <key> --project-name <project>",
                    }
                )
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            ctx.exit(1)
            return

    try:
        with spinner(f"Downloading '{key}'...", output_mode):
            data = get_bucket_object(project_name, bucket_name, key)
    except ProjectNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(str(e))
        ctx.exit(1)
        return
    except ResourceNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(str(e))
        ctx.exit(1)
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed to get object: {e}")
        ctx.exit(1)
        return

    if output_file:
        Path(output_file).write_bytes(data)
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": True,
                    "saved_to": output_file,
                    "size": len(data),
                }
            )
        else:
            ui.success(f"✅ Saved to {output_file} ({len(data)} bytes)")
    else:
        if output_mode == OutputMode.JSON:
            # Try to decode as text for JSON output
            try:
                text = data.decode("utf-8")
                ui.print_json(
                    {
                        "ok": True,
                        "content": text,
                        "size": len(data),
                        "encoding": "utf-8",
                    }
                )
            except UnicodeDecodeError:
                import base64

                ui.print_json(
                    {
                        "ok": True,
                        "content_base64": base64.b64encode(data).decode(),
                        "size": len(data),
                        "encoding": "base64",
                    }
                )
        else:
            # Print raw content to stdout
            click.echo(data.decode("utf-8", errors="replace"))
