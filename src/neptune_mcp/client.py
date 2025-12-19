from dataclasses import dataclass
from typing import Any

import httpx
from neptune_common import (
    GetLogsResponse,
    GetProjectResponse,
    ListBucketKeysResponse,
    ListProjectsResponse,
    PostDeploymentResponse,
    PutProjectRequest,
    QueryDatabaseRequest,
)
import requests

from neptune_mcp.config import SETTINGS


@dataclass
class Client:
    api_base_url: str = SETTINGS.api_base_url

    def _mk_url(self, path: str) -> str:
        return f"{self.api_base_url}/{path.lstrip('/')}"

    def _get_headers(self) -> dict[str, str]:
        """Generate headers with bearer token if access_token is set."""
        headers = {}
        if SETTINGS.access_token is not None:
            headers["Authorization"] = f"Bearer {SETTINGS.access_token}"
        return headers

    def create_project(self, request: PutProjectRequest) -> None:
        response = requests.post(
            self._mk_url("/project"), json=request.model_dump(mode="json"), headers=self._get_headers()
        )
        response.raise_for_status()

    def update_project(self, request: PutProjectRequest) -> None:
        response = requests.put(
            self._mk_url(f"/project/{request.name}"),
            json=request.model_dump(mode="json"),
            headers=self._get_headers(),
        )
        response.raise_for_status()

    def delete_project(self, project_name: str) -> None:
        response = requests.delete(self._mk_url(f"/project/{project_name}"), headers=self._get_headers())
        response.raise_for_status()

    def get_project(self, project_name: str) -> GetProjectResponse | None:
        response = requests.get(self._mk_url(f"/project/{project_name}"), headers=self._get_headers())
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return GetProjectResponse.model_validate(response.json())

    def create_deployment(self, project_name: str) -> PostDeploymentResponse:
        response = requests.post(self._mk_url(f"/project/{project_name}/deploy"), headers=self._get_headers())
        response.raise_for_status()
        return PostDeploymentResponse.model_validate(response.json())

    async def create_deployment_async(self, project_name: str) -> PostDeploymentResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(self._mk_url(f"/project/{project_name}/deploy"), headers=self._get_headers())
            response.raise_for_status()
            return PostDeploymentResponse.model_validate(response.json())

    def get_deployment(self, project_name: str, revision: str | int = "latest") -> PostDeploymentResponse:
        response = requests.get(
            self._mk_url(f"/project/{project_name}/deploy/{revision}"),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return PostDeploymentResponse.model_validate(response.json())

    async def get_deployment_async(self, project_name: str, revision: str | int = "latest") -> PostDeploymentResponse:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self._mk_url(f"/project/{project_name}/deploy/{revision}"),
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return PostDeploymentResponse.model_validate(response.json())

    def get_logs(self, project_name: str) -> GetLogsResponse:
        response = requests.get(self._mk_url(f"/project/{project_name}/logs"), headers=self._get_headers())
        response.raise_for_status()
        return GetLogsResponse.model_validate(response.json())

    def set_secret_value(self, project_name: str, key: str, value: str) -> None:
        requests.put(
            self._mk_url(f"/project/{project_name}/secret"),
            json={"secret_name": key, "secret_string": value},
            headers=self._get_headers(),
        )

    def list_bucket_keys(self, project_name: str, bucket_name: str) -> list[str]:
        response = requests.get(
            self._mk_url(f"/project/{project_name}/bucket/{bucket_name}"),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return ListBucketKeysResponse.model_validate(response.json()).keys

    def get_bucket_object(self, project_name: str, bucket_name: str, key: str) -> bytes:
        response = requests.get(
            self._mk_url(f"/project/{project_name}/bucket/{bucket_name}/object/{key}"),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.content

    def get_project_schema(self) -> dict[str, Any]:
        """Get the JSON schema that defines valid neptune.json configurations.

        Returns:
            JSON schema definition for project configuration (neptune.json)
        """
        response = requests.get(
            self._mk_url("/schema/project"),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def list_projects(self) -> ListProjectsResponse:
        response = requests.get(self._mk_url("/project"), headers=self._get_headers())
        response.raise_for_status()
        return ListProjectsResponse.model_validate(response.json())

    def query_database(self, project_name: str, database_name: str, request: QueryDatabaseRequest) -> dict[str, Any]:
        response = requests.post(
            self._mk_url(f"/project/{project_name}/database/{database_name}/query"),
            json=request.model_dump(mode="json"),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()
