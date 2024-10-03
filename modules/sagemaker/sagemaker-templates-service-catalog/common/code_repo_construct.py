from enum import Enum
from typing import Any

from aws_cdk import Aws, CustomResource, Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambdafunction
from constructs import Construct


class RepositoryType(str, Enum):
    GITHUB = "GitHub"
    GITLAB = "GitLab"
    GITHUB_ENTERPRISE = "GitHub Enterprise"
    GITLAB_ENTERPRISE = "GitLab Enterprise"


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

        req = urllib.request.Request('https://api.github.com/user/repos', data=data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req) as response:
                repo_data = json.loads(response.read().decode())
                repo_url = repo_data['clone_url']
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code} - {e.reason}")
            print(e.read().decode())
            raise

        print(f"Repository created: {repo_url}")

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
            print(f"HTTP Error: {e.code} - {e.reason}")
            print(e.read().decode())
            raise

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    else:
        # raise Exception(f"Invalid request type: {event['RequestType']}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
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
                actions=["codebuild:ListSourceCredentials", "codebuild:ImportSourceCredentials"],
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
