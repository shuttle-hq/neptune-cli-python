"""Deploy command - Build and deploy a project."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode, DeployResult as DeployResultType
from neptune_cli.ui import (
    NeptuneUI,
    confirm,
    print_lint_report,
    spinner,
)


@click.command("deploy")
@click.option(
    "--skip-spec",
    is_flag=True,
    help="Skip spec generation and reuse existing neptune.json",
)
@click.option(
    "--skip-lint",
    is_flag=True,
    help="Skip AI lint before deploying",
)
@click.option(
    "--allow-ai-errors",
    is_flag=True,
    help="Ignore blocking AI lint errors",
)
@click.option(
    "--allow-ai-warnings",
    is_flag=True,
    help="Ignore blocking AI lint warnings",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.pass_context
def deploy_command(
    ctx: click.Context,
    skip_spec: bool,
    skip_lint: bool,
    allow_ai_errors: bool,
    allow_ai_warnings: bool,
    yes: bool,
) -> None:
    """Build and deploy the current project.

    This command will:
    1. Check for required Dockerfile
    2. Generate/update neptune.json (spec)
    3. Run AI lint validation
    4. Build a Docker image
    5. Push to Neptune's registry
    6. Create a deployment

    Note: A Dockerfile is required. If one doesn't exist, the command will
    provide guidance on creating one. AI agents can use the AGENTS.md
    instructions or MCP tools to generate an appropriate Dockerfile.
    """
    from neptune_cli.services.deploy import (
        run_preflight_checks,
        generate_or_load_spec,
        assess_lint_results,
        provision_resources,
        build_and_push_image,
        NeptuneJsonNotFoundError,
        SpecGenerationError,
        ProvisioningError,
        DockerBuildError,
        DockerPushError,
        DockerLoginError,
    )
    from neptune_cli.client import get_client
    from neptune_cli.utils import resolve_project_name

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    # Resolve project name early for error messages
    try:
        project_name = resolve_project_name(working_dir)
    except Exception:
        project_name = working_dir.name

    # Initialize JSON output if needed
    json_out = None
    if output_mode == OutputMode.JSON:
        json_out = DeployResultType(
            ok=False,
            project=project_name,
            next_action_command="",
        )

    # ==========================================================================
    # Step 1: Preflight Checks
    # ==========================================================================
    ui.header("Preflight")

    preflight = run_preflight_checks(working_dir)

    # Check Dockerfile
    if not preflight.dockerfile_exists:
        guidance = preflight.dockerfile_guidance
        if json_out:
            json_out.messages = [
                "Dockerfile not found in project directory",
                f"Detected project type: {guidance.project_type}" if guidance else "",
                "",
                "To deploy, you need to create a Dockerfile.",
            ]
            json_out.next_action_command = "Create a Dockerfile, then run: neptune deploy"
            result = json_out.model_dump(mode="json")
            if guidance:
                result["dockerfile_guidance"] = guidance.to_dict()
            ui.print_json(result)
            return
        else:
            ui.error("Dockerfile not found")
            if guidance:
                ui.step("", f"Detected project type: {guidance.project_type}")
                if guidance.start_command:
                    ui.step("", f"Detected start command: {guidance.start_command}")
                click.echo()
                ui.info("A Dockerfile is required to deploy to Neptune.")
                click.echo()
                ui.step("📝", "Example Dockerfile:")
                click.echo()
                for line in guidance.dockerfile_example.split("\n"):
                    click.echo(f"    {line}")
                click.echo()
                ui.info("Requirements:")
                for req in guidance.requirements:
                    ui.step("  •", req)
            click.echo()
            ui.info("After creating the Dockerfile, run 'neptune deploy' again.")
            ctx.exit(1)

    ui.success("✅ Dockerfile found")

    # Check Docker
    if not preflight.docker_available:
        message = "Docker is not installed or not found in PATH"
        if json_out:
            json_out.messages = [
                message,
                "Install Docker: https://docs.docker.com/get-docker/",
            ]
            json_out.next_action_command = "Install Docker, then run: neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.warn(message)
            ui.info("Install Docker: https://docs.docker.com/get-docker/")
            ctx.exit(1)

    if not preflight.docker_running:
        message = "Docker daemon is not running"
        if json_out:
            json_out.messages = [message, "Start Docker and try again"]
            json_out.next_action_command = "Start Docker, then run: neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.warn(message)
            ui.info("Start Docker (e.g., Docker Desktop) and retry.")
            ctx.exit(1)

    ui.success("✅ Docker is installed and running")

    # ==========================================================================
    # Step 2: Generate or Load Spec
    # ==========================================================================
    ui.header("Configuration")

    client = get_client()

    try:
        with spinner("Processing project configuration...", output_mode):
            spec_result = generate_or_load_spec(
                working_dir,
                project_name,
                skip_generation=skip_spec,
                skip_lint=skip_lint,
                client=client,
            )
    except NeptuneJsonNotFoundError:
        message = "Cannot skip spec generation because neptune.json does not exist"
        if json_out:
            json_out.messages = [message, "Run `neptune generate spec` first"]
            json_out.next_action_command = "neptune generate spec"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error(message)
            ctx.exit(1)
    except SpecGenerationError as e:
        if json_out:
            json_out.messages = [str(e)]
            json_out.next_action_command = "neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error(str(e))
            ctx.exit(1)

    if spec_result.generated:
        ui.success("✅ Generated neptune.json")
    else:
        ui.success("✅ Using existing neptune.json")

    if skip_lint and output_mode != OutputMode.JSON:
        ui.step("", "Skipping AI lint (--skip-lint)")

    # ==========================================================================
    # Step 3: Check Lint Results
    # ==========================================================================
    if spec_result.ai_lint_report:
        if json_out:
            json_out.ai_lint_report = spec_result.ai_lint_report
        else:
            print_lint_report(ui, spec_result.ai_lint_report, output_mode)

        assessment = assess_lint_results(
            spec_result.ai_lint_report,
            allow_errors=allow_ai_errors,
            allow_warnings=allow_ai_warnings,
        )

        if assessment.blocking:
            if json_out:
                json_out.messages = [
                    *assessment.reasons,
                    "Deployment aborted due to AI lint findings.",
                ]
                json_out.next_action_command = "Fix issues, then run: neptune deploy"
                ui.print_json(json_out.model_dump(mode="json"))
                return
            else:
                for reason in assessment.reasons:
                    ui.warn(f"Blocking: {reason}")
                ui.info("Use --allow-ai-errors / --allow-ai-warnings to override.")
                ui.info("Deployment aborted; resolve findings or override to continue.")
                ctx.exit(1)

    # ==========================================================================
    # Step 4: Confirmation
    # ==========================================================================
    if not yes and output_mode != OutputMode.JSON:
        if not confirm("Proceed with build and deployment?"):
            ui.step("", "Aborted by user.")
            return

    # ==========================================================================
    # Step 5: Provision Infrastructure
    # ==========================================================================
    ui.header("Infrastructure")

    try:
        with spinner("Provisioning infrastructure...", output_mode):
            provision_resources(
                working_dir,
                client=client,
            )
    except ProvisioningError as e:
        if json_out:
            json_out.messages = [str(e)]
            json_out.next_action_command = "neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error(str(e))
            ctx.exit(1)

    ui.success("✅ Infrastructure ready")

    # ==========================================================================
    # Step 6: Create Deployment and Build/Push
    # ==========================================================================
    ui.header("Build")

    try:
        deployment = client.create_deployment(project_name)
    except Exception as e:
        if json_out:
            json_out.messages = [f"Failed to create deployment: {e}"]
            json_out.next_action_command = "neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error(f"Failed to create deployment: {e}")
            ctx.exit(1)

    ui.step("🔨", f"Building image for revision {deployment.revision}...")

    try:
        build_and_push_image(
            working_dir,
            deployment.image,
            push_token=deployment.push_token,
            on_status=lambda msg: ui.step("", msg) if output_mode != OutputMode.JSON else None,
        )
    except DockerLoginError as e:
        if json_out:
            json_out.messages = ["Docker login to registry failed", str(e)]
            json_out.next_action_command = "neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error("Docker login to registry failed")
            ctx.exit(1)
    except DockerBuildError as e:
        if json_out:
            json_out.messages = [
                "Docker build failed",
                "Check your Dockerfile for errors",
            ]
            if e.output:
                json_out.messages.append(e.output)
            json_out.next_action_command = "Fix Dockerfile, then run: neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error("Docker build failed")
            ui.info("Check your Dockerfile for errors and try again.")
            ctx.exit(1)
    except DockerPushError as e:
        if json_out:
            json_out.messages = ["Docker push failed", str(e)]
            json_out.next_action_command = "neptune deploy"
            ui.print_json(json_out.model_dump(mode="json"))
            return
        else:
            ui.error("Docker push failed")
            ctx.exit(1)

    ui.success("✅ Image built and pushed successfully")

    # ==========================================================================
    # Step 7: Wait for Deployment
    # ==========================================================================
    ui.header("Deploy")
    ui.step("🚀", f"Deployment created (revision {deployment.revision})")
    ui.step("", "Waiting for deployment to complete...")

    import time

    max_attempts = 60
    for _ in range(max_attempts):
        deployment = client.get_deployment(project_name, deployment.revision)
        if deployment.status == "Deployed":
            break
        time.sleep(5)

    # Get final status
    project = client.get_project(project_name)

    if json_out:
        json_out.ok = True
        json_out.deployment = {
            "revision": deployment.revision,
            "status": deployment.status,
        }
        if project:
            json_out.final_condition = {
                "provisioning_state": project.provisioning_state,
                "running_status": project.running_status.model_dump() if project.running_status else None,
            }
            if project.running_status and project.running_status.public_ip:
                json_out.final_url = f"http://{project.running_status.public_ip}"
        json_out.next_action_command = "neptune status"
        ui.print_json(json_out.model_dump(mode="json"))
        return

    # Human-readable output
    ui.header("Status")

    if project:
        state = project.provisioning_state
        running = project.running_status.current if project.running_status else "Unknown"

        if state == "Ready":
            ui.success(f"✅ Infrastructure: {state}")
        else:
            ui.step("", f"Infrastructure: {state}")

        if running == "Running":
            ui.success(f"✅ Service: {running}")
        elif running in ["Stopped", "Error"]:
            ui.warn(f"Service: {running}")
        else:
            ui.step("", f"Service: {running}")

        if project.running_status and project.running_status.public_ip:
            ui.step("", f"URL: http://{project.running_status.public_ip}")

        if state == "Ready" and running == "Running":
            ui.success("✅ Deployment complete!")
