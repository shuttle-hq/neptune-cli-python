Neptune is a cloud deployment platform that makes it easy to deploy and manage applications.

## Workflow

1. **Create neptune.json**: Use `get_project_schema` to get the JSON schema, then create a valid `neptune.json` configuration file based on the project's needs.

2. **Add resources**: Use `add_new_resource` to get information about specific resource types (StorageBucket, Secret) before adding them to the configuration.

3. **Create Dockerfile**: Ensure a Dockerfile exists in the project directory. Neptune builds and runs your application as a container.

4. **Provision**: Use `provision_resources` to create the cloud infrastructure defined in `neptune.json`.

5. **Configure resources**:
   - For **Secrets**: Use `set_secret_value` to securely set their values.
   - For **Storage Buckets**: Note the `aws_id` returned - this is the bucket ID needed in your code. See "Storage Bucket Workflow" below.

6. **Deploy**: Use `deploy_project` to build and deploy the application.

7. **Monitor**: Use `get_deployment_status`, `wait_for_deployment`, and `get_logs` to monitor the deployment.

## Storage Bucket Workflow

When using Storage Buckets, follow this workflow to properly connect your application:

1. **Add the bucket to neptune.json**:
   ```json
   {
     "kind": "StorageBucket",
     "name": "uploads"
   }
   ```

2. **Provision resources**: Run `provision_resources`. The response includes the `aws_id` for each bucket - this is the actual S3 bucket name you need.

3. **Use the bucket ID in your code**: Hardcode the `aws_id` value returned from provisioning:
   ```python
   import os
   import boto3

   # Use the aws_id from provision_resources response
   BUCKET_ID = 'neptune-abc123-uploads'  # Replace with your actual aws_id

   s3 = boto3.client(
       's3',
       aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
       aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
       region_name='eu-west-2',
   )

   s3.upload_file('file.jpg', BUCKET_ID, 'path/file.jpg')
   ```

   Note: AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) are automatically injected into your deployed application.

**Tools for bucket management**:
- `get_bucket_connection_info`: Get the bucket ID and usage examples
- `list_bucket_files`: List files in a bucket
- `get_bucket_object`: Retrieve a file from a bucket

## Troubleshooting Deployments

After a deployment, ALWAYS check the service status. If the service is not "Running":

1. **Check status**: Use `get_deployment_status` to see the current state
2. **Get logs**: If status shows "Error", "Stopped", "Pending", or "Starting" for too long, use `get_logs` immediately
3. **Analyze logs**: Look for common issues:
    - Application crash on startup (missing dependencies, config errors)
    - Port binding issues (app must listen on port 8080 by default)
    - Missing environment variables or secrets
4. **Fix and redeploy**: After identifying the issue, fix the code/config and run `deploy_project` again

Common service issues:

-   **Stopped/Error**: Application crashed - check logs for stack traces or error messages
-   **Pending too long**: Container may be failing health checks - ensure app responds on port 8080
-   **Starting too long**: Application may be hanging during startup - check for blocking operations

## Key Concepts

-   **neptune.json**: The configuration file that defines the project name, workload type, and required resources.
-   **Resources**: Infrastructure components like storage buckets and secrets that the application needs.
-   **Dockerfile**: Required for deployment - Neptune builds and runs your application as a container.

## Important Notes

-   Always use `get_project_schema` before creating or modifying `neptune.json` to ensure the configuration is valid.
-   Always use `add_new_resource` before adding resources to understand their properties and requirements.
-   Deployments are ECS tasks on Fargate - container data is not persistent. Use provisioned resources for persistent storage.
-   **Always verify deployment health**: After `deploy_project`, check status and fetch logs if the service isn't running properly.
