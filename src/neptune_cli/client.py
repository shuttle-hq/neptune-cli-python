import requests

from dataclasses import dataclass

from neptune_cli.config import SETTINGS

from neptune_api.models import (
    PutProjectRequest,
    GetProjectResponse,
    PostDeploymentResponse,
    GetLogsResponse,
    ListBucketKeysResponse,
    GetDatabaseConnectionInfoResponse,
)


@dataclass
class Client:
    api_base_url: str = SETTINGS.api_base_url

    def _mk_url(self, path: str) -> str:
        return f"{self.api_base_url}/{path.lstrip('/')}"

    def create_project(self, request: PutProjectRequest) -> None:
        requests.post(self._mk_url(f"/project"), json=request.model_dump(mode="json"))

    def update_project(self, request: PutProjectRequest) -> None:
        requests.put(
            self._mk_url(f"/project/{request.name}"),
            json=request.model_dump(mode="json"),
        )

    def delete_project(self, project_name: str) -> None:
        requests.delete(self._mk_url(f"/project/{project_name}"))

    def get_project(self, project_name: str) -> GetProjectResponse | None:
        response = requests.get(self._mk_url(f"/project/{project_name}"))
        if response.status_code == 404:
            return None
        return GetProjectResponse.model_validate(response.json())

    def create_deployment(self, project_name: str) -> PostDeploymentResponse:
        response = requests.post(self._mk_url(f"/project/{project_name}/deploy"))
        return PostDeploymentResponse.model_validate(response.json())

    def get_deployment(
        self, project_name: str, revision: str | int = "latest"
    ) -> PostDeploymentResponse:
        response = requests.get(
            self._mk_url(f"/project/{project_name}/deploy/{revision}")
        )
        return PostDeploymentResponse.model_validate(response.json())

    def get_logs(self, project_name: str) -> GetLogsResponse:
        response = requests.get(self._mk_url(f"/project/{project_name}/logs"))
        return GetLogsResponse.model_validate(response.json())

    def set_secret_value(self, project_name: str, key: str, value: str) -> None:
        requests.put(
            self._mk_url(f"/project/{project_name}/secret"),
            json={"secret_name": key, "secret_string": value},
        )

    def list_bucket_keys(self, project_name: str, bucket_name: str) -> list[str]:
        response = requests.get(
            self._mk_url(f"/project/{project_name}/bucket/{bucket_name}")
        )
        return ListBucketKeysResponse.model_validate(response.json()).keys

    def get_bucket_object(self, project_name: str, bucket_name: str, key: str) -> bytes:
        response = requests.get(
            self._mk_url(f"/project/{project_name}/bucket/{bucket_name}/object/{key}")
        )
        return response.content

    def get_database_connection_info(
        self, project_name: str, database_name: str
    ) -> GetDatabaseConnectionInfoResponse:
        response = requests.get(
            self._mk_url(
                f"/project/{project_name}/database/{database_name}/connection-info"
            )
        )
        return GetDatabaseConnectionInfoResponse.model_validate(response.json())
