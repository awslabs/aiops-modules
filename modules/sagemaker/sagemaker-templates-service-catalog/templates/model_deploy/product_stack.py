# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import json
from typing import Any, List

import aws_cdk.aws_s3_assets as s3_assets
import aws_cdk.aws_servicecatalog as servicecatalog
from aws_cdk import Aws, CfnParameter, CustomResource, Duration, Tags
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambdafunction
from aws_cdk import aws_s3 as s3
from constructs import Construct

from common.code_repo_construct import GitHubRepositoryCreator, RepositoryType


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
        repository_type: RepositoryType,
        access_token_secret_name: str,
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
            github_token_secret_name=access_token_secret_name,
            repo_name=f"{sagemaker_project_name}-deploy",
            repo_description=f"Deployment repository for SageMaker project {sagemaker_project_name}",
            github_owner=repository_owner,
            s3_bucket_name=deploy_app_asset.s3_bucket_name,
            s3_bucket_object_key=deploy_app_asset.s3_object_key,
            code_connection_arn=aws_codeconnection_arn,
        )

        # Import model bucket
        model_bucket = s3.Bucket.from_bucket_name(self, "ModelBucket", bucket_name=model_bucket_name)

        code_pipeline_deploy_project_name = "CodePipelineDeployProject"

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
            source=codebuild.Source.git_hub(owner=repository_owner, repo=f"{sagemaker_project_name}-deploy"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables={
                    "CODE_CONNECTION_ARN": codebuild.BuildEnvironmentVariable(value=aws_codeconnection_arn),
                    "SOURCE_REPOSITORY": codebuild.BuildEnvironmentVariable(
                        value=f"{repository_owner}/{sagemaker_project_name}-deploy"
                    ),
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
                            resources=[aws_codeconnection_arn],
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
        custom_resource.node.add_dependency(github_repo)
