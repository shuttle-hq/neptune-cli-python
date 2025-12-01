"""Neptune MCP Server.

This module provides an MCP (Model Context Protocol) server that exposes
Neptune CLI functionality to AI assistants.

All MCP tools use the shared service layer to ensure consistency with CLI commands.
The service layer contains all business logic - MCP tools are thin wrappers that
format responses for AI consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from loguru import logger as log

from neptune_cli.utils import resolve_project_name


mcp = FastMCP("Neptune (neptune.dev) MCP")


# ==============================================================================
# Helper: Get project name from current directory
# ==============================================================================


def _get_project_name() -> str | None:
    """Try to get project name from current directory."""
    try:
        return resolve_project_name(Path.cwd())
    except Exception:
        return None


# ==============================================================================
# Schema & Resource Info
# ==============================================================================


@mcp.tool("get_project_schema")
def get_project_schema() -> dict[str, Any]:
    """Get the JSON schema that defines how to create a valid neptune.json file.

    IMPORTANT: Use this tool BEFORE creating or modifying 'neptune.json' to ensure
    the configuration is valid.

    This schema defines the exact structure and constraints for neptune.json files:
    - Required fields (kind, name)
    - Optional fields (resources, port_mappings, cpu, memory)
    - Valid resource types (Database, StorageBucket, Secret) and their properties
    - Allowed values for each field

    The returned schema is a standard JSON Schema that you should use as the
    authoritative reference when generating neptune.json configurations.
    """
    from neptune_cli.services import get_project_schema as do_get_schema

    try:
        schema = do_get_schema()
        return {
            "status": "success",
            "schema": schema,
            "purpose": "Use this schema as the authoritative reference when creating or modifying neptune.json files",
            "next_step": "Create a valid neptune.json based on this schema, then use 'provision_resources' to provision the infrastructure",
        }
    except Exception as e:
        log.error(f"Failed to fetch project schema: {e}")
        return {
            "status": "error",
            "message": f"Failed to fetch project schema: {e}",
            "next_step": "Ensure you are logged in with valid credentials",
        }


@mcp.tool("add_new_resource")
def add_new_resource(kind: str) -> dict[str, Any]:
    """Get information about resource types that can be provisioned on Neptune.

    IMPORTANT: Always use this tool before modifying 'neptune.json'. This is to ensure your modification is correct.

    Valid 'kind' are: "StorageBucket", "Database" and "Secret".
    """
    from neptune_cli.services import get_resource_info

    try:
        info = get_resource_info(kind)
        return info.to_dict()
    except ValueError as e:
        return {
            "error": "Unknown resource kind",
            "message": str(e),
        }


# ==============================================================================
# Dockerfile Guidance
# ==============================================================================


@mcp.tool("get_dockerfile_guidance")
def get_dockerfile_guidance() -> dict[str, Any]:
    """Get guidance for creating a Dockerfile for the current project.

    IMPORTANT: Use this tool BEFORE attempting to deploy if no Dockerfile exists.

    This tool analyzes the current project and provides:
    - Detected project type (Python, Node.js, Go, Rust, etc.)
    - The recommended start command (if available from previous spec generation)
    - An example Dockerfile tailored to the project type
    - Requirements and best practices for Neptune deployments

    After getting guidance, create the Dockerfile in the project root directory,
    then use 'deploy_project' to deploy.
    """
    from neptune_cli.services import get_dockerfile_guidance as do_get_guidance

    working_dir = Path.cwd()
    guidance = do_get_guidance(working_dir)

    dockerfile_exists = (working_dir / "Dockerfile").exists()
    result = guidance.to_dict()
    result["dockerfile_exists"] = dockerfile_exists

    if dockerfile_exists:
        result["status"] = "dockerfile_found"
        result["message"] = "A Dockerfile already exists. You can proceed with 'deploy_project'."
        result["next_step"] = "deploy_project"
    else:
        result["status"] = "dockerfile_needed"
        result["message"] = "No Dockerfile found. Create one using the example above, then deploy."
        result["next_step"] = "Create a Dockerfile in the project root, then run deploy_project"

    return result


# ==============================================================================
# Project Provisioning & Deployment
# ==============================================================================


@mcp.tool("provision_resources")
def provision_resources() -> dict[str, Any]:
    """Provision necessary cloud resources for the current project as per its configuration

    If the working directory does not contain a 'neptune.json' file, an error message is returned.
    """
    from neptune_cli.services import (
        provision_resources as do_provision,
        NeptuneJsonNotFoundError,
    )

    working_dir = Path.cwd()

    try:
        result = do_provision(working_dir, on_status=lambda msg: log.info(msg))
        return {
            "infrastructure_status": "ready",
            "message": "all the resources required by the project have been provisioned, and it is ready for deployment",
            "next_step": "deploy the project using the 'deploy_project' command; note how each resource should be used by inspecting their descriptions in this response",
            "infrastructure_resources": result.resources,
        }
    except NeptuneJsonNotFoundError:
        log.error("neptune.json not found in the current directory")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }
    except Exception as e:
        log.error(f"Failed to provision resources: {e}")
        return {
            "status": "error",
            "message": f"Failed to provision resources: {e}",
            "next_step": "check the error message and try again",
        }


@mcp.tool("deploy_project")
def deploy_project() -> dict[str, Any]:
    """Deploy the current project.

    This only works after the project has been provisioned using 'provision_resources'.

    UNDER THE HOOD: deployments are ECS tasks running on Fargate, with images stored in ECR. In particular, this tool builds an image using the Dockerfile in the current directory.

    Note: running tasks are *not* persistent; if the task stops or is redeployed, all data stored in the container is lost. Use provisioned resources (databases, storage buckets, etc.) for persistent data storage.
    """
    from neptune_cli.services import (
        deploy_project as do_deploy,
        NeptuneJsonNotFoundError,
        DockerfileNotFoundError,
        DockerBuildError,
        DockerPushError,
        DockerNotAvailableError,
        DockerLoginError,
        LintBlockingError,
        ProvisioningError,
        DeploymentCreationError,
    )

    working_dir = Path.cwd()

    try:
        result = do_deploy(
            working_dir,
            skip_lint=True,  # MCP users handle lint separately
            on_status=lambda msg: log.info(msg),
        )
        return {
            "deployment_status": result.status,
            "deployment_revision": result.revision,
            "url": result.url,
            "next_step": "the deployment was sent to Neptune's backend, and is now propagating. Investigate the deployment status with 'get_deployment_status'",
        }
    except DockerfileNotFoundError as e:
        log.error("Dockerfile not found")
        result = {
            "status": "error",
            "message": "Dockerfile not found in the current directory",
            "next_step": "Use 'get_dockerfile_guidance' to get an example Dockerfile for your project type, create the file, then run deploy_project again",
            "hint": "Neptune requires a Dockerfile to build and deploy your application.",
        }
        if e.guidance:
            result["dockerfile_guidance"] = e.guidance.to_dict()
        return result
    except DockerNotAvailableError as e:
        log.error(f"Docker not available: {e}")
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure Docker is installed and running, then try again",
        }
    except NeptuneJsonNotFoundError:
        log.error("neptune.json not found")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "create a 'neptune.json' file or use 'generate_spec' first",
        }
    except DockerBuildError as e:
        log.error(f"Docker build failed: {e}")
        return {
            "status": "error",
            "message": "Docker build failed",
            "error_output": e.output if e.output else str(e),
            "next_step": "Fix the Dockerfile or application errors shown above, then run deploy_project again",
            "hint": "Common issues: missing dependencies, incorrect start command, syntax errors in Dockerfile",
        }
    except DockerPushError as e:
        log.error(f"Docker push failed: {e}")
        return {
            "status": "error",
            "message": "Docker push failed",
            "error_output": e.output if e.output else str(e),
            "next_step": "Check Docker login and network connectivity, then run deploy_project again",
        }
    except DockerLoginError as e:
        log.error(f"Docker login failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure Docker is working correctly and try again",
        }
    except LintBlockingError as e:
        log.error(f"Lint blocking: {e}")
        return {
            "status": "error",
            "message": "Deployment blocked by lint errors",
            "reasons": e.reasons,
            "next_step": "fix the lint errors and try again, or use run_ai_lint to see details",
        }
    except ProvisioningError as e:
        log.error(f"Provisioning failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure the project is provisioned with 'provision_resources' and try again",
        }
    except DeploymentCreationError as e:
        log.error(f"Deployment creation failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure the project is provisioned and try again",
        }
    except Exception as e:
        log.error(f"Failed to deploy project: {e}")
        return {
            "status": "error",
            "message": f"Failed to deploy project: {e}",
            "next_step": "ensure the project is provisioned with 'provision_resources' and try again",
        }


# ==============================================================================
# Project Status & Management
# ==============================================================================


@mcp.tool("get_deployment_status")
def get_deployment_status() -> dict[str, Any]:
    """Get the status of the current deployment of a project and its provisioned resources.

    This will tell you about running resources the project is using, as well as the state of the service.
    """
    from neptune_cli.services import get_project_status, ProjectNotFoundError

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    try:
        status = get_project_status(project_name)
        return {
            "infrastructure_provisioning_status": status.provisioning_state,
            "service_running_status": status.running_status,
            "infrastructure_resources": status.resources,
            "url": status.url,
            "next_steps": "use this information to monitor the deployment status; if there are issues, check the logs and redeploy as necessary",
        }
    except ProjectNotFoundError:
        log.error(f"Project '{project_name}' not found")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }
    except Exception as e:
        log.error(f"Failed to get project status: {e}")
        return {
            "status": "error",
            "message": f"Failed to get project status: {e}",
        }


@mcp.tool("list_projects")
def list_projects_tool() -> dict[str, Any]:
    """List all projects in your Neptune account.

    Returns a list of all projects with their status, resource count, and URLs.
    """
    from neptune_cli.services import list_projects

    try:
        projects = list_projects()
        return {
            "status": "success",
            "projects": [p.to_dict() for p in projects],
            "count": len(projects),
            "next_step": "use 'get_deployment_status' from a project directory or create a new project with 'provision_resources'",
        }
    except Exception as e:
        log.error(f"Failed to list projects: {e}")
        return {
            "status": "error",
            "message": f"Failed to list projects: {e}",
        }


@mcp.tool("delete_project")
def delete_project_tool(project_name: str | None = None) -> dict[str, Any]:
    """Delete a project and all its resources.

    WARNING: This permanently deletes the project and all associated resources
    including databases, storage buckets, and secrets.

    Args:
        project_name: Name of the project to delete. If not provided, uses the
                     project name from neptune.json in the current directory.
    """
    from neptune_cli.services import delete_project, ProjectNotFoundError

    # Resolve project name
    if project_name is None:
        project_name = _get_project_name()
        if not project_name:
            return {
                "status": "error",
                "message": "Could not determine project name. Provide project_name parameter or ensure neptune.json exists.",
            }

    try:
        delete_project(project_name)
        return {
            "status": "success",
            "message": f"Project '{project_name}' deleted successfully",
            "next_step": "the project and all its resources have been permanently deleted",
        }
    except ProjectNotFoundError:
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found",
        }
    except Exception as e:
        log.error(f"Failed to delete project: {e}")
        return {
            "status": "error",
            "message": f"Failed to delete project: {e}",
        }


@mcp.tool("wait_for_deployment")
def wait_for_deployment() -> dict[str, Any]:
    """Wait for the current project deployment to complete."""
    from neptune_cli.services import (
        wait_for_deployment as do_wait,
        ProjectNotFoundError,
        DeploymentError,
    )

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    try:
        status = do_wait(project_name)
        return {
            "infrastructure_provisioning_status": status.provisioning_state,
            "service_running_status": status.running_status,
            "infrastructure_resources": status.resources,
            "url": status.url,
            "next_steps": "use this information to monitor the deployment status; if there are issues, check the logs and redeploy as necessary",
        }
    except ProjectNotFoundError:
        log.error(f"Project '{project_name}' not found")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }
    except DeploymentError as e:
        log.error(f"Deployment error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "state": e.state,
            "next_step": "check the logs with 'get_logs' and try deploying again",
        }
    except Exception as e:
        log.error(f"Failed while waiting for deployment: {e}")
        return {
            "status": "error",
            "message": f"Failed while waiting for deployment: {e}",
        }


# ==============================================================================
# Secrets
# ==============================================================================


@mcp.tool("set_secret_value")
async def set_secret_value(ctx: Context, secret_name: str) -> dict[str, Any]:
    """Set the value of a secret resource for the current project.

    This will elicit a prompt to securely enter the secret value.

    Note the secret must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before setting its value.
    """
    from neptune_cli.services import (
        set_secret_value as do_set_secret,
        ResourceNotFoundError,
        ProjectNotFoundError,
    )

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    # Elicit secret value from user
    result = await ctx.elicit(message="Please provide the secret's value:", response_type=str)

    if result.action == "accept":
        secret_value = result.data
    elif result.action == "decline":
        return {
            "status": "cancelled",
            "message": "Secret value input was cancelled by the user.",
            "next_step": "run the 'set_secret_value' command again to set the secret value",
        }
    else:
        return {
            "status": "error",
            "message": "Elicitation cancelled during requesting secret value input.",
            "next_step": "try running the 'set_secret_value' command again",
        }

    try:
        do_set_secret(project_name, secret_name, secret_value)
        return {
            "status": "success",
            "message": f"Secret '{secret_name}' set successfully for project '{project_name}'.",
            "next_step": "redeploy the project if necessary to use the updated secret value with 'deploy_project'",
        }
    except ProjectNotFoundError:
        log.error(f"Project '{project_name}' not found")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you provision resources for it?",
            "next_step": "provision the project using the 'provision_resources' command",
        }
    except ResourceNotFoundError as e:
        log.error(str(e))
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure the secret is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }
    except Exception as e:
        log.error(f"Failed to set secret: {e}")
        return {
            "status": "error",
            "message": f"Failed to set secret: {e}",
        }


# ==============================================================================
# Databases
# ==============================================================================


@mcp.tool("get_database_connection_info")
def get_database_connection_info(database_name: str) -> dict[str, Any]:
    """Get the connection information for a database resource for the current project.

    Note the database must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before retrieving its connection info.
    """
    from neptune_cli.services import (
        get_database_connection_info as get_db_info,
        ResourceNotFoundError,
        ProjectNotFoundError,
    )

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    try:
        conn_info = get_db_info(project_name, database_name)
        return {
            "database_connection_info": conn_info.to_dict(),
            "next_step": "use this connection information to connect to your database; remember the token expires after 15 minutes so do not use it for programmatic access - only for local testing.",
        }
    except ProjectNotFoundError:
        log.error(f"Project '{project_name}' not found")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }
    except ResourceNotFoundError as e:
        log.error(str(e))
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure the database is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }
    except Exception as e:
        log.error(f"Failed to get database connection info: {e}")
        return {
            "status": "error",
            "message": f"Failed to get database connection info: {e}",
        }


# ==============================================================================
# Storage Buckets
# ==============================================================================


@mcp.tool("list_bucket_files")
def list_bucket_files(bucket_name: str) -> dict[str, Any]:
    """List all files in a storage bucket resource for the current project.

    Note the bucket must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before listing its files.
    """
    from neptune_cli.services import (
        list_bucket_files as do_list_files,
        ResourceNotFoundError,
        ProjectNotFoundError,
    )

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    try:
        keys = do_list_files(project_name, bucket_name)
        return {
            "bucket_name": bucket_name,
            "files": keys,
            "next_step": "use these file keys to interact with objects in the bucket; retrieve or manage them as needed",
        }
    except ProjectNotFoundError:
        log.error(f"Project '{project_name}' not found")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }
    except ResourceNotFoundError as e:
        log.error(str(e))
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure the storage bucket is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }
    except Exception as e:
        log.error(f"Failed to list bucket files: {e}")
        return {
            "status": "error",
            "message": f"Failed to list bucket files: {e}",
        }


@mcp.tool("get_bucket_object")
def get_bucket_object(bucket_name: str, key: str) -> dict[str, str] | bytes:
    """Retrieve an object from a storage bucket resource for the current project.

    Note the bucket must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before retrieving its objects.
    """
    from neptune_cli.services import (
        get_bucket_object as do_get_object,
        ResourceNotFoundError,
        ProjectNotFoundError,
    )

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    try:
        data = do_get_object(project_name, bucket_name, key)
        return data
    except ProjectNotFoundError:
        log.error(f"Project '{project_name}' not found")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }
    except ResourceNotFoundError as e:
        log.error(str(e))
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure the storage bucket is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }
    except Exception as e:
        log.error(f"Failed to get bucket object: {e}")
        return {
            "status": "error",
            "message": f"Failed to get bucket object: {e}",
        }


# ==============================================================================
# Logs
# ==============================================================================


@mcp.tool("get_logs")
def get_logs() -> dict[str, Any]:
    """Retrieve the logs for the current project deployment."""
    from neptune_cli.services import get_logs as do_get_logs

    project_name = _get_project_name()
    if not project_name:
        log.error("Could not determine project name")
        return {
            "status": "error",
            "message": "neptune.json not found in the current directory",
            "next_step": "make sure a 'neptune.json' file exists in the current directory",
        }

    try:
        logs_result = do_get_logs(project_name)
        return {
            "logs": logs_result.logs,
            "next_step": "use these logs to debug your application or monitor its behavior; fix any issues and redeploy as necessary",
        }
    except Exception as e:
        log.error(f"Failed to get logs: {e}")
        return {
            "status": "error",
            "message": f"Failed to get logs: {e}",
        }


# ==============================================================================
# Generation & Linting
# ==============================================================================


@mcp.tool("generate_spec")
def generate_spec_tool() -> dict[str, Any]:
    """Generate neptune.json configuration for the current project.

    Analyzes the project structure and code to automatically generate an
    appropriate neptune.json configuration file.

    This includes:
    - Detecting the project type and workload kind
    - Identifying required resources (databases, storage, secrets)
    - Running AI lint to validate the configuration

    After generation, review the neptune.json file and make any necessary
    adjustments before provisioning.
    """
    from neptune_cli.services import generate_spec, SpecGenerationError

    working_dir = Path.cwd()

    try:
        result = generate_spec(working_dir)
        response = {
            "status": "success",
            "spec_path": str(result.spec_path),
            "spec": result.spec,
            "changed": result.changed,
            "start_command": result.start_command,
            "next_step": "review the generated neptune.json, then use 'provision_resources' to create the infrastructure",
        }

        if result.ai_lint_report:
            response["ai_lint_report"] = {
                "compatible": result.ai_lint_report.compatible,
                "errors": len(result.ai_lint_report.errors),
                "warnings": len(result.ai_lint_report.warnings),
            }
            if result.ai_lint_report.errors:
                response["lint_errors"] = [
                    {"code": e.code, "message": e.message, "suggestion": e.suggestion}
                    for e in result.ai_lint_report.errors
                ]
            if result.ai_lint_report.warnings:
                response["lint_warnings"] = [
                    {"code": w.code, "message": w.message, "suggestion": w.suggestion}
                    for w in result.ai_lint_report.warnings
                ]

        return response
    except SpecGenerationError as e:
        log.error(f"Failed to generate spec: {e}")
        return {
            "status": "error",
            "message": str(e),
            "next_step": "ensure you're in a valid project directory and try again",
        }
    except Exception as e:
        log.error(f"Failed to generate spec: {e}")
        return {
            "status": "error",
            "message": f"Failed to generate spec: {e}",
            "next_step": "ensure you're in a valid project directory and try again",
        }


@mcp.tool("run_ai_lint")
def run_ai_lint_tool() -> dict[str, Any]:
    """Run AI lint on the current project.

    Analyzes the project configuration and code to detect potential issues
    before deployment. This includes checking for:
    - Configuration errors in neptune.json
    - Unsupported workload types
    - Missing or incompatible resources
    - Architecture issues

    Fix any errors before deploying. Warnings can often be ignored but
    should be reviewed.
    """
    from neptune_cli.services import run_ai_lint

    working_dir = Path.cwd()

    # Check for neptune.json first
    if not (working_dir / "neptune.json").exists():
        return {
            "status": "error",
            "message": "neptune.json not found. Run 'generate_spec' first.",
            "next_step": "use 'generate_spec' to create neptune.json, then run lint again",
        }

    try:
        report = run_ai_lint(working_dir)
        return {
            "status": "success",
            "compatible": report.compatible,
            "summary": {
                "errors": report.summary.errors,
                "warnings": report.summary.warnings,
                "suppressed": report.summary.suppressed,
                "blocking": report.summary.blocking,
            },
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "path": e.path,
                    "suggestion": e.suggestion,
                }
                for e in report.errors
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "path": w.path,
                    "suggestion": w.suggestion,
                }
                for w in report.warnings
            ],
            "next_step": "fix any errors before deploying; warnings should be reviewed but can often be ignored",
        }
    except Exception as e:
        log.error(f"Failed to run AI lint: {e}")
        return {
            "status": "error",
            "message": f"Failed to run AI lint: {e}",
        }


# ==============================================================================
# Entry Point
# ==============================================================================


if __name__ == "__main__":
    mcp.run()
