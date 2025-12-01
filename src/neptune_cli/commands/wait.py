"""Wait command - Wait for deployment to complete."""

from __future__ import annotations

import click

from neptune_cli.types import OutputMode
from neptune_cli.ui import NeptuneUI
from neptune_cli.utils import resolve_project_name


@click.command("wait")
@click.option("--project-name", help="Explicit project name")
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Maximum seconds to wait (default: 300)",
)
@click.pass_context
def wait_command(
    ctx: click.Context,
    project_name: str | None,
    timeout: int,
) -> None:
    """Wait for the current deployment to complete.

    Polls the deployment status until the service reaches Running state,
    enters an error state, or the timeout is exceeded.
    """
    from neptune_cli.services.project import (
        wait_for_deployment,
        ProjectNotFoundError,
        DeploymentError,
    )

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    ui = NeptuneUI(output_mode)

    ui.header("Wait for Deployment")

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name()
        except Exception:
            if output_mode == OutputMode.JSON:
                ui.print_json(
                    {
                        "ok": False,
                        "error": "Could not determine project name",
                        "next_action_command": "neptune wait --project-name <name>",
                    }
                )
            else:
                ui.error("Could not determine project name")
                ui.info("Run from a project directory or use --project-name")
            ctx.exit(1)
            return

    ui.step("", f"Waiting for '{project_name}' to reach Running state...")
    ui.step("", f"(timeout: {timeout}s)")

    try:
        status = wait_for_deployment(
            project_name,
            timeout=float(timeout) if timeout else None,
        )
    except ProjectNotFoundError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "neptune deploy",
                }
            )
        else:
            ui.error(str(e))
            ui.info("Make sure the project exists. Run 'neptune deploy' first.")
        ctx.exit(1)
        return
    except DeploymentError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "state": e.state,
                    "next_action_command": "neptune logs",
                }
            )
        else:
            ui.error(str(e))
            ui.info("Check logs with 'neptune logs' for more details.")
        ctx.exit(1)
        return
    except TimeoutError as e:
        if output_mode == OutputMode.JSON:
            ui.print_json(
                {
                    "ok": False,
                    "error": str(e),
                    "next_action_command": "neptune wait --timeout <seconds>",
                }
            )
        else:
            ui.warn(str(e))
            ui.info("The deployment is still in progress. Run 'neptune wait' again or increase --timeout.")
        ctx.exit(1)
        return
    except Exception as e:
        if output_mode == OutputMode.JSON:
            ui.print_json({"ok": False, "error": str(e)})
        else:
            ui.error(f"Failed: {e}")
        ctx.exit(1)
        return

    if output_mode == OutputMode.JSON:
        result = status.to_dict()
        result["ok"] = True
        result["next_action_command"] = "neptune status"
        ui.print_json(result)
        return

    # Human-readable output
    ui.success("✅ Deployment complete!")

    state = status.provisioning_state
    running = status.running_status.get("current", "Unknown")

    if state == "Ready":
        ui.success(f"✅ Infrastructure: {state}")
    else:
        ui.step("", f"Infrastructure: {state}")

    if running == "Running":
        ui.success(f"✅ Service: {running}")
    else:
        ui.step("", f"Service: {running}")

    if status.url:
        ui.step("", f"URL: {status.url}")
