import os
import time
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from loguru import logger as log

from neptune_cli.client import Client

from neptune_common import PutProjectRequest


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
    - Valid resource types (StorageBucket, Secret) and their properties
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


@mcp.tool("login")
def login() -> dict[str, Any]:
    """Authenticate with Neptune.

    Opens a browser window for OAuth login. After successful authentication,
    the access token is saved for use with Neptune tools.
    """
    import webbrowser
    from urllib.parse import urlencode
    from neptune_cli.auth import serve_callback_handler
    from neptune_cli.config import SETTINGS

    # Start local server to receive OAuth callback
    port, httpd, thread = serve_callback_handler()

    # Build login URL
    params = urlencode({"redirect_uri": f"http://localhost:{port}/callback"})
    login_url = f"{SETTINGS.api_base_url}/auth/login?{params}"

    # Try to open browser
    browser_opened = webbrowser.open(login_url)

    if not browser_opened:
        return {
            "status": "pending",
            "message": "Could not open browser automatically.",
            "login_url": login_url,
            "next_step": "Please open the URL above in your browser to complete login, then call this tool again.",
        }

    # Wait for callback
    thread.join()

    if httpd.access_token is not None:
        SETTINGS.access_token = httpd.access_token
        SETTINGS.save_to_file()
        return {
            "status": "success",
            "message": "Successfully logged in!",
            "next_step": "You can now use other Neptune tools to deploy and manage your projects.",
        }
    else:
        return {
            "status": "error",
            "message": "Login failed - no access token received.",
            "next_step": "Try running the 'login' tool again.",
        }


@mcp.tool("add_new_resource")
def add_new_resource(kind: str) -> dict[str, Any]:
    """Get information about resource types that can be provisioned on Neptune.

    IMPORTANT: Always use this tool before modifying 'neptune.json'. This is to ensure your modification is correct.

    Valid 'kind' are: "StorageBucket" and "Secret".
    """
    if kind == "StorageBucket":
        return {
            "description": "S3-compatible object storage for files and assets. Under the hood, these are AWS S3 buckets.",
            "auto_injected_credentials": {
                "AWS_ACCESS_KEY_ID": "Access key for S3 API - automatically injected into your deployed application",
                "AWS_SECRET_ACCESS_KEY": "Secret key for S3 API - automatically injected into your deployed application",
            },
            "bucket_id_workflow": """
IMPORTANT: After provisioning, you need the bucket ID (aws_id) to connect to your bucket.

1. Run 'provision_resources' to create the bucket
2. The response will include the 'aws_id' for each StorageBucket resource
3. Hardcode this 'aws_id' in your application code as the Bucket parameter in S3 operations
""",
            "neptune_json_configuration": """
To add a bucket to a project, add the following to 'resources' in 'neptune.json':
```json
{
    "kind": "StorageBucket",
    "name": "<bucket_name>"
}
```

A full working example:
```json
{
  "kind": "Service",
  "name": "<project_name>",
  "resources": [
    {
      "kind": "StorageBucket",
      "name": "uploads"
    }
  ]
}
```

When done with the change, provision the bucket with 'provision_resources'.
Note the 'aws_id' returned and hardcode it in your application code.
""",
            "example_code_usage": """
```python
import os
import boto3

# Hardcode the aws_id from the provision_resources response
BUCKET_ID = 'neptune-abc123-uploads'  # Replace with your actual aws_id

s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name='eu-west-2',
)

# Upload a file
s3.upload_file('photo.jpg', BUCKET_ID, 'images/photo.jpg')

# Download a file
s3.download_file(BUCKET_ID, 'images/photo.jpg', 'photo.jpg')
```
""",
            "next_steps": [
                "1. Add StorageBucket to neptune.json",
                "2. Run 'provision_resources'",
                "3. Note the 'aws_id' returned for the bucket",
                "4. Hardcode the 'aws_id' in your application code",
                "5. Run 'deploy_project'",
            ],
        }
    elif kind == "Secret":
        return {
            "description": "Managed secret storage for your applications. Secrets are securely stored and injected as environment variables into your deployed application.",
            "neptune_json_configuration": """
To add a secret to a project, add the following to 'resources' in 'neptune.json':
```json
{
    "kind": "Secret",
    "name": "<SECRET_NAME>"
}
```

TIP: Use uppercase names with underscores for secrets (e.g., "API_KEY", "DATABASE_URL") 
as they become environment variables in your application.

A full working example:
```json
{
  "kind": "Service",
  "name": "<project_name>",
  "resources": [
    {
      "kind": "Secret",
      "name": "API_KEY"
    }
  ]
}
```

When done with the change, provision the secret with 'provision_resources'.
After provisioning, use 'set_secret_value' to set the secret's value.
""",
            "example_code_usage": """
```python
import os

# Secrets are automatically injected as environment variables
api_key = os.environ['API_KEY']
```
""",
            "next_steps": [
                "1. Add Secret to neptune.json",
                "2. Run 'provision_resources'",
                "3. Use 'set_secret_value' to set the secret's value",
                "4. Access the secret in your code via os.environ['SECRET_NAME']",
                "5. Run 'deploy_project'",
            ],
        }
    else:
        return {
            "error": "Unknown resource kind",
            "message": f"The resource kind '{kind}' is not recognized. Valid kinds are 'StorageBucket' and 'Secret'.",
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

    # Extract bucket IDs for easy reference
    bucket_ids = {}
    for resource in project.resources:
        if resource.kind == "StorageBucket" and resource.aws_id:
            bucket_ids[resource.name] = resource.aws_id

    response = {
        "infrastructure_status": "ready",
        "message": "all the resources required by the project have been provisioned, and it is ready for deployment",
        "infrastructure_resources": [resource.model_dump() for resource in project.resources],
    }

    # Add bucket-specific guidance if buckets were provisioned
    if bucket_ids:
        response["storage_bucket_ids"] = bucket_ids
        response["bucket_usage_instructions"] = (
            "IMPORTANT: Use the 'aws_id' values above as the Bucket parameter in your S3 operations. "
            "Hardcode these bucket IDs in your application code. "
            "AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) are automatically injected into your deployed application."
        )
        response["next_steps"] = [
            "1. Note the 'aws_id' for each StorageBucket above - this is the actual S3 bucket name",
            "2. Hardcode the 'aws_id' in your application code",
            "3. Deploy the project using 'deploy_project'",
        ]
    else:
        response["next_step"] = "deploy the project using the 'deploy_project' command"

    return response


@mcp.tool("delete_project")
def delete_project(neptune_json_path: str) -> dict[str, Any]:
    """Delete a project and all its resources.

    WARNING: This permanently deletes the project and all associated resources
    including storage buckets and secrets. This action cannot be undone.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    # Check if project exists first
    project = client.get_project(project_name)
    if project is None:
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found.",
            "next_step": "Check the project name and try again.",
        }

    try:
        client.delete_project(project_name)
        log.info(f"Project '{project_name}' deleted successfully")
        return {
            "status": "success",
            "message": f"Project '{project_name}' and all its resources have been permanently deleted.",
        }
    except Exception as e:
        log.error(f"Failed to delete project '{project_name}': {e}")
        return {
            "status": "error",
            "message": f"Failed to delete project '{project_name}': {e}",
            "next_step": "Check the error and try again.",
        }


@mcp.tool("deploy_project")
def deploy_project(neptune_json_path: str) -> dict[str, Any]:
    """Deploy the current project.

    This only works after the project has been provisioned using 'provision_resources'.

    UNDER THE HOOD: deployments are ECS tasks running on Fargate, with images stored in ECR. In particular, this tool builds an image using the Dockerfile in the current directory.

    Note: running tasks are *not* persistent; if the task stops or is redeployed, all data stored in the container is lost. Use provisioned resources (storage buckets, etc.) for persistent data storage.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    project_dir = os.path.dirname(os.path.abspath(neptune_json_path))

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

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


@mcp.tool("get_bucket_connection_info")
def get_bucket_connection_info(neptune_json_path: str, bucket_name: str) -> dict[str, Any]:
    """Get the connection information for a storage bucket resource.

    Returns the bucket ID (aws_id) needed to connect to the bucket in your application code.
    AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) are automatically injected
    into your deployed application.

    Note the bucket must already exist in the neptune.json configuration of the project.
    It must also be provisioned using 'provision_resources' before retrieving its connection info.
    """
    client = Client()

    if validation_result := validate_neptune_json(neptune_json_path):
        return validation_result

    with open(neptune_json_path, "r") as f:
        project_data = f.read()

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    project = client.get_project(project_name)
    if project is None:
        log.error(f"Project '{project_name}' not found; was it provisioned?")
        return {
            "status": "error",
            "message": f"Project '{project_name}' not found; did you provision it?",
            "next_step": "provision the project using the 'provision_resources' command",
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

    if bucket_resource.status != "Available":
        return {
            "status": "pending",
            "message": f"Bucket '{bucket_name}' is still being provisioned (status: {bucket_resource.status})",
            "next_step": "wait for provisioning to complete and try again",
        }

    return {
        "status": "success",
        "bucket_name": bucket_name,
        "bucket_id": bucket_resource.aws_id,
        "region": "eu-west-2",
        "auto_injected_credentials": {
            "AWS_ACCESS_KEY_ID": "Automatically injected into your deployed application",
            "AWS_SECRET_ACCESS_KEY": "Automatically injected into your deployed application",
        },
        "usage_example": f"""
import os
import boto3

# Hardcode the bucket ID from this response
BUCKET_ID = '{bucket_resource.aws_id}'

s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name='eu-west-2',
)

# Upload a file
s3.upload_file('local_file.txt', BUCKET_ID, 'remote/path/file.txt')

# Download a file
s3.download_file(BUCKET_ID, 'remote/path/file.txt', 'local_file.txt')
""",
        "next_steps": [
            f"1. Hardcode '{bucket_resource.aws_id}' as the Bucket parameter in your S3 operations",
            "2. Update your application code to use the bucket",
            "3. Deploy with 'deploy_project'",
        ],
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

    project_request = PutProjectRequest.model_validate_json(project_data)
    project_name = project_request.name

    logs_response = client.get_logs(project_name)

    return {
        "logs": logs_response.logs,
        "next_step": "use these logs to debug your application or monitor its behavior; fix any issues and redeploy as necessary",
    }


if __name__ == "__main__":
    mcp.run()
