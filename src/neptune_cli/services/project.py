"""Project-related services.

These services handle project lifecycle operations like status, listing,
deletion, and waiting for state changes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from neptune_cli.client import Client, get_client

if TYPE_CHECKING:
    from neptune_api.models import GetProjectResponse


class ProjectNotFoundError(Exception):
    """Raised when a project is not found."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        super().__init__(f"Project '{project_name}' not found")


class DeploymentError(Exception):
    """Raised when a deployment fails or enters an error state."""

    def __init__(self, project_name: str, state: str, message: str | None = None):
        self.project_name = project_name
        self.state = state
        super().__init__(message or f"Project '{project_name}' is in state '{state}'")


@dataclass
class ProjectStatus:
    """Status information for a project."""

    name: str
    kind: str
    provisioning_state: str
    running_status: dict[str, Any]
    resources: list[dict[str, Any]]
    url: str | None = None

    @classmethod
    def from_response(cls, project: GetProjectResponse) -> ProjectStatus:
        """Create from API response."""
        url = None
        if project.running_status and project.running_status.public_ip:
            url = f"http://{project.running_status.public_ip}"

        return cls(
            name=project.name,
            kind=project.kind,
            provisioning_state=project.provisioning_state,
            running_status=project.running_status.model_dump() if project.running_status else {},
            resources=[r.model_dump() for r in project.resources],
            url=url,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind,
            "provisioning_state": self.provisioning_state,
            "running_status": self.running_status,
            "resources": self.resources,
            "url": self.url,
        }


@dataclass
class ProjectSummary:
    """Summary information for a project (used in list)."""

    name: str
    kind: str
    provisioning_state: str
    running_status: str
    resource_count: int
    url: str | None = None

    @classmethod
    def from_response(cls, project: GetProjectResponse) -> ProjectSummary:
        """Create from API response."""
        url = None
        running = "Unknown"

        if project.running_status:
            running = project.running_status.current or "Unknown"
            if project.running_status.public_ip:
                url = f"http://{project.running_status.public_ip}"

        return cls(
            name=project.name,
            kind=project.kind,
            provisioning_state=project.provisioning_state,
            running_status=running,
            resource_count=len(project.resources),
            url=url,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind,
            "provisioning_state": self.provisioning_state,
            "running_status": self.running_status,
            "resource_count": self.resource_count,
            "url": self.url,
        }


def get_project_status(
    project_name: str,
    client: Client | None = None,
) -> ProjectStatus:
    """Get the status of a project.

    Args:
        project_name: Name of the project
        client: Optional client instance (creates new one if not provided)

    Returns:
        ProjectStatus with current state

    Raises:
        ProjectNotFoundError: If project doesn't exist
    """
    client = client or get_client()
    project = client.get_project(project_name)

    if project is None:
        raise ProjectNotFoundError(project_name)

    return ProjectStatus.from_response(project)


def list_projects(client: Client | None = None) -> list[ProjectSummary]:
    """List all projects.

    Args:
        client: Optional client instance

    Returns:
        List of project summaries
    """
    client = client or get_client()
    projects = client.get_projects()
    return [ProjectSummary.from_response(p) for p in projects]


def delete_project(
    project_name: str,
    client: Client | None = None,
) -> None:
    """Delete a project.

    Args:
        project_name: Name of the project to delete
        client: Optional client instance

    Raises:
        ProjectNotFoundError: If project doesn't exist
    """
    client = client or get_client()

    # Check if project exists first
    project = client.get_project(project_name)
    if project is None:
        raise ProjectNotFoundError(project_name)

    client.delete_project(project_name)


def wait_for_deployment(
    project_name: str,
    client: Client | None = None,
    poll_interval: float = 2.0,
    timeout: float | None = None,
) -> ProjectStatus:
    """Wait for a project's deployment to reach Running state.

    Args:
        project_name: Name of the project
        client: Optional client instance
        poll_interval: Seconds between status checks
        timeout: Maximum seconds to wait (None for no timeout)

    Returns:
        Final project status

    Raises:
        ProjectNotFoundError: If project doesn't exist
        DeploymentError: If deployment enters error state
        TimeoutError: If timeout is exceeded
    """
    client = client or get_client()
    start_time = time.time()

    while True:
        project = client.get_project(project_name)
        if project is None:
            raise ProjectNotFoundError(project_name)

        running_status = project.running_status.current if project.running_status else None

        if running_status == "Running":
            return ProjectStatus.from_response(project)

        if running_status in ["Stopped", "Error"]:
            raise DeploymentError(
                project_name,
                running_status,
                f"Deployment failed: service is in '{running_status}' state",
            )

        if timeout is not None and (time.time() - start_time) > timeout:
            raise TimeoutError(
                f"Timeout waiting for deployment of '{project_name}' " f"(current state: {running_status})"
            )

        time.sleep(poll_interval)


def wait_for_provisioning(
    project_name: str,
    client: Client | None = None,
    poll_interval: float = 2.0,
    timeout: float | None = None,
) -> ProjectStatus:
    """Wait for a project's infrastructure to reach Ready state.

    Args:
        project_name: Name of the project
        client: Optional client instance
        poll_interval: Seconds between status checks
        timeout: Maximum seconds to wait (None for no timeout)

    Returns:
        Final project status

    Raises:
        ProjectNotFoundError: If project doesn't exist
        TimeoutError: If timeout is exceeded
    """
    client = client or get_client()
    start_time = time.time()

    while True:
        project = client.get_project(project_name)
        if project is None:
            raise ProjectNotFoundError(project_name)

        if project.provisioning_state == "Ready":
            # Also check all resources are provisioned
            all_ready = all(r.status != "Pending" for r in project.resources)
            if all_ready:
                return ProjectStatus.from_response(project)

        if timeout is not None and (time.time() - start_time) > timeout:
            raise TimeoutError(
                f"Timeout waiting for provisioning of '{project_name}' "
                f"(current state: {project.provisioning_state})"
            )

        time.sleep(poll_interval)
