# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import json
from typing import Any, List, Optional, Tuple, cast

import aws_cdk.aws_s3_assets as s3_assets
import cdk_nag
from aws_cdk import Aws, CustomResource, Duration, Tags
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambdafunction
from aws_cdk import aws_s3 as s3
from aws_cdk.aws_codebuild import ISource
from constructs import Construct

from common.code_repo_construct import GitHubRepositoryCreator
from settings import RepositoryType


class ModelDeployProject(Construct):
    DESCRIPTION: str = (
        "Creates a self-mutating CodePipeline that deploys a model endpoint to dev, pre-prod, and prod environments."
    )
    TEMPLATE_NAME: str = "Deployment pipeline that deploys model endpoints to dev, pre-prod, and prod"

    def codebuild_source_for_github(
        self,
        repository_owner: str,
        sagemaker_project_name: str,
        deploy_app_asset: s3_assets.Asset,
        access_token_secret_name: str,
        aws_codeconnection_arn: str,
    ) -> Tuple[ISource, GitHubRepositoryCreator]:
        # Create GitHub repository
        github_repo = GitHubRepositoryCreator(
            self,
            "DeployAppGitHubRepo",
            github_token_secret_name=access_token_secret_name,
            repo_name=f"{sagemaker_project_name}-deploy",
            repo_description=f"Deployment repository for SageMaker project {sagemaker_project_name}",
            github_owner=repository_owner,
            s3_bucket_name=deploy_app_asset.s3_bucket_name,
            s3_bucket_object_key=deploy_app_asset.s3_object_key,
            code_connection_arn=aws_codeconnection_arn,
        )
        return codebuild.Source.git_hub(
            owner=repository_owner, repo=f"{sagemaker_project_name}-deploy", branch_or_ref="main"
        ), github_repo

    def codebuild_source_for_codecommit(
        self,
        sagemaker_project_name: str,
        deploy_app_asset: s3_assets.Asset,
    ) -> ISource:
        # Create CodeCommit repo from seed bucket/key
        repository = codecommit.Repository(
            self,
            "Deploy App Code Repo",
            repository_name=f"{sagemaker_project_name}-deploy",
            code=codecommit.Code.from_asset(
                asset=deploy_app_asset,
                branch="main",
            ),
        )
        return codebuild.Source.code_commit(repository=repository)

    def __init__(
        self,
        scope: Construct,
        id: str,
        deploy_app_asset: s3_assets.Asset,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        model_package_group_name: str,
        model_bucket_name: str,
        enable_network_isolation: str,
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
        repository_type: RepositoryType,
        access_token_secret_name: Optional[str],
        aws_codeconnection_arn: Optional[str],
        repository_owner: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id)

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

        # Import model bucket
        model_bucket = s3.Bucket.from_bucket_name(self, "ModelBucket", bucket_name=model_bucket_name)

        codebuild_env_vars = {
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
            "DEV_SECURITY_GROUP_IDS": codebuild.BuildEnvironmentVariable(value=json.dumps(dev_security_group_ids)),
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
            "PROD_SECURITY_GROUP_IDS": codebuild.BuildEnvironmentVariable(value=json.dumps(prod_security_group_ids)),
            "ENABLE_NETWORK_ISOLATION": codebuild.BuildEnvironmentVariable(value=enable_network_isolation),
        }
        code_pipeline_deploy_project_name = "CodePipelineDeployProject"

        codebuild_source: ISource
        if repository_type == RepositoryType.CODECOMMIT:
            codebuild_source = self.codebuild_source_for_codecommit(sagemaker_project_name, deploy_app_asset)
        elif repository_type == RepositoryType.GITHUB:
            codebuild_source, github_repo = self.codebuild_source_for_github(
                cast(str, repository_owner),
                sagemaker_project_name,
                deploy_app_asset,
                cast(str, access_token_secret_name),
                cast(str, aws_codeconnection_arn),
            )
            github_env_vars = {
                "CODE_CONNECTION_ARN": codebuild.BuildEnvironmentVariable(value=aws_codeconnection_arn),
                "SOURCE_REPOSITORY": codebuild.BuildEnvironmentVariable(
                    value=f"{repository_owner}/{sagemaker_project_name}-deploy"
                ),
            }
            # Append github_env_vars into codebuild_env_vars
            codebuild_env_vars = {**codebuild_env_vars, **github_env_vars}

        codebuild_project = codebuild.Project(
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
                                f"export REPOSITORY_TYPE={repository_type.value}",
                                'cdk deploy --require-approval never --app "python app.py" ',
                            ]
                        }
                    },
                }
            ),
            source=codebuild_source,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables=codebuild_env_vars,
            ),
        )
        if codebuild_project.role is not None:
            codebuild_project.role.attach_inline_policy(
                iam.Policy(
                    self,
                    "Policy",
                    statements=[
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
        if repository_type == RepositoryType.GITHUB and codebuild_project.role is not None:
            codebuild_project.role.attach_inline_policy(
                iam.Policy(
                    self,
                    "GitHubSecretsManagerPolicy",
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "codebuild:ImportSourceCredentials",
                                "codebuild:DeleteSourceCredentials",
                                "codebuild:ListSourceCredentials",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "codeconnections:UseConnection",
                                "codeconnections:PassConnection",
                                "codeconnections:GetConnection",
                                "codeconnections:GetConnectionToken",
                            ],
                            resources=[cast(str, aws_codeconnection_arn)],
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
                            resources=[codebuild_project.project_arn],
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
            runtime=lambdafunction.Runtime.PYTHON_3_13,
            handler="index.handler",
            role=custom_resource_lambda_role,
            code=lambdafunction.Code.from_inline(lambda_func_code),
            environment={
                "CODE_BUILD_PROJECT_NAME": codebuild_project.project_name,
            },
            timeout=Duration.minutes(5),
        )

        custom_resource = CustomResource(
            self,
            "Custom::CodeBuildTriggerResourceType",
            service_token=custom_resource_lambda.function_arn,
            properties={
                "CodeBuildProjectName": codebuild_project.project_name,
            },
        )
        custom_resource.node.add_dependency(codebuild_project)
        if repository_type == RepositoryType.GITHUB:
            custom_resource.node.add_dependency(github_repo)

        # CDK NAG suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            codebuild_project,
            [
                {
                    "id": "AwsSolutions-CB4",
                    "reason": (
                        "CodeBuild project uses the default AWS managed encryption which is "
                        "sufficient for model deployment builds. Customer managed KMS keys are "
                        "not required for this use case."
                    ),
                }
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            custom_resource_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": (
                        "Lambda function uses Python 3.9 runtime which is appropriate for this "
                        "custom resource trigger. Runtime version is managed by the CDK construct."
                    ),
                }
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            custom_resource_lambda_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "Wildcard permissions are required for CloudWatch logs as the exact log "
                        "group and stream names are generated dynamically during Lambda execution."
                    ),
                }
            ],
        )

        if codebuild_project.role is not None:
            cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
                codebuild_project.stack,
                f"{codebuild_project.role.node.path}/DefaultPolicy/Resource",
                [
                    {
                        "id": "AwsSolutions-IAM5",
                        "reason": (
                            "Wildcard permissions are required for CodeBuild logs and report groups "
                            "as the exact resource names are generated dynamically during build execution."
                        ),
                    }
                ],
            )

            # Suppress the Policy resource
            policy_construct = self.node.find_child("Policy")
            if policy_construct:
                cdk_nag.NagSuppressions.add_resource_suppressions(
                    policy_construct,
                    [
                        {
                            "id": "AwsSolutions-IAM5",
                            "reason": (
                                "Wildcard permissions are required for SageMaker model packages and "
                                "cross-account CDK role assumptions as the exact resource names are "
                                "generated dynamically during multi-account deployment."
                            ),
                        }
                    ],
                )
