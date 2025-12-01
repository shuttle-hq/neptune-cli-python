"""Deployment-related services.

These services handle project provisioning and deployment operations.
All business logic for deployments lives here - CLI and MCP are thin wrappers.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from neptune_cli.client import Client, get_client
from neptune_cli.utils import (
    create_project_archive,
    docker_installed,
    docker_running,
    read_neptune_json,
    read_start_command,
    resolve_project_name,
    ai_spec_to_platform_request,
    write_neptune_json,
    write_start_command,
)

from neptune_api.models import PutProjectRequest


# ==============================================================================
# Exceptions
# ==============================================================================


class NeptuneJsonNotFoundError(Exception):
    """Raised when neptune.json is not found."""

    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"neptune.json not found at {path}")


class DockerfileNotFoundError(Exception):
    """Raised when Dockerfile is not found."""

    def __init__(self, path: Path, guidance: "DockerfileGuidance | None" = None):
        self.path = path
        self.guidance = guidance
        super().__init__(f"Dockerfile not found at {path}")


class DockerNotAvailableError(Exception):
    """Raised when Docker is not installed or not running."""

    def __init__(self, message: str, is_running_issue: bool = False):
        self.is_running_issue = is_running_issue
        super().__init__(message)


class DockerBuildError(Exception):
    """Raised when Docker build fails."""

    def __init__(self, message: str, output: str | None = None):
        self.output = output
        super().__init__(message)


class DockerPushError(Exception):
    """Raised when Docker push fails."""

    def __init__(self, message: str, output: str | None = None):
        self.output = output
        super().__init__(message)


class DockerLoginError(Exception):
    """Raised when Docker login fails."""

    def __init__(self, message: str):
        super().__init__(message)


class SpecGenerationError(Exception):
    """Raised when spec generation fails."""

    def __init__(self, message: str):
        super().__init__(message)


class LintBlockingError(Exception):
    """Raised when lint findings block deployment."""

    def __init__(self, reasons: list[str], report: Any):
        self.reasons = reasons
        self.report = report
        super().__init__(f"Deployment blocked by lint: {', '.join(reasons)}")


class ProvisioningError(Exception):
    """Raised when project provisioning fails."""

    def __init__(self, message: str):
        super().__init__(message)


class DeploymentCreationError(Exception):
    """Raised when deployment creation fails."""

    def __init__(self, message: str):
        super().__init__(message)


# ==============================================================================
# Data Classes
# ==============================================================================


@dataclass
class DockerfileGuidance:
    """Guidance for creating a Dockerfile."""

    project_type: str
    detected_files: list[str]
    start_command: str | None
    dockerfile_example: str
    requirements: list[str]
    best_practices: list[str]
    dockerfile_exists: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_type": self.project_type,
            "detected_files": self.detected_files,
            "start_command": self.start_command,
            "dockerfile_exists": self.dockerfile_exists,
            "dockerfile_example": self.dockerfile_example,
            "requirements": self.requirements,
            "best_practices": self.best_practices,
        }


@dataclass
class PreflightResult:
    """Result of preflight checks."""

    dockerfile_exists: bool
    docker_available: bool
    docker_running: bool
    dockerfile_guidance: DockerfileGuidance | None = None


@dataclass
class SpecResult:
    """Result of spec generation/loading."""

    spec: dict[str, Any]
    spec_path: Path
    start_command: str | None
    generated: bool  # True if generated, False if loaded existing
    ai_lint_report: Any | None = None


@dataclass
class LintAssessment:
    """Assessment of whether lint findings should block deployment."""

    blocking: bool = False
    reasons: list[str] = field(default_factory=list)


@dataclass
class ProvisionResult:
    """Result of provisioning operation."""

    project_name: str
    provisioning_state: str
    resources: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "infrastructure_status": self.provisioning_state,
            "infrastructure_resources": self.resources,
        }


@dataclass
class DeployResult:
    """Result of deployment operation."""

    project_name: str
    revision: str | int
    status: str
    image: str
    provisioning_state: str | None = None
    running_status: dict[str, Any] | None = None
    url: str | None = None
    resources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "deployment_revision": self.revision,
            "deployment_status": self.status,
            "image": self.image,
            "provisioning_state": self.provisioning_state,
            "running_status": self.running_status,
            "url": self.url,
            "resources": self.resources,
        }


# ==============================================================================
# Dockerfile Templates
# ==============================================================================


DOCKERFILE_TEMPLATES: dict[str, str] = {
    "python": """FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Neptune expects 8080 by default)
EXPOSE 8080

# Start the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]""",
    "nodejs": """FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Expose port (Neptune expects 8080 by default)
EXPOSE 8080

# Start the application
CMD ["node", "index.js"]""",
    "go": """FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.* ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/server .

EXPOSE 8080
CMD ["./server"]""",
    "rust": """FROM rust:1.75 AS builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src

RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/app /usr/local/bin/app

EXPOSE 8080
CMD ["app"]""",
    "unknown": """# Adjust this Dockerfile based on your project type
FROM python:3.12-slim

WORKDIR /app

# Install dependencies (adjust based on your dependency file)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Neptune expects port 8080 by default
EXPOSE 8080

# Replace with your actual start command
CMD ["python", "main.py"]""",
}


# ==============================================================================
# Service Functions
# ==============================================================================


def detect_project_type(working_dir: Path) -> tuple[str, list[str]]:
    """Detect project type from files in directory.

    Returns:
        Tuple of (project_type, detected_files)
    """
    detected_files = []
    project_type = "unknown"

    # Check for Python
    if (working_dir / "requirements.txt").exists():
        project_type = "python"
        detected_files.append("requirements.txt")
    if (working_dir / "pyproject.toml").exists():
        project_type = "python"
        detected_files.append("pyproject.toml")

    # Check for Node.js
    if (working_dir / "package.json").exists():
        project_type = "nodejs"
        detected_files.append("package.json")

    # Check for Go
    if (working_dir / "go.mod").exists():
        project_type = "go"
        detected_files.append("go.mod")

    # Check for Rust
    if (working_dir / "Cargo.toml").exists():
        project_type = "rust"
        detected_files.append("Cargo.toml")

    return project_type, detected_files


def get_dockerfile_guidance(working_dir: Path) -> DockerfileGuidance:
    """Get guidance for creating a Dockerfile.

    Args:
        working_dir: Project directory

    Returns:
        DockerfileGuidance with template and instructions
    """
    dockerfile_exists = (working_dir / "Dockerfile").exists()
    project_type, detected_files = detect_project_type(working_dir)
    start_command = read_start_command(working_dir)
    template = DOCKERFILE_TEMPLATES.get(project_type, DOCKERFILE_TEMPLATES["unknown"])

    # Customize template with start command if available
    if start_command:
        template = template.replace(
            "# Start the application",
            f"# Detected start command: {start_command}",
        )

    return DockerfileGuidance(
        project_type=project_type,
        detected_files=detected_files,
        start_command=start_command,
        dockerfile_example=template,
        dockerfile_exists=dockerfile_exists,
        requirements=[
            "Application must listen on port 8080 (or configure port_mappings)",
            "Image will be built for linux/amd64 architecture",
        ],
        best_practices=[
            "Use multi-stage builds for compiled languages to reduce image size",
            "Only include production dependencies",
            "Don't include secrets or credentials in the image",
            "Use .dockerignore to exclude unnecessary files",
        ],
    )


def run_preflight_checks(working_dir: Path) -> PreflightResult:
    """Run preflight checks before deployment.

    Args:
        working_dir: Project directory

    Returns:
        PreflightResult with check results
    """
    dockerfile_path = working_dir / "Dockerfile"
    dockerfile_exists = dockerfile_path.exists()

    guidance = None
    if not dockerfile_exists:
        guidance = get_dockerfile_guidance(working_dir)

    return PreflightResult(
        dockerfile_exists=dockerfile_exists,
        docker_available=docker_installed(),
        docker_running=docker_running(),
        dockerfile_guidance=guidance,
    )


def generate_or_load_spec(
    working_dir: Path,
    project_name: str,
    skip_generation: bool = False,
    skip_lint: bool = False,
    client: Client | None = None,
) -> SpecResult:
    """Generate or load project spec.

    Args:
        working_dir: Project directory
        project_name: Name of the project
        skip_generation: If True, only load existing spec
        skip_lint: If True, don't include lint report
        client: Optional client instance

    Returns:
        SpecResult with spec and metadata

    Raises:
        NeptuneJsonNotFoundError: If skip_generation=True and no spec exists
        SpecGenerationError: If generation fails
    """
    client = client or get_client()
    spec_path = working_dir / "neptune.json"

    if skip_generation:
        if not spec_path.exists():
            raise NeptuneJsonNotFoundError(spec_path)

        spec = read_neptune_json(working_dir)
        start_command = read_start_command(working_dir)

        # Run lint separately if requested
        ai_lint_report = None
        if not skip_lint:
            try:
                archive = create_project_archive(working_dir)
                ai_lint_report = client.ai_lint(archive)
            except Exception as e:
                raise SpecGenerationError(f"Failed to run AI lint: {e}") from e

        return SpecResult(
            spec=spec,
            spec_path=spec_path,
            start_command=start_command,
            generated=False,
            ai_lint_report=ai_lint_report,
        )

    # Generate new spec
    try:
        archive = create_project_archive(working_dir)
        gen_response = client.generate(archive, project_name)
    except Exception as e:
        raise SpecGenerationError(f"Failed to generate spec: {e}") from e

    # Convert to platform format
    ai_spec = gen_response.platform_spec.model_dump(mode="json")
    new_spec = ai_spec_to_platform_request(ai_spec, project_name)

    # Write spec
    write_neptune_json(new_spec, working_dir)

    # Save start command
    if gen_response.start_command:
        write_start_command(working_dir, gen_response.start_command)

    return SpecResult(
        spec=new_spec,
        spec_path=spec_path,
        start_command=gen_response.start_command,
        generated=True,
        ai_lint_report=gen_response.ai_lint_report if not skip_lint else None,
    )


def assess_lint_results(
    report: Any,
    allow_errors: bool = False,
    allow_warnings: bool = False,
) -> LintAssessment:
    """Assess whether lint findings should block deployment.

    Args:
        report: AI lint report
        allow_errors: If True, don't block on errors
        allow_warnings: If True, don't block on warnings

    Returns:
        LintAssessment with blocking status and reasons
    """
    if report is None:
        return LintAssessment(blocking=False)

    reasons = []

    # Check if report indicates blocking
    if hasattr(report, "summary"):
        if report.summary.blocking and report.summary.blocking_reason:
            reasons.append(report.summary.blocking_reason)

    # Check errors
    if hasattr(report, "errors") and report.errors and not allow_errors:
        reasons.append(f"{len(report.errors)} error(s) found")

    # Check warnings with block_on_warnings config
    if hasattr(report, "warnings") and report.warnings:
        if hasattr(report, "config") and report.config.block_on_warnings and not allow_warnings:
            reasons.append(f"{len(report.warnings)} warning(s) found (block_on_warnings enabled)")

    return LintAssessment(
        blocking=len(reasons) > 0,
        reasons=reasons,
    )


def provision_resources(
    working_dir: Path | None = None,
    client: Client | None = None,
    poll_interval: float = 2.0,
    on_status: Callable[[str], None] | None = None,
) -> ProvisionResult:
    """Provision cloud resources for a project.

    Args:
        working_dir: Directory containing neptune.json
        client: Optional client instance
        poll_interval: Seconds between status checks
        on_status: Optional callback for status updates

    Returns:
        ProvisionResult with final status

    Raises:
        NeptuneJsonNotFoundError: If neptune.json doesn't exist
        ProvisioningError: If provisioning fails
    """
    working_dir = working_dir or Path.cwd()
    client = client or get_client()

    def status(msg: str):
        if on_status:
            on_status(msg)

    # Read neptune.json
    neptune_json_path = working_dir / "neptune.json"
    project_data = read_neptune_json(working_dir)

    if project_data is None:
        raise NeptuneJsonNotFoundError(neptune_json_path)

    project_request = PutProjectRequest.model_validate(project_data)
    project_name = project_request.name

    # Create or update project
    try:
        existing = client.get_project(project_name)
        if existing is None:
            status(f"Creating project '{project_name}'...")
            client.create_project(project_request)
        else:
            status(f"Updating project '{project_name}'...")
            client.update_project(project_request)
    except Exception as e:
        raise ProvisioningError(f"Failed to create/update project: {e}") from e

    # Wait for provisioning
    status("Waiting for infrastructure to be ready...")
    project = client.get_project(project_name)
    while project and project.provisioning_state != "Ready":
        time.sleep(poll_interval)
        project = client.get_project(project_name)

    # Wait for all resources
    if project:
        all_ready = False
        while not all_ready:
            all_ready = all(r.status != "Pending" for r in project.resources)
            if not all_ready:
                time.sleep(poll_interval)
                project = client.get_project(project_name)

    resources = [r.model_dump() for r in project.resources] if project else []

    return ProvisionResult(
        project_name=project_name,
        provisioning_state=project.provisioning_state if project else "Unknown",
        resources=resources,
    )


def build_and_push_image(
    working_dir: Path,
    image_tag: str,
    push_token: str | None = None,
    on_status: Callable[[str], None] | None = None,
) -> None:
    """Build and push Docker image.

    Args:
        working_dir: Project directory with Dockerfile
        image_tag: Full image tag to build and push
        push_token: Optional registry authentication token
        on_status: Optional callback for status updates

    Raises:
        DockerLoginError: If registry login fails
        DockerBuildError: If build fails
        DockerPushError: If push fails
    """

    def status(msg: str):
        if on_status:
            on_status(msg)

    # Docker login if we have a token
    if push_token:
        registry = image_tag.split("/")[0]
        status(f"Logging in to registry {registry}...")

        login_cmd = ["docker", "login", "-u", "AWS", "--password-stdin", registry]
        login_proc = subprocess.Popen(
            login_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        _, stderr = login_proc.communicate(input=push_token.encode())

        if login_proc.returncode != 0:
            raise DockerLoginError(f"Docker login failed: {stderr.decode() if stderr else 'unknown error'}")

    # Build image
    status("Building Docker image...")

    build_cmd = [
        "docker",
        "build",
        "--platform",
        "linux/amd64",
        "-t",
        image_tag,
        "-f",
        "Dockerfile",
        str(working_dir),
    ]

    try:
        subprocess.run(
            build_cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise DockerBuildError(
            "Docker build failed",
            output=e.stderr[-2000:] if e.stderr else None,
        ) from e
    except FileNotFoundError:
        raise DockerNotAvailableError("Docker is not installed or not in PATH")

    # Push image
    status("Pushing image to registry...")

    push_cmd = ["docker", "push", image_tag]

    try:
        subprocess.run(push_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise DockerPushError(
            "Docker push failed",
            output=e.stderr[-2000:] if e.stderr else None,
        ) from e


def deploy_project(
    working_dir: Path | None = None,
    skip_spec: bool = False,
    skip_lint: bool = False,
    allow_lint_errors: bool = False,
    allow_lint_warnings: bool = False,
    client: Client | None = None,
    poll_interval: float = 2.0,
    on_status: Callable[[str], None] | None = None,
    on_lint_report: Callable[[Any], None] | None = None,
) -> DeployResult:
    """Deploy a project to Neptune.

    This is the main deployment function that orchestrates:
    1. Preflight checks (Dockerfile, Docker)
    2. Spec generation/loading
    3. Lint validation
    4. Provisioning
    5. Docker build/push
    6. Deployment creation and waiting

    Args:
        working_dir: Project directory
        skip_spec: If True, use existing neptune.json
        skip_lint: If True, skip lint validation
        allow_lint_errors: If True, don't block on lint errors
        allow_lint_warnings: If True, don't block on lint warnings
        client: Optional client instance
        poll_interval: Seconds between status checks
        on_status: Optional callback for status updates
        on_lint_report: Optional callback when lint report is available

    Returns:
        DeployResult with deployment information

    Raises:
        DockerfileNotFoundError: If no Dockerfile exists
        DockerNotAvailableError: If Docker not installed/running
        NeptuneJsonNotFoundError: If skip_spec and no neptune.json
        SpecGenerationError: If spec generation fails
        LintBlockingError: If lint blocks deployment
        ProvisioningError: If provisioning fails
        DeploymentCreationError: If deployment creation fails
        DockerBuildError: If Docker build fails
        DockerPushError: If Docker push fails
    """
    working_dir = working_dir or Path.cwd()
    client = client or get_client()

    def status(msg: str):
        if on_status:
            on_status(msg)

    # Step 1: Preflight checks
    status("Running preflight checks...")
    preflight = run_preflight_checks(working_dir)

    if not preflight.dockerfile_exists:
        raise DockerfileNotFoundError(
            working_dir / "Dockerfile",
            guidance=preflight.dockerfile_guidance,
        )

    if not preflight.docker_available:
        raise DockerNotAvailableError("Docker is not installed or not in PATH")

    if not preflight.docker_running:
        raise DockerNotAvailableError("Docker daemon is not running", is_running_issue=True)

    # Resolve project name
    try:
        project_name = resolve_project_name(working_dir)
    except Exception:
        project_name = working_dir.name

    # Step 2: Generate or load spec
    status("Processing project configuration...")
    spec_result = generate_or_load_spec(
        working_dir,
        project_name,
        skip_generation=skip_spec,
        skip_lint=skip_lint,
        client=client,
    )

    # Step 3: Check lint results
    if spec_result.ai_lint_report:
        if on_lint_report:
            on_lint_report(spec_result.ai_lint_report)

        assessment = assess_lint_results(
            spec_result.ai_lint_report,
            allow_errors=allow_lint_errors,
            allow_warnings=allow_lint_warnings,
        )

        if assessment.blocking:
            raise LintBlockingError(assessment.reasons, spec_result.ai_lint_report)

    # Step 4: Provision infrastructure
    status("Provisioning infrastructure...")
    provision_resources(
        working_dir,
        client=client,
        poll_interval=poll_interval,
        on_status=on_status,
    )

    # Step 5: Create deployment
    status("Creating deployment...")
    try:
        deployment = client.create_deployment(project_name)
    except Exception as e:
        raise DeploymentCreationError(f"Failed to create deployment: {e}") from e

    # Step 6: Build and push image
    status(f"Building and pushing image for revision {deployment.revision}...")
    build_and_push_image(
        working_dir,
        deployment.image,
        push_token=deployment.push_token,
        on_status=on_status,
    )

    # Step 7: Wait for deployment
    status("Waiting for deployment to complete...")
    while deployment.status != "Deployed":
        time.sleep(poll_interval)
        deployment = client.get_deployment(project_name, deployment.revision)

    # Get final project status
    project = client.get_project(project_name)
    url = None
    running_status = None
    resources = []

    if project:
        if project.running_status:
            running_status = project.running_status.model_dump()
            if project.running_status.public_ip:
                url = f"http://{project.running_status.public_ip}"
        resources = [r.model_dump() for r in project.resources]

    return DeployResult(
        project_name=project_name,
        revision=deployment.revision,
        status=deployment.status,
        image=deployment.image,
        provisioning_state=project.provisioning_state if project else None,
        running_status=running_status,
        url=url,
        resources=resources,
    )
