"""Resource-related services.

These services handle operations on project resources like databases,
storage buckets, and secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neptune_cli.client import Client, get_client
from neptune_cli.services.project import ProjectNotFoundError


class ResourceNotFoundError(Exception):
    """Raised when a resource is not found."""

    def __init__(self, project_name: str, resource_kind: str, resource_name: str):
        self.project_name = project_name
        self.resource_kind = resource_kind
        self.resource_name = resource_name
        super().__init__(f"{resource_kind} resource '{resource_name}' not found in project '{project_name}'")


@dataclass
class ResourceInfo:
    """Information about a resource type."""

    kind: str
    description: str
    neptune_json_example: str
    code_usage_example: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "kind": self.kind,
            "description": self.description,
            "neptune_json_configuration": self.neptune_json_example,
            "example_code_usage": self.code_usage_example,
        }


@dataclass
class DatabaseConnectionInfo:
    """Database connection information."""

    host: str
    port: int
    username: str
    password: str
    database: str
    connection_string: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
        }
        if self.connection_string:
            result["connection_string"] = self.connection_string
        return result


# Resource type documentation
RESOURCE_INFO: dict[str, ResourceInfo] = {
    "Database": ResourceInfo(
        kind="Database",
        description="Managed PostgreSQL database instance for your applications.",
        neptune_json_example="""To add a database to a project, add the following to 'resources' in 'neptune.json':

```json
{
    "kind": "Database",
    "name": "<database_name>"
}
```

Full example:

```json
{
  "kind": "Service",
  "name": "my-project",
  "resources": [
    {
      "kind": "Database",
      "name": "main-db"
    }
  ]
}
```""",
        code_usage_example="""After provisioning, get connection info with:
  neptune resource database info <database_name>

Then use in your application:

```python
import psycopg2
# Connection details from `neptune resource database info`
conn = psycopg2.connect(
    host="...",
    port=5432,
    database="...",
    user="...",
    password="..."
)
```

Note: For deployed services, use the environment variables automatically
injected by Neptune rather than hardcoding connection strings.""",
    ),
    "StorageBucket": ResourceInfo(
        kind="StorageBucket",
        description="S3-compatible object storage bucket for files and data.",
        neptune_json_example="""To add a storage bucket to a project, add the following to 'resources' in 'neptune.json':

```json
{
    "kind": "StorageBucket",
    "name": "<bucket_name>"
}
```

Full example:

```json
{
  "kind": "Service",
  "name": "my-project",
  "resources": [
    {
      "kind": "StorageBucket",
      "name": "uploads"
    }
  ]
}
```""",
        code_usage_example="""After provisioning, use boto3 to interact with the bucket:

```python
import boto3

# AWS credentials are automatically available in deployed services
s3 = boto3.client("s3")

# Upload a file
s3.put_object(
    Bucket="<aws_bucket_id>",  # Get from `neptune status`
    Key="path/to/file.txt",
    Body=b"Hello, World!"
)

# Download a file
response = s3.get_object(Bucket="<aws_bucket_id>", Key="path/to/file.txt")
content = response["Body"].read()
```

For local development, use `neptune resource bucket list` and
`neptune resource bucket get` commands.""",
    ),
    "Secret": ResourceInfo(
        kind="Secret",
        description="Secure storage for sensitive values like API keys and credentials.",
        neptune_json_example="""To add a secret to a project, add the following to 'resources' in 'neptune.json':

```json
{
    "kind": "Secret",
    "name": "<secret_name>"
}
```

Full example:

```json
{
  "kind": "Service",
  "name": "my-project",
  "resources": [
    {
      "kind": "Secret",
      "name": "api-key"
    }
  ]
}
```""",
        code_usage_example="""After provisioning, set the secret value:
  neptune resource secret set <secret_name>

Then access in your application:

```python
import boto3

secrets = boto3.client("secretsmanager")
response = secrets.get_secret_value(SecretId="<aws_secret_id>")
secret_value = response["SecretString"]
```

For deployed services, Neptune can also inject secrets as environment
variables - check the resource description in `neptune status`.""",
    ),
}


def get_resource_info(kind: str) -> ResourceInfo:
    """Get information about a resource type.

    Args:
        kind: Resource kind (Database, StorageBucket, Secret)

    Returns:
        ResourceInfo with documentation

    Raises:
        ValueError: If kind is not recognized
    """
    if kind not in RESOURCE_INFO:
        valid_kinds = ", ".join(RESOURCE_INFO.keys())
        raise ValueError(f"Unknown resource kind '{kind}'. Valid kinds are: {valid_kinds}")
    return RESOURCE_INFO[kind]


def _get_resource_from_project(
    project_name: str,
    resource_kind: str,
    resource_name: str,
    client: Client,
):
    """Get a specific resource from a project.

    Raises:
        ProjectNotFoundError: If project doesn't exist
        ResourceNotFoundError: If resource doesn't exist
    """
    project = client.get_project(project_name)
    if project is None:
        raise ProjectNotFoundError(project_name)

    for resource in project.resources:
        if resource.kind == resource_kind and resource.name == resource_name:
            return resource

    raise ResourceNotFoundError(project_name, resource_kind, resource_name)


def set_secret_value(
    project_name: str,
    secret_name: str,
    secret_value: str,
    client: Client | None = None,
) -> None:
    """Set the value of a secret.

    Args:
        project_name: Name of the project
        secret_name: Name of the secret resource
        secret_value: Value to set
        client: Optional client instance

    Raises:
        ProjectNotFoundError: If project doesn't exist
        ResourceNotFoundError: If secret doesn't exist
    """
    client = client or get_client()

    # Verify the secret exists
    _get_resource_from_project(project_name, "Secret", secret_name, client)

    client.set_secret_value(project_name, secret_name, secret_value)


def get_database_connection_info(
    project_name: str,
    database_name: str,
    client: Client | None = None,
) -> DatabaseConnectionInfo:
    """Get connection information for a database.

    Args:
        project_name: Name of the project
        database_name: Name of the database resource
        client: Optional client instance

    Returns:
        DatabaseConnectionInfo with connection details

    Raises:
        ProjectNotFoundError: If project doesn't exist
        ResourceNotFoundError: If database doesn't exist
    """
    client = client or get_client()

    # Verify the database exists
    _get_resource_from_project(project_name, "Database", database_name, client)

    conn_info = client.get_database_connection_info(project_name, database_name)

    return DatabaseConnectionInfo(
        host=conn_info.host,
        port=conn_info.port,
        username=conn_info.username,
        password=conn_info.password,
        database=conn_info.database,
        connection_string=getattr(conn_info, "connection_string", None),
    )


def list_bucket_files(
    project_name: str,
    bucket_name: str,
    client: Client | None = None,
) -> list[str]:
    """List files in a storage bucket.

    Args:
        project_name: Name of the project
        bucket_name: Name of the bucket resource
        client: Optional client instance

    Returns:
        List of file keys

    Raises:
        ProjectNotFoundError: If project doesn't exist
        ResourceNotFoundError: If bucket doesn't exist
    """
    client = client or get_client()

    # Verify the bucket exists
    _get_resource_from_project(project_name, "StorageBucket", bucket_name, client)

    return client.list_bucket_keys(project_name, bucket_name)


def get_bucket_object(
    project_name: str,
    bucket_name: str,
    key: str,
    client: Client | None = None,
) -> bytes:
    """Get an object from a storage bucket.

    Args:
        project_name: Name of the project
        bucket_name: Name of the bucket resource
        key: Object key
        client: Optional client instance

    Returns:
        Object content as bytes

    Raises:
        ProjectNotFoundError: If project doesn't exist
        ResourceNotFoundError: If bucket doesn't exist
    """
    client = client or get_client()

    # Verify the bucket exists
    _get_resource_from_project(project_name, "StorageBucket", bucket_name, client)

    return client.get_bucket_object(project_name, bucket_name, key)
