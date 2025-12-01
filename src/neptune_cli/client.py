"""API client for Neptune platform and AI service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import requests

from neptune_cli.config import ResolvedConfig, load_config

if TYPE_CHECKING:
    from neptune_cli.types import AiLintReport, GenerateResponse, Spec

# Import models from neptune_api
from neptune_api.models import (
    GetDatabaseConnectionInfoResponse,
    GetLogsResponse,
    GetProjectResponse,
    ListBucketKeysResponse,
    PostDeploymentResponse,
    PutProjectRequest,
)

# Version header
CLI_VERSION = "0.1.0"


@dataclass
class Client:
    """Client for Neptune platform API and AI service.

    Handles both the platform API (for project/deployment management)
    and the AI service (for spec generation, linting).
    """

    config: ResolvedConfig = field(default_factory=lambda: load_config())
    timeout: int = 60
    ai_timeout: int = 300  # Longer timeout for AI operations

    @property
    def api_base_url(self) -> str:
        return self.config.api_url

    @property
    def ai_base_url(self) -> str:
        return self.config.ai_url

    def _get_headers(self) -> dict[str, str]:
        """Generate headers with authentication."""
        headers = {
            "X-Neptune-CLI-Version": CLI_VERSION,
            "Content-Type": "application/json",
        }
        token = self.config.auth_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _mk_url(self, path: str) -> str:
        """Build platform API URL."""
        return f"{self.api_base_url}/{path.lstrip('/')}"

    def _mk_ai_url(self, path: str) -> str:
        """Build AI service URL."""
        return f"{self.ai_base_url}/{path.lstrip('/')}"

    # ==========================================================================
    # Platform API - Projects
    # ==========================================================================

    def get_projects(self) -> list[GetProjectResponse]:
        """List all projects.

        Note: This endpoint may not exist in the current API version.
        Falls back to empty list if not available.
        """
        try:
            response = requests.get(
                self._mk_url("/projects"),
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            # Handle both array and {projects: [...]} response formats
            if isinstance(data, list):
                return [GetProjectResponse.model_validate(p) for p in data]
            elif isinstance(data, dict) and "projects" in data:
                return [GetProjectResponse.model_validate(p) for p in data["projects"]]
            return []
        except Exception:
            return []

    def get_project(self, project_name: str) -> GetProjectResponse | None:
        """Get a project by name."""
        response = requests.get(
            self._mk_url(f"/project/{project_name}"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return GetProjectResponse.model_validate(response.json())

    def create_project(self, request: PutProjectRequest) -> None:
        """Create a new project."""
        response = requests.post(
            self._mk_url("/project"),
            json=request.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

    def update_project(self, request: PutProjectRequest) -> None:
        """Update an existing project."""
        response = requests.put(
            self._mk_url(f"/project/{request.name}"),
            json=request.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

    def delete_project(self, project_name: str) -> None:
        """Delete a project."""
        response = requests.delete(
            self._mk_url(f"/project/{project_name}"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

    # ==========================================================================
    # Platform API - Deployments
    # ==========================================================================

    def create_deployment(self, project_name: str) -> PostDeploymentResponse:
        """Create a new deployment."""
        response = requests.post(
            self._mk_url(f"/project/{project_name}/deploy"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return PostDeploymentResponse.model_validate(response.json())

    def get_deployment(self, project_name: str, revision: str | int = "latest") -> PostDeploymentResponse:
        """Get deployment status."""
        response = requests.get(
            self._mk_url(f"/project/{project_name}/deploy/{revision}"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return PostDeploymentResponse.model_validate(response.json())

    def get_logs(self, project_name: str) -> GetLogsResponse:
        """Get project logs."""
        response = requests.get(
            self._mk_url(f"/project/{project_name}/logs"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return GetLogsResponse.model_validate(response.json())

    # ==========================================================================
    # Platform API - Resources
    # ==========================================================================

    def set_secret_value(self, project_name: str, key: str, value: str) -> None:
        """Set a secret value."""
        requests.put(
            self._mk_url(f"/project/{project_name}/secret"),
            json={"secret_name": key, "secret_string": value},
            headers=self._get_headers(),
            timeout=self.timeout,
        )

    def list_bucket_keys(self, project_name: str, bucket_name: str) -> list[str]:
        """List keys in a storage bucket."""
        response = requests.get(
            self._mk_url(f"/project/{project_name}/bucket/{bucket_name}"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return ListBucketKeysResponse.model_validate(response.json()).keys

    def get_bucket_object(self, project_name: str, bucket_name: str, key: str) -> bytes:
        """Get an object from a storage bucket."""
        response = requests.get(
            self._mk_url(f"/project/{project_name}/bucket/{bucket_name}/object/{key}"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content

    def get_database_connection_info(self, project_name: str, database_name: str) -> GetDatabaseConnectionInfoResponse:
        """Get database connection information."""
        response = requests.get(
            self._mk_url(f"/project/{project_name}/database/{database_name}/connection-info"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return GetDatabaseConnectionInfoResponse.model_validate(response.json())

    # ==========================================================================
    # Platform API - Schema
    # ==========================================================================

    def get_project_schema(self) -> dict[str, Any]:
        """Get the JSON schema that defines valid neptune.json configurations.

        This schema is the authoritative reference for creating neptune.json files,
        defining the structure, required fields, resource types, and valid values.

        Returns:
            JSON schema definition for project configuration (neptune.json)
        """
        response = requests.get(
            self._mk_url("/schema/project"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ==========================================================================
    # Platform API - Auth
    # ==========================================================================

    def get_current_user(self) -> dict[str, Any]:
        """Get the current authenticated user."""
        response = requests.get(
            self._mk_url("/users/me"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_registry_auth(self, project_id: str) -> dict[str, Any]:
        """Get registry authentication for pushing images."""
        response = requests.post(
            self._mk_url(f"/projects/{project_id}/registry_auth"),
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # ==========================================================================
    # AI Service
    # ==========================================================================

    def get_agents_md(self) -> str:
        """Get the AGENTS.md content from AI service."""
        response = requests.get(
            self._mk_ai_url("/v1/agents.md"),
            headers=self._get_headers(),
            timeout=self.ai_timeout,
        )
        response.raise_for_status()
        return response.text

    def generate_spec(self, project_archive: bytes, project_name: str) -> Spec:
        """Generate a platform spec from project archive.

        Args:
            project_archive: ZIP archive of the project
            project_name: Name of the project

        Returns:
            Generated platform spec
        """
        from neptune_cli.types import Spec

        headers = self._get_headers()
        del headers["Content-Type"]  # Let requests set multipart content-type

        response = requests.post(
            self._mk_ai_url("/v1/generate/spec"),
            headers=headers,
            files={"project": ("proj.zip", project_archive, "application/octet-stream")},
            data={"project_name": project_name},
            timeout=self.ai_timeout,
        )
        response.raise_for_status()
        return Spec.model_validate(response.json())

    def generate(self, project_archive: bytes, project_name: str) -> GenerateResponse:
        """Generate spec, lint report, and start command from project archive.

        Args:
            project_archive: ZIP archive of the project
            project_name: Name of the project

        Returns:
            Complete generation response including spec, lint report, start command
        """
        from neptune_cli.types import GenerateResponse

        headers = self._get_headers()
        del headers["Content-Type"]  # Let requests set multipart content-type

        response = requests.post(
            self._mk_ai_url("/v1/generate"),
            headers=headers,
            files={"project": ("proj.zip", project_archive, "application/octet-stream")},
            data={"project_name": project_name},
            timeout=self.ai_timeout,
        )
        response.raise_for_status()
        return GenerateResponse.model_validate(response.json())

    def ai_lint(self, project_archive: bytes) -> AiLintReport:
        """Run AI lint on project archive.

        Args:
            project_archive: ZIP archive of the project

        Returns:
            AI lint report
        """
        from neptune_cli.types import AiLintReport

        headers = self._get_headers()
        del headers["Content-Type"]  # Let requests set multipart content-type

        response = requests.post(
            self._mk_ai_url("/v1/lint"),
            headers=headers,
            files={"project": ("proj.zip", project_archive, "application/zip")},
            timeout=self.ai_timeout,
        )
        response.raise_for_status()

        data = response.json()
        # Handle both response formats
        if "ai_lint_report" in data:
            return AiLintReport.model_validate(data["ai_lint_report"])
        return AiLintReport.model_validate(data)


# Convenience function for creating a client with current settings
def get_client() -> Client:
    """Get a client configured from current settings."""
    return Client(config=load_config())
