# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, List

import aws_cdk.aws_s3_assets as s3_assets
import aws_cdk.aws_servicecatalog as servicecatalog
from aws_cdk import Aws, CfnParameter, CustomResource, Duration, Tags, CfnOutput, SecretValue

from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambdafunction
from aws_cdk import aws_s3 as s3
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
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        
        github_lambda_func_code="""
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

    if event['RequestType'] == 'Create':
        secret_name = os.environ['GITHUB_TOKEN_SECRET_NAME']
        repo_name = event['ResourceProperties']['RepoName']
        repo_description = event['ResourceProperties']['RepoDescription']
        github_owner = event['ResourceProperties']['GitHubOwner']
        s3_bucket_name = event['ResourceProperties']['S3BucketName']
        s3_bucket_object_key = event['ResourceProperties']['S3BucketObjectKey']

        print(f"Creating GitHub repository '{repo_name}'")
        print(f"Description: {repo_description}")
        print(f"Owner: {github_owner}")
        print(f"S3 bucket: {s3_bucket_name}")

        # Get GitHub token from Secrets Manager
        secrets_manager = boto3.client('secretsmanager')
        secret = secrets_manager.get_secret_value(SecretId=secret_name)
        github_token = json.loads(secret['SecretString'])['github_token']

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

        response_data = {
            'RepoName': repo_name,
            'RepoUrl': f"https://github.com/{github_owner}/{repo_name}.git"
        }

        # Send a successful response back to CloudFormation
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)


    elif event['RequestType'] == 'Update':
        # Handle updates if needed
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

    elif event['RequestType'] == 'Delete':
        # Optionally, delete the GitHub repository
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
            timeout=Duration.seconds(300),
            environment={
                "GITHUB_TOKEN_SECRET_NAME": github_token_secret_name,
            },
            layers=[
                lambdafunction.LayerVersion.from_layer_version_arn(self, "git-lambda2", "arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8") #TODO: This needs to be changed
            ],
        )

        # Grant the Lambda function permission to read the GitHub token from Secrets Manager and AmazonS3ReadOnlyAccess
        github_repo_creator_lambda.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"))
        github_repo_creator_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue", ],
                resources=[f"arn:aws:secretsmanager:{Aws.REGION}:{Aws.ACCOUNT_ID}:secret:{github_token_secret_name}*"],
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
            },
        )

        self.repo_name = github_repo_resource.get_att_string("RepoName")
        self.repo_url = github_repo_resource.get_att_string("RepoUrl")

        # CfnOutput(self, "GitHubRepoName", value=self.repo_name)
        # CfnOutput(self, "GitHubRepoUrl", value=self.repo_url)

class Product(servicecatalog.ProductStack):
    DESCRIPTION: str = (
        "Creates a self-mutating CodePipeline that deploys a model endpoint to dev, pre-prod, and prod environments."
    )
    TEMPLATE_NAME: str = "Deployment pipeline that deploys model endpoints to dev, pre-prod, and prod"

    def __init__(
        self,
        scope: Construct,
        id: str,
        deploy_app_asset: s3_assets.Asset,
        dev_vpc_id: str,
        dev_subnet_ids: List[str],
        dev_security_group_ids: List[str],
        pre_prod_account_id: str,
        pre_prod_region: str,
        pre_prod_vpc_id: str,
        pre_prod_subnet_ids: List[str],
        pre_prod_security_group_ids: List[str],
        prod_account_id: str,
        prod_region: str,
        prod_vpc_id: str,
        prod_subnet_ids: List[str],
        prod_security_group_ids: List[str],
        sagemaker_domain_id: str,
        sagemaker_domain_arn: str,
        repository_type: str,
        repository_access_token: str,
        aws_codeconnection_arn: str,
        repository_owner: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id)

        sagemaker_project_name = CfnParameter(
            self,
            "SageMakerProjectName",
            type="String",
            description="Name of the project.",
        ).value_as_string

        sagemaker_project_id = CfnParameter(
            self,
            "SageMakerProjectId",
            type="String",
            description="Service generated Id of the project.",
        ).value_as_string

        model_package_group_name = CfnParameter(
            self,
            "ModelPackageGroupName",
            type="String",
            description="Name of the model package group.",
        ).value_as_string

        model_bucket_name = CfnParameter(
            self,
            "ModelBucketName",
            type="String",
            description="Name of the bucket that stores model artifacts.",
        ).value_as_string

        pre_prod_account_id = CfnParameter(
            self,
            "PreProdAccountId",
            type="String",
            description="Pre-prod AWS account id.",
            default=pre_prod_account_id,
        ).value_as_string

        pre_prod_region = CfnParameter(
            self,
            "PreProdRegion",
            type="String",
            description="Pre-prod region name.",
            default=pre_prod_region,
        ).value_as_string

        prod_account_id = CfnParameter(
            self,
            "ProdAccountId",
            type="String",
            description="Prod AWS account id.",
            default=prod_account_id,
        ).value_as_string

        prod_region = CfnParameter(
            self,
            "ProdRegion",
            type="String",
            description="Prod region name.",
            default=prod_region,
        ).value_as_string

        enable_network_isolation = CfnParameter(
            self,
            "EnableNetworkIsolation",
            type="String",
            description="Enable network isolation",
            allowed_values=["true", "false"],
            default="false",
        ).value_as_string

        Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)
        if sagemaker_domain_id:
            Tags.of(self).add("sagemaker:domain-id", sagemaker_domain_id)
        if sagemaker_domain_arn:
            Tags.of(self).add("sagemaker:domain-arn", sagemaker_domain_arn)

        dev_account_id: str = Aws.ACCOUNT_ID
        dev_region: str = Aws.REGION

        model_package_arn = (
            f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/"
            f"{model_package_group_name}/*"
        )
        model_package_group_arn = (
            f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package-group/"
            f"{model_package_group_name}"
        )

        # Create GitHub repository
        github_repo = GitHubRepositoryCreator(
            self,
            "DeployAppGitHubRepo",
            github_token_secret_name=repository_access_token,
            repo_name=f"{sagemaker_project_name}-deploy",
            repo_description=f"Deployment repository for SageMaker project {sagemaker_project_name}",
            github_owner=repository_owner,
            s3_bucket_name=deploy_app_asset.s3_bucket_name,
            s3_bucket_object_key=deploy_app_asset.s3_object_key
        )

        # Import model bucket
        model_bucket = s3.Bucket.from_bucket_name(self, "ModelBucket", bucket_name=model_bucket_name)

        code_pipeline_deploy_project_name = "CodePipelineDeployProject"

        # Remove GitHub Default source credential
        # codebuild.GitHubSourceCredentials.remove(self, "DefaultGitHubSourceCredential")

        # Set up GitHub credentials
        # github_credentials = codebuild.GitHubSourceCredentials(
        #     self, "CodeBuildGitHubCreds",
        #     access_token=SecretValue.secrets_manager("github_access_secret")
        # )

        # # Import the source credentials
        # codebuild.CfnSourceCredential(
        #     self, 
        #     "CodeBuildSourceCredential",
        #     auth_type="PERSONAL_ACCESS_TOKEN",
        #     server_type="GITHUB",
        #     token=SecretValue.secrets_manager("github_access_secret", json_field="Token").to_string()
        # )

        # TODO: Need to implement resing same GitHub credentials instead of creating one. 
        # Build fails if credentials exists it tries to create new one. We might need to have Custom Resource 
        # that checks if Source Credential exists for GitHub and create only if it doesn't exists
        
        # Import the source credentials
        codebuild.CfnSourceCredential(
            self, 
            "CodeBuildSourceCredential",
            auth_type="CODECONNECTIONS",
            server_type="GITHUB",
            token=aws_codeconnection_arn
        )

        project = codebuild.Project(
            self,
            code_pipeline_deploy_project_name,
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                "npm install -g aws-cdk",
                                "python -m pip install -r requirements.txt",
                                'cdk deploy --require-approval never --app "python app.py" ',
                            ]
                        }
                    },
                }
            ),
            source=codebuild.Source.git_hub(
                owner=repository_owner,
                repo=f"{sagemaker_project_name}-deploy"
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables={
                    "CODE_CONNECTION_ARN": codebuild.BuildEnvironmentVariable(value=aws_codeconnection_arn),
                    "SOURCE_REPOSITORY": codebuild.BuildEnvironmentVariable(value=f"{repository_owner}/{sagemaker_project_name}-deploy"),
                    "MODEL_PACKAGE_GROUP_NAME": codebuild.BuildEnvironmentVariable(value=model_package_group_name),
                    "MODEL_BUCKET_ARN": codebuild.BuildEnvironmentVariable(value=model_bucket.bucket_arn),
                    "PROJECT_ID": codebuild.BuildEnvironmentVariable(value=sagemaker_project_id),
                    "PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=sagemaker_project_name),
                    "DOMAIN_ID": codebuild.BuildEnvironmentVariable(value=sagemaker_domain_id),
                    "DOMAIN_ARN": codebuild.BuildEnvironmentVariable(value=sagemaker_domain_arn),
                    "DEV_VPC_ID": codebuild.BuildEnvironmentVariable(value=dev_vpc_id),
                    "DEV_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=dev_account_id),
                    "DEV_REGION": codebuild.BuildEnvironmentVariable(value=dev_region),
                    "DEV_SUBNET_IDS": codebuild.BuildEnvironmentVariable(value=json.dumps(dev_subnet_ids)),
                    "DEV_SECURITY_GROUP_IDS": codebuild.BuildEnvironmentVariable(
                        value=json.dumps(dev_security_group_ids)
                    ),
                    "PRE_PROD_VPC_ID": codebuild.BuildEnvironmentVariable(value=pre_prod_vpc_id),
                    "PRE_PROD_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=pre_prod_account_id),
                    "PRE_PROD_REGION": codebuild.BuildEnvironmentVariable(value=pre_prod_region),
                    "PRE_PROD_SUBNET_IDS": codebuild.BuildEnvironmentVariable(value=json.dumps(pre_prod_subnet_ids)),
                    "PRE_PROD_SECURITY_GROUP_IDS": codebuild.BuildEnvironmentVariable(
                        value=json.dumps(pre_prod_security_group_ids)
                    ),
                    "PROD_VPC_ID": codebuild.BuildEnvironmentVariable(value=prod_vpc_id),
                    "PROD_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=prod_account_id),
                    "PROD_REGION": codebuild.BuildEnvironmentVariable(value=prod_region),
                    "PROD_SUBNET_IDS": codebuild.BuildEnvironmentVariable(value=json.dumps(prod_subnet_ids)),
                    "PROD_SECURITY_GROUP_IDS": codebuild.BuildEnvironmentVariable(
                        value=json.dumps(prod_security_group_ids)
                    ),
                    "ENABLE_NETWORK_ISOLATION": codebuild.BuildEnvironmentVariable(value=enable_network_isolation),
                },
            ),
        )


        # Verify that the project.role is not None
        if project.role is None:
            raise ValueError("project.role is None, unable to attach inline policy")
        else:
            project.role.attach_inline_policy(
                iam.Policy(
                    self,
                    "Policy",
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "codebuild:ImportSourceCredentials",
                                "codebuild:DeleteSourceCredentials",
                                "codebuild:ListSourceCredentials"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "codeconnections:UseConnection", 
                                "codeconnections:PassConnection",
                                "codeconnections:GetConnection",
                                "codeconnections:GetConnectionToken"
                            ],
                            resources=[
                                f"arn:aws:codeconnections:*:{Aws.ACCOUNT_ID}:connection/*"
                            ],
                        ),
                        iam.PolicyStatement(
                            sid="ModelPackageGroup",
                            actions=[
                                "sagemaker:DescribeModelPackageGroup",
                            ],
                            resources=[model_package_group_arn],
                        ),
                        iam.PolicyStatement(
                            sid="ModelPackage",
                            actions=[
                                "sagemaker:DescribeModelPackage",
                                "sagemaker:ListModelPackages",
                                "sagemaker:UpdateModelPackage",
                                "sagemaker:CreateModel",
                            ],
                            resources=[model_package_arn],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "sts:AssumeRole",
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[
                                f"arn:{Aws.PARTITION}:iam::{dev_account_id}:role/cdk*",
                                f"arn:{Aws.PARTITION}:iam::{pre_prod_account_id}:role/cdk*",
                                f"arn:{Aws.PARTITION}:iam::{prod_account_id}:role/cdk*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["ssm:GetParameter"],
                            resources=[
                                f"arn:{Aws.PARTITION}:ssm:{dev_region}:{dev_account_id}:parameter/*",
                                f"arn:{Aws.PARTITION}:ssm:{pre_prod_region}:{pre_prod_account_id}:parameter/*",
                                f"arn:{Aws.PARTITION}:ssm:{prod_region}:{prod_account_id}:parameter/*",
                            ],
                        ),
                    ],
                )
            )
        
        # Create custom resource as lamda function that triggers codebuild project
        custom_resource_lambda_role = iam.Role(
            self,
            "CodeBuildTriggerCustomResourceLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "CodeBuildTriggerCustomResourceLambdaPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "codebuild:ImportSourceCredentials",
                                "codebuild:StartBuild",
                                "codebuild:BatchGetBuilds",
                                "codebuild:DescribeTestCases",
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=[project.project_arn],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            effect=iam.Effect.ALLOW,
                            resources=["*"],
                        ),
                    ]
                )
            },
        )
        lambda_func_code = """
import boto3
import cfnresponse

def handler(event, context):
    print(f"Event: {event}")

    # Get the CodeBuild project name from the event parameters
    project_name = event["ResourceProperties"]["CodeBuildProjectName"]

    try:
        # Create a CodeBuild client
        codebuild = boto3.client("codebuild")

        # Start the CodeBuild project
        response = codebuild.start_build(projectName=project_name)
        print(f"CodeBuild project started: {response}")

        # Send a successful response back to CloudFormation
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

    except Exception as e:
        print(f"Error: {e}")
        # Send a failed response back to CloudFormation
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

"""
        custom_resource_lambda = lambdafunction.Function(
            self,
            "CustomResourceLambda",
            runtime=lambdafunction.Runtime.PYTHON_3_9,
            handler="index.handler",
            role=custom_resource_lambda_role,
            code=lambdafunction.Code.from_inline(lambda_func_code),
            environment={
                "CODE_BUILD_PROJECT_NAME": project.project_name,
            },
            timeout=Duration.minutes(5),
        )

        custom_resource = CustomResource(
            self,
            "Custom::CodeBuildTriggerResourceType",
            service_token=custom_resource_lambda.function_arn,
            properties={
                "CodeBuildProjectName": project.project_name,
            },
        )
        custom_resource.node.add_dependency(project)
