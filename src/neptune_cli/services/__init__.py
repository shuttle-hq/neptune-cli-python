"""Service layer for Neptune CLI.

This module provides the core business logic used by both CLI commands and MCP tools.
All stateful operations should go through these services to ensure consistency.

The services are designed to:
1. Be independent of UI concerns (no click, no spinners, no colors)
2. Return structured data (dataclasses/Pydantic models)
3. Raise exceptions for errors (callers handle display)
4. Be easily testable

Architecture:
    CLI Command → Service → Client → API
    MCP Tool    → Service → Client → API

Both CLI and MCP use the same service functions, ensuring consistent behavior.
"""

# Project operations
from neptune_cli.services.project import (
    get_project_status,
    list_projects,
    delete_project,
    wait_for_deployment,
    wait_for_provisioning,
    ProjectStatus,
    ProjectSummary,
    ProjectNotFoundError,
    DeploymentError,
)

# Resource operations
from neptune_cli.services.resources import (
    get_resource_info,
    set_secret_value,
    get_database_connection_info,
    list_bucket_files,
    get_bucket_object,
    ResourceInfo,
    DatabaseConnectionInfo,
    ResourceNotFoundError,
)

# Deployment operations
from neptune_cli.services.deploy import (
    provision_resources,
    deploy_project,
    run_preflight_checks,
    generate_or_load_spec,
    assess_lint_results,
    build_and_push_image,
    get_dockerfile_guidance,
    detect_project_type,
    # Result types
    PreflightResult,
    SpecResult,
    LintAssessment,
    ProvisionResult,
    DeployResult,
    DockerfileGuidance,
    # Exceptions
    NeptuneJsonNotFoundError,
    DockerfileNotFoundError,
    DockerNotAvailableError,
    DockerBuildError,
    DockerPushError,
    DockerLoginError,
    SpecGenerationError,
    LintBlockingError,
    ProvisioningError,
    DeploymentCreationError,
)

# Generation operations
from neptune_cli.services.generate import (
    generate_spec,
    get_agents_md,
    GenerateSpecResult,
)

# Lint operations
from neptune_cli.services.lint import run_ai_lint

# Logs operations
from neptune_cli.services.logs import get_logs, LogsResult

# Schema operations
from neptune_cli.services.schema import get_project_schema

__all__ = [
    # Project operations
    "get_project_status",
    "list_projects",
    "delete_project",
    "wait_for_deployment",
    "wait_for_provisioning",
    "ProjectStatus",
    "ProjectSummary",
    "ProjectNotFoundError",
    "DeploymentError",
    # Resource operations
    "get_resource_info",
    "set_secret_value",
    "get_database_connection_info",
    "list_bucket_files",
    "get_bucket_object",
    "ResourceInfo",
    "DatabaseConnectionInfo",
    "ResourceNotFoundError",
    # Deployment operations
    "provision_resources",
    "deploy_project",
    "run_preflight_checks",
    "generate_or_load_spec",
    "assess_lint_results",
    "build_and_push_image",
    "get_dockerfile_guidance",
    "detect_project_type",
    "PreflightResult",
    "SpecResult",
    "LintAssessment",
    "ProvisionResult",
    "DeployResult",
    "DockerfileGuidance",
    "NeptuneJsonNotFoundError",
    "DockerfileNotFoundError",
    "DockerNotAvailableError",
    "DockerBuildError",
    "DockerPushError",
    "DockerLoginError",
    "SpecGenerationError",
    "LintBlockingError",
    "ProvisioningError",
    "DeploymentCreationError",
    # Generation operations
    "generate_spec",
    "get_agents_md",
    "GenerateSpecResult",
    # Lint operations
    "run_ai_lint",
    # Logs operations
    "get_logs",
    "LogsResult",
    # Schema operations
    "get_project_schema",
]
