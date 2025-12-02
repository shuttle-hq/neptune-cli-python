import os
import time
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from loguru import logger as log

from neptune_cli.client import Client

from neptune_api.models import PutProjectRequest


def _load_instructions() -> str:
    """Load MCP instructions from the instructions file."""
    instructions_path = Path(__file__).parent / "mcp_instructions.md"
    return instructions_path.read_text()


mcp = FastMCP("Neptune (neptune.dev) MCP", instructions=_load_instructions())


def validate_neptune_json(neptune_json_path: str) -> dict[str, Any] | None:
    """Validate that neptune.json exists at the given path.

    Returns an error dict if the file doesn't exist, None otherwise.
    """
    if not os.path.exists(neptune_json_path):
        log.error(f"neptune.json not found at {neptune_json_path}")
        return {
            "status": "error",
            "message": f"neptune.json not found at {neptune_json_path}",
            "next_step": f"make sure a 'neptune.json' file exists at {neptune_json_path}",
        }
    return None


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
    client = Client()

    try:
        schema = client.get_project_schema()
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
    if kind == "Database":
        return {
            "description": "Managed database instances for your applications.",
            "neptune_json_configuration": """
To add a database to a project, add the following to 'resources' in 'neptune.json':
```json
{
    "kind": "Database",
    "name": "<database_name>"
}
```
""",
            "example_code_usage": """
See resource description returned from `get_deployment_status` after provisioning the database.
""",
        }
    elif kind == "StorageBucket":
        return {
            "description": "Backend is a plain AWS S3 bucket.",
            "neptune_json_configuration": """
To add a bucket to a project, add the following to 'resources' in 'neptune.json':
```json
{
    "kind": "StorageBucket",
    "name": "<bucket_name>"
}

A full working example:

```json
{
  "kind": "Service",
  "name": "<project_name>",
  "resources": [
    {
      "kind": "StorageBucket",
      "name": "<bucket_name>"
    }
  ]
}
```

When done with the change, provision the bucket with 'provision_resources'.
""",
            "example_code_usage": """
```python
import boto3
client = boto3.client("s3")
client.put_object(Bucket="<aws_id>", Key="path/to/object", Body=b"data")
```
""",
        }
    elif kind == "Secret":
        return {
            "description": "Managed secret storage for your applications.",
            "neptune_json_configuration": """
To add a secret to a project, add the following to 'resources' in 'neptune.json':
```json
{
    "kind": "Secret",
    "name": "<secret_name>"
}
```
""",
            "example_code_usage": """
```python
import boto3
client = boto3.client("secretsmanager")
response = client.get_secret_value(SecretId="<aws_id>")
secret = response['SecretString']
```
""",
        }
    else:
        return {
            "error": "Unknown resource kind",
            "message": f"The resource kind '{kind}' is not recognized. Valid kind are 'StorageBucket' and 'Database'.",
        }


@mcp.tool("provision_resources")
def provision_resources(neptune_json_path: str) -> dict[str, Any]:
    """Provision necessary cloud resources for the current project as per its configuration

    If the working directory does not contain a 'neptune.json' file, an error message is returned.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    project_request = PutProjectRequest.model_validate_json(project_data)

    if client.get_project(project_request.name) is None:
        log.info(f"Creating project '{project_request.name}'...")
        client.create_project(project_request)
    else:
        log.info(f"Updating project '{project_request.name}'...")
        client.update_project(project_request)

    # while loop to retrieve project status, wait until ready
    project = client.get_project(project_request.name)
    while project.provisioning_state != "Ready":
        log.info(
            f"Project '{project_request.name}' status: {project.provisioning_state}. Waiting for resources to be provisioned..."
        )
        time.sleep(2)
        project = client.get_project(project_request.name)

    # go over all resources, wait until all are provisioned
    all_provisioned = False
    while not all_provisioned:
        all_provisioned = True
        for resource in project.resources:
            if resource.status == "Pending":
                all_provisioned = False
                log.info(f"Resource '{resource.name}' ({resource.kind}) status: {resource.status}. Waiting...")
        if not all_provisioned:
            time.sleep(2)
            project = client.get_project(project_request.name)

    log.info(f"Project '{project_request.name}' resources provisioned successfully")
    return {
        "infrastructure_status": "ready",
        "message": "all the resources required by the project have been provisioned, and it is ready for deployment",
        "next_step": "deploy the project using the 'deploy_project' command; note how each resource should be used by inspecting their descriptions in this response",
        "infrastructure_resources": [resource.model_dump() for resource in project.resources],
    }


@mcp.tool("deploy_project")
def deploy_project(neptune_json_path: str) -> dict[str, Any]:
    """Deploy the current project.

    This only works after the project has been provisioned using 'provision_resources'.

    UNDER THE HOOD: deployments are ECS tasks running on Fargate, with images stored in ECR. In particular, this tool builds an image using the Dockerfile in the current directory.

    Note: running tasks are *not* persistent; if the task stops or is redeployed, all data stored in the container is lost. Use provisioned resources (databases, storage buckets, etc.) for persistent data storage.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    project_dir = os.path.dirname(os.path.abspath(neptune_json_path))

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)

    log.info(f"Deploying project '{project_request.name}'...")

    try:
        deployment = client.create_deployment(project_request.name)
    except Exception as e:
        log.error(f"Failed to create deployment for project '{project_request.name}': {e}")
        return {
            "status": "error",
            "message": f"failed to create deployment for project '{project_request.name}': {e}",
            "next_step": "ensure the project is provisioned with 'provision_resources' and try again",
        }

    # Run `docker build -t <image_name> -f Dockerfile . `, hiding the logs of the subprocess
    log.info(f"Building image for revision {deployment.revision}...")
    import subprocess

    if (push_token := deployment.push_token) is not None:
        registry = deployment.image.split("/")[0]
        login_cmd = [
            "docker",
            "login",
            "-u",
            "AWS",
            "--password-stdin",
            registry,
        ]
        login_process = subprocess.Popen(
            login_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            cwd=project_dir,
        )
        login_process.communicate(input=push_token.encode())
        if login_process.returncode != 0:
            log.error("Docker login failed")
            return {
                "status": "error",
                "message": "docker login failed",
                "registry": registry,
                "username": "AWS",
                "password": push_token,
                "next_step": "ensure your Docker setup is correct and try again",
            }

    build_cmd = [
        "docker",
        "build",
        "--platform",
        "linux/amd64",
        "-t",
        deployment.image,
        "-f",
        "Dockerfile",
        ".",
    ]
    subprocess.run(build_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, cwd=project_dir)
    log.info("Image built successfully")

    log.info(f"Pushing image for revision {deployment.revision}...")
    push_cmd = ["docker", "push", deployment.image]
    subprocess.run(push_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, cwd=project_dir)

    # while deployment.status is not "Deployed", poll every 2 seconds
    while deployment.status != "Deployed":
        time.sleep(2)
        deployment = client.get_deployment(project_request.name, revision=deployment.revision)

    log.info(f"Revision {deployment.revision} deployed successfully")

    return {
        "deployment_status": "Deployed",
        "deployment_revision": deployment.revision,
        "next_step": "the deployment was sent to Neptune's backend, and is now propagating. Investigate the deployment status with 'get_deployment_status'",
    }


@mcp.tool("get_deployment_status")
def get_deployment_status(neptune_json_path: str) -> dict[str, Any]:
    """Get the status of the current deployment of a project and its provisioned resources.

    This will tell you about running resources the project is using, as well as the state of the service.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it deployed?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }

    return {
        "infrastructure_provisioning_status": project.provisioning_state,
        "service_running_status": project.running_status.model_dump(),
        "infrastructure_resources": [resource.model_dump() for resource in project.resources],
        "next_steps": "use this information to monitor the deployment status; if there are issues, check the logs and redeploy as necessary",
    }


@mcp.tool("set_secret_value")
async def set_secret_value(ctx: Context, neptune_json_path: str, secret_name: str) -> dict[str, Any]:
    """Set the value of a secret resource for the current project.

    This will elicit a prompt to securely enter the secret value.

    Note the secret must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before setting its value.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it deployed?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you provision resources for it?",
            "next_step": "provision the project using the 'provision_resources' command",
        }

    secret_resource = next(
        (res for res in project.resources if res.kind == "Secret" and res.name == secret_name),
        None,
    )
    if secret_resource is None:
        log.error(f"Secret resource '{secret_name}' not found in project '{project_name}'")
        return {
            "status": "error",
            "message": f"Secret resource '{secret_name}' not found in project '{project_name}'",
            "next_step": "ensure the secret is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }

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
            "message": "Elicitation cancelled, received during requesting secret value input.",
            "next_step": "try running the 'set_secret_value' command again",
        }

    client.set_secret_value(project_name, secret_name, secret_value)

    return {
        "status": "success",
        "message": f"Secret '{secret_name}' set successfully for project '{project_name}'.",
        "next_step": "redeploy the project if necessary to use the updated secret value with 'deploy_project'",
    }


@mcp.tool("get_database_connection_info")
def get_database_connection_info(neptune_json_path: str, database_name: str) -> dict[str, Any]:
    """Get the connection information for a database resource for the current project.

    Note the database must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before retrieving its connection info.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it deployed?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }

    database_resource = next(
        (res for res in project.resources if res.kind == "Database" and res.name == database_name),
        None,
    )
    if database_resource is None:
        log.error(f"Database resource '{database_name}' not found in project '{project_name}'")
        return {
            "status": "error",
            "message": f"Database resource '{database_name}' not found in project '{project_name}'",
            "next_step": "ensure the database is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }

    conn_info = client.get_database_connection_info(project_name, database_name)

    return {
        "database_connection_info": conn_info.model_dump(),
        "next_step": "use this connection information to connect to your database from your application or management tools; remember the token expires after 15 minutes so do not use it for programmatic access - only for local testing.",
    }


@mcp.tool("list_bucket_files")
def list_bucket_files(neptune_json_path: str, bucket_name: str) -> dict[str, Any]:
    """List all files in a storage bucket resource for the current project.

    Note the bucket must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before listing its files.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it deployed?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }

    bucket_resource = next(
        (res for res in project.resources if res.kind == "StorageBucket" and res.name == bucket_name),
        None,
    )
    if bucket_resource is None:
        log.error(f"Storage bucket resource '{bucket_name}' not found in project '{project_name}'")
        return {
            "status": "error",
            "message": f"Storage bucket resource '{bucket_name}' not found in project '{project_name}'",
            "next_step": "ensure the storage bucket is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }

    keys = client.list_bucket_keys(project_name, bucket_name)

    return {
        "bucket_name": bucket_name,
        "files": keys,
        "next_step": "use these file keys to interact with objects in the bucket; retrieve or manage them as needed",
    }


@mcp.tool("get_bucket_object")
def get_bucket_object(neptune_json_path: str, bucket_name: str, key: str) -> dict[str, str] | bytes:
    """Retrieve an object from a storage bucket resource for the current project.

    Note the bucket must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before retrieving its objects.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it deployed?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }

    bucket_resource = next(
        (res for res in project.resources if res.kind == "StorageBucket" and res.name == bucket_name),
        None,
    )
    if bucket_resource is None:
        log.error(f"Storage bucket resource '{bucket_name}' not found in project '{project_name}'")
        return {
            "status": "error",
            "message": f"Storage bucket resource '{bucket_name}' not found in project '{project_name}'",
            "next_step": "ensure the storage bucket is defined in 'neptune.json' and provisioned with 'provision_resources'",
        }

    object_data = client.get_bucket_object(project_name, bucket_name, key)

    return object_data


@mcp.tool("wait_for_deployment")
def wait_for_deployment(neptune_json_path: str) -> dict[str, Any]:
    """Wait for the current project deployment to complete."""
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it deployed?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you deploy it?",
            "next_step": "deploy the project using the 'deploy_project' command",
        }

    while project.running_status.current != "Running":
        if project.running_status.current in ["Stopped", "Error"]:
            log.error(
                f"Project '{project_name}' is in state '{project.running_status.current}'; cannot wait for deployment"
            )
            return {
                "status": "error",
                "message": f"Project '{project_name}' is in state '{project.running_status.current}'; cannot wait for deployment",
                "next_step": "try deploying the project using the 'deploy_project' command",
            }
        log.info(
            f"Project '{project_name}' running status: {project.running_status.current}. Waiting for deployment to complete..."
        )
        time.sleep(2)
        project = client.get_project(project_name)

    return {
        "infrastructure_provisioning_status": project.provisioning_state,
        "service_running_status": project.running_status.model_dump(),
        "infrastructure_resources": [resource.model_dump() for resource in project.resources],
        "next_steps": "use this information to monitor the deployment status; if there are issues, check the logs and redeploy as necessary",
    }


@mcp.tool("get_logs")
def get_logs(neptune_json_path: str) -> dict[str, Any]:
    """Retrieve the logs for the current project deployment."""
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    from neptune_api import PutProjectRequest

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    logs_response = client.get_logs(project_name)

    return {
        "logs": logs_response.logs,
        "next_step": "use these logs to debug your application or monitor its behavior; fix any issues and redeploy as necessary",
    }


if __name__ == "__main__":
    mcp.run()
