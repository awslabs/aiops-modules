from typing import Any

from aws_cdk import Aws, CustomResource, Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambdafunction
from constructs import Construct


class GitHubRepositoryCreator(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        github_token_secret_name: str,
        repo_name: str,
        repo_description: str,
        github_owner: str,
        s3_bucket_name: str,
        s3_bucket_object_key: str,
        code_connection_arn: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        github_lambda_func_code = """
import json
import os
import boto3
import urllib.request
import urllib.error
import tempfile
import subprocess
import shutil
import base64
import shlex
import random
import string
import zipfile
import cfnresponse

def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def init_and_push_repo(repo_url, local_dir):

    print(f"Initializing and pushing to repository: {repo_url}")
    print(f"Local directory: {local_dir}")

    # Initialize a new repository
    subprocess.run(['git', 'init'], cwd=local_dir, check=True)

    # Configure Git user (replace with your desired values or use environment variables)
    subprocess.run(['git', 'config', 'user.email', "user@aiops.com"], cwd=local_dir, check=True)
    subprocess.run(['git', 'config', 'user.name', "aiops-user"], cwd=local_dir, check=True)

    # Add all files to the repository
    subprocess.run(['git', 'add', '.'], cwd=local_dir, check=True)

    # Commit the changes
    subprocess.run(['git', 'commit', '-m', "Initial commit with files from S3"], cwd=local_dir, check=True)

    # Configure main branch
    subprocess.run(['git', 'branch', '-M', 'main'], cwd=local_dir, check=True)

    # Add the remote origin
    subprocess.run(['git', 'remote', 'add', 'origin', repo_url], cwd=local_dir, check=True)

    # Push to the remote repository
    subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=local_dir, check=True)

def download_s3_bucket(s3_client, bucket_name, local_dir):
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name):
        for obj in page.get('Contents', []):
            key = obj['Key']
            target = os.path.join(local_dir, key)
            if not os.path.exists(os.path.dirname(target)):
                os.makedirs(os.path.dirname(target))
            s3_client.download_file(bucket_name, key, target)

def download_s3_bucket_v2(bucket_name, download_dir):
    # Download all files from the specified S3 bucket to a local directory.
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)

    for obj in bucket.objects.all():
        path, filename = os.path.split(obj.key)
        local_dir = os.path.join(download_dir, path)
        os.makedirs(local_dir, exist_ok=True)

        file_path = os.path.join(local_dir, filename)
        bucket.download_file(obj.key, file_path)
        print(f"Downloaded {obj.key} to {file_path}")

def download_s3_object_v3(bucket_name, object_key, download_path):
    # Download a specific object (zip file) from the S3 bucket.
    try:
        s3 = boto3.client('s3')
        s3.download_file(bucket_name, object_key, download_path)
        print(f"Downloaded {object_key} from {bucket_name} to {download_path}")
    except Exception as e:
        print(f"Error downloading {object_key} from S3: {str(e)}")
        raise e

def extract_zip_file(zip_file_path, extract_dir):
    # Extract the contents of a zip file.
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"Extracted {zip_file_path} to {extract_dir}")
    except Exception as e:
        print(f"Error extracting zip file: {str(e)}")
        raise e

def is_organization(github_owner, headers):
    # Check if github_owner is a GitHub organization (not a personal user account).
    # Returns True if it's an organization, False otherwise.
    print(f"Checking if '{github_owner}' is a GitHub organization...")
    req = urllib.request.Request(f'https://api.github.com/orgs/{github_owner}', headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                print(f"'{github_owner}' is a GitHub organization")
                return True
            else:
                print(f"Unexpected status code {response.getcode()} when checking organization")
                return False
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"'{github_owner}' is not an organization (404 - not found)")
            return False
        else:
            print(f"Error checking if '{github_owner}' is an organization: {e.code} - {e.reason}")
            # For other errors (403, etc.), assume it might be an org and let the create call fail with proper error
            return True

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    secret_name = os.environ['GITHUB_TOKEN_SECRET_NAME']
    repo_name = event['ResourceProperties']['RepoName']
    repo_description = event['ResourceProperties']['RepoDescription']
    github_owner = event['ResourceProperties']['GitHubOwner']
    s3_bucket_name = event['ResourceProperties']['S3BucketName']
    s3_bucket_object_key = event['ResourceProperties']['S3BucketObjectKey']
    code_connection_arn = event['ResourceProperties']['CodeConnectionArn']

    # Get GitHub token from Secrets Manager
    secrets_manager = boto3.client('secretsmanager')
    secret = secrets_manager.get_secret_value(SecretId=secret_name)
    github_token = json.loads(secret['SecretString'])['github_token']

    if event['RequestType'] == 'Create':
        # Create GitHub repository
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        data = json.dumps({
            'name': repo_name,
            'description': repo_description,
            'private': True
        }).encode('utf-8')

        # Determine if github_owner is an organization or personal user account
        if is_organization(github_owner, headers):
            # Use organization endpoint
            api_url = f'https://api.github.com/orgs/{github_owner}/repos'
            print(f"Creating repository under organization '{github_owner}' using {api_url}")
        else:
            # Use user endpoint
            api_url = 'https://api.github.com/user/repos'
            print(f"Creating repository under user account using {api_url}")

        req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req) as response:
                repo_data = json.loads(response.read().decode())
                repo_url = repo_data['clone_url']
                print(f"Repository created successfully: {repo_url}")
        except urllib.error.HTTPError as e:
            print(f"HTTP Error creating repository: {e.code} - {e.reason}")
            error_body = e.read().decode()
            print(f"Error details: {error_body}")
            raise

        # Download entire S3 bucket
        s3 = boto3.client('s3')
        with tempfile.TemporaryDirectory() as tmp_dir:

            # Generate a unique directory name
            # random_suffix = generate_random_string()
            # tmp_dir = f"/tmp/repo_{random_suffix}"
            # zip_file_path = f"{tmp_dir}/deploy.zip"
            zip_file_path = os.path.join(tmp_dir, 'code.zip')

            # download_s3_bucket_v2(s3_bucket_name, tmp_dir)
            download_s3_object_v3(s3_bucket_name, s3_bucket_object_key, zip_file_path)
            extract_zip_file(zip_file_path, tmp_dir)

            # Update repo_url with github_owner and github_token
            repo_url = f"https://{github_owner}:{github_token}@github.com/{github_owner}/{repo_name}.git"
            # Initialize Git repo and push
            init_and_push_repo(repo_url, tmp_dir)

            print(f"Repository initialized and pushed successfully")

            # Retrieve the list of existing source credentials from codebuild
            codebuild = boto3.client('codebuild')
            response = codebuild.list_source_credentials()

            existing_source_credentials = response['sourceCredentialsInfos']
            # Check if a source credential for GitHub already exists
            github_source_credential = any(cred['serverType'] == 'GITHUB' for cred in existing_source_credentials)
            print(f"GitHub source credential already exists: {github_source_credential}")

            if github_source_credential is False:
                codebuild.import_source_credentials(
                    token=code_connection_arn,
                    serverType="GITHUB",
                    authType="CODECONNECTIONS"
                )
                print(f"GitHub source credential imported successfully")
            else:
                print(f"GitHub source credential already exists")

            response_data = {
                'RepoName': repo_name,
                'RepoUrl': f"https://github.com/{github_owner}/{repo_name}.git"
            }

            # Send a successful response back to CloudFormation
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)


    elif event['RequestType'] == 'Delete':
        # Delete GitHub repository using GitHub API
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        req = urllib.request.Request(f"https://api.github.com/repos/{github_owner}/{repo_name}",
                    headers=headers,
                    method='DELETE')
        try:
            with urllib.request.urlopen(req) as response:
                response_code = response.getcode()
                if response_code == 204:
                    print(f"Repository {repo_name} deleted successfully")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Repository doesn't exist - already deleted
                print(f"Repository {repo_name} not found - treating as successful deletion")
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
                return
            elif e.code == 403:
                # Forbidden - try to archive instead
                print(f"HTTP Error deleting repository: 403 - Forbidden")
                print(f"Attempting to archive repository instead...")
                try:
                    archive_data = json.dumps({'archived': True}).encode('utf-8')
                    archive_req = urllib.request.Request(
                        f"https://api.github.com/repos/{github_owner}/{repo_name}",
                        data=archive_data,
                        headers=headers,
                        method='PATCH'
                    )
                    with urllib.request.urlopen(archive_req) as archive_response:
                        if archive_response.getcode() == 200:
                            print(f"Repository {repo_name} archived successfully")
                            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
                            return
                except Exception as archive_error:
                    print(f"Failed to archive repository: {str(archive_error)}")
                    cfnresponse.send(event, context, cfnresponse.FAILED, {})
                    return
            else:
                # Other errors - fail
                print(f"HTTP Error deleting repository: {e.code} - {e.reason}")
                print(e.read().decode())
                cfnresponse.send(event, context, cfnresponse.FAILED, {})
                return

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    elif event['RequestType'] == 'Update':
        old_props = event['OldResourceProperties']
        new_props = event['ResourceProperties']
        physical_resource_id = event['PhysicalResourceId']

        # Check if repository_owner changed - create new repo under new owner
        if old_props['GitHubOwner'] != new_props['GitHubOwner']:
            print(f"GitHubOwner changed from {old_props['GitHubOwner']} to {new_props['GitHubOwner']}")
            print(
                f"Creating new repo under {new_props['GitHubOwner']} with seed code, "
                f"keeping old repo under {old_props['GitHubOwner']}"
            )

            new_github_owner = new_props['GitHubOwner']
            new_repo_name = new_props['RepoName']

            try:
                # Create new repository under new owner
                headers = {
                    'Authorization': f'token {github_token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json'
                }
                data = json.dumps({
                    'name': new_repo_name,
                    'description': repo_description,
                    'private': True
                }).encode('utf-8')

                if is_organization(new_github_owner, headers):
                    api_url = f'https://api.github.com/orgs/{new_github_owner}/repos'
                else:
                    api_url = 'https://api.github.com/user/repos'

                req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')
                with urllib.request.urlopen(req) as response:
                    repo_data = json.loads(response.read().decode())
                    print(f"Created new repository: {repo_data['clone_url']}")

                # Push seed code to new repo
                s3 = boto3.client('s3')
                with tempfile.TemporaryDirectory() as tmp_dir:
                    zip_file_path = os.path.join(tmp_dir, 'code.zip')
                    download_s3_object_v3(s3_bucket_name, s3_bucket_object_key, zip_file_path)
                    extract_zip_file(zip_file_path, tmp_dir)

                    new_repo_url = f"https://{new_github_owner}:{github_token}@github.com/{new_github_owner}/{new_repo_name}.git"
                    init_and_push_repo(new_repo_url, tmp_dir)
                    print(f"Pushed seed code to new repository under {new_github_owner}")

            except Exception as e:
                print(f"Error creating new repo under new owner: {e}")
                cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_resource_id)
                return

        # Check if CodeConnectionArn changed - update CodeBuild credentials
        if old_props.get('CodeConnectionArn') != new_props.get('CodeConnectionArn'):
            print(f"CodeConnectionArn changed, updating CodeBuild source credentials")
            codebuild = boto3.client('codebuild')
            try:
                # List and delete old GitHub credentials
                response = codebuild.list_source_credentials()
                for cred in response['sourceCredentialsInfos']:
                    if cred['serverType'] == 'GITHUB' and cred['authType'] == 'CODECONNECTIONS':
                        codebuild.delete_source_credentials(arn=cred['arn'])
                        print(f"Deleted old source credential: {cred['arn']}")

                # Import new credentials
                codebuild.import_source_credentials(
                    token=new_props['CodeConnectionArn'],
                    serverType="GITHUB",
                    authType="CODECONNECTIONS"
                )
                print(f"Imported new CodeConnection credentials")
            except Exception as e:
                print(f"Error updating CodeBuild credentials: {e}")
                cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_resource_id)
                return

        # Check if S3 seed code changed - create branch and PR
        if (old_props.get('S3BucketObjectKey') != new_props.get('S3BucketObjectKey')):
            print(f"S3 seed code changed, creating branch and PR")
            import time
            branch_name = f"update-seedcode-{int(time.time())}"

            try:
                s3 = boto3.client('s3')
                with tempfile.TemporaryDirectory() as tmp_dir:
                    zip_file_path = os.path.join(tmp_dir, 'code.zip')
                    download_s3_object_v3(s3_bucket_name, s3_bucket_object_key, zip_file_path)
                    extract_zip_file(zip_file_path, tmp_dir)

                    repo_url = f"https://{github_owner}:{github_token}@github.com/{github_owner}/{repo_name}.git"

                    # Clone existing repo
                    subprocess.run(['git', 'clone', repo_url, 'repo'], cwd=tmp_dir, check=True)
                    repo_dir = os.path.join(tmp_dir, 'repo')

                    # Configure git
                    subprocess.run(['git', 'config', 'user.email', "user@aiops.com"], cwd=repo_dir, check=True)
                    subprocess.run(['git', 'config', 'user.name', "aiops-user"], cwd=repo_dir, check=True)

                    # Create new branch
                    subprocess.run(['git', 'checkout', '-b', branch_name], cwd=repo_dir, check=True)

                    # Copy new code (excluding .git and repo dir)
                    for item in os.listdir(tmp_dir):
                        if item not in ['code.zip', 'repo']:
                            src = os.path.join(tmp_dir, item)
                            dst = os.path.join(repo_dir, item)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src, dst)

                    # Commit and push
                    subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
                    subprocess.run(['git', 'commit', '-m', "Update seed code from S3"], cwd=repo_dir, check=True)
                    subprocess.run(['git', 'push', '-u', 'origin', branch_name], cwd=repo_dir, check=True)

                    # Create PR via GitHub API
                    headers = {
                        'Authorization': f'token {github_token}',
                        'Accept': 'application/vnd.github.v3+json',
                        'Content-Type': 'application/json'
                    }
                    pr_data = json.dumps({
                        'title': 'Update seed code',
                        'body': 'Automated update of seed code from S3',
                        'head': branch_name,
                        'base': 'main'
                    }).encode('utf-8')

                    pr_url = f'https://api.github.com/repos/{github_owner}/{repo_name}/pulls'
                    req = urllib.request.Request(pr_url, data=pr_data, headers=headers, method='POST')
                    with urllib.request.urlopen(req) as response:
                        pr_result = json.loads(response.read().decode())
                        print(f"Created PR: {pr_result['html_url']}")

            except Exception as e:
                print(f"Error creating branch and PR: {e}")
                cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_resource_id)
                return

        # No changes or successful update
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, physical_resource_id)
"""
        # Lambda function to create GitHub repository
        github_repo_creator_lambda = lambdafunction.Function(
            self,
            "GitHubRepoCreatorLambda",
            runtime=lambdafunction.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            code=lambdafunction.Code.from_inline(github_lambda_func_code),
            memory_size=512,
            timeout=Duration.seconds(300),
            environment={
                "GITHUB_TOKEN_SECRET_NAME": github_token_secret_name,
            },
            layers=[
                lambdafunction.LayerVersion.from_layer_version_arn(
                    self, "git-lambda2", "arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8"
                )  # TODO: Check how can be add layer with git instead of adding vailable third party layer
            ],
        )

        # Grant the Lambda function permission to read the GitHub token from Secrets Manager
        if github_repo_creator_lambda.role:
            github_repo_creator_lambda.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess")
            )
        github_repo_creator_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[f"arn:aws:secretsmanager:{Aws.REGION}:{Aws.ACCOUNT_ID}:secret:{github_token_secret_name}*"],
            )
        )
        # Add another policy statement to list source credentials for CodeBuild
        github_repo_creator_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "codebuild:ListSourceCredentials",
                    "codebuild:ImportSourceCredentials",
                    "codebuild:DeleteSourceCredentials",
                ],
                resources=["*"],
            )
        )
        # Custom resource to create GitHub repository
        github_repo_resource = CustomResource(
            self,
            "GitHubRepoResource",
            service_token=github_repo_creator_lambda.function_arn,
            properties={
                "RepoName": repo_name,
                "RepoDescription": repo_description,
                "GitHubOwner": github_owner,
                "S3BucketName": s3_bucket_name,
                "S3BucketObjectKey": s3_bucket_object_key,
                "CodeConnectionArn": code_connection_arn,
            },
        )
        self.cutom_resource = github_repo_resource
