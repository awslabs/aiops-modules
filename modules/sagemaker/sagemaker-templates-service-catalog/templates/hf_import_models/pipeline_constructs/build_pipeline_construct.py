# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from typing import Any, Optional, cast

import aws_cdk
import cdk_nag
from aws_cdk import Aws
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from constructs import Construct

from common.code_repo_construct import GitHubRepositoryCreator
from settings import RepositoryType


class BuildPipelineConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        project_name: str,
        project_id: str,
        domain_id: str,
        domain_arn: str,
        s3_artifact: s3.IBucket,
        repo_asset: s3_assets.Asset,
        model_package_group_name: str,
        hf_access_token_secret: str,
        hf_model_id: str,
        repository_type: RepositoryType,
        access_token_secret_name: Optional[str],
        aws_codeconnection_arn: Optional[str],
        repository_owner: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define resource names
        codepipeline_name = f"{project_name}-{construct_id}"

        sagemaker_pipeline_name = f"{project_name}-{project_id}"
        sagemaker_pipeline_description = f"{project_name} Model Build Pipeline"

        # Create source repo from seed bucket/key
        build_app_repository: codecommit.IRepository
        if repository_type == RepositoryType.CODECOMMIT:
            build_app_repository = codecommit.Repository(
                self,
                "Build App Code Repo",
                repository_name=f"{project_name}-{construct_id}",
                code=codecommit.Code.from_asset(
                    asset=repo_asset,
                    branch="main",
                ),
            )
            aws_cdk.Tags.of(build_app_repository).add("sagemaker:project-id", project_id)
            aws_cdk.Tags.of(build_app_repository).add("sagemaker:project-name", project_name)
            if domain_id:
                aws_cdk.Tags.of(build_app_repository).add("sagemaker:domain-id", domain_id)
            if domain_arn:
                aws_cdk.Tags.of(build_app_repository).add("sagemaker:domain-arn", domain_arn)
        elif repository_type == RepositoryType.GITHUB:
            GitHubRepositoryCreator(
                self,
                "Build App Code Repo",
                github_token_secret_name=cast(str, access_token_secret_name),
                repo_name=f"{project_name}-{construct_id}",
                repo_description=f"Repository for project {project_name}",
                github_owner=cast(str, repository_owner),
                s3_bucket_name=repo_asset.s3_bucket_name,
                s3_bucket_object_key=repo_asset.s3_object_key,
                code_connection_arn=cast(str, aws_codeconnection_arn),
            )

        sagemaker_seedcode_bucket = s3.Bucket.from_bucket_name(
            self, "SageMaker Seedcode Bucket", f"sagemaker-{Aws.REGION}-{Aws.ACCOUNT_ID}"
        )

        codebuild_role = iam.Role(
            self,
            "CodeBuild Role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/service-role/",
        )

        sagemaker_execution_role = iam.Role(
            self,
            "SageMaker Execution Role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            path="/service-role/",
        )

        # Create a policy statement for SageMaker pull
        sagemaker_policy = iam.Policy(
            self,
            "SageMaker Policy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:Describe*",
                            "ecr:GetAuthorizationToken",
                            "ecr:GetDownloadUrlForLayer",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "kms:Encrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[f"arn:{Aws.PARTITION}:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:key/*"],
                    ),
                ]
            ),
        )

        cloudwatch.Metric.grant_put_metric_data(sagemaker_policy)
        sagemaker_execution_role.grant_pass_role(sagemaker_policy)  # type: ignore[arg-type]
        s3_artifact.grant_read_write(sagemaker_policy)
        sagemaker_seedcode_bucket.grant_read_write(sagemaker_policy)

        # Attach the policy
        sagemaker_policy.attach_to_role(sagemaker_execution_role)
        sagemaker_policy.attach_to_role(codebuild_role)

        cdk_nag.NagSuppressions.add_resource_suppressions(
            sagemaker_policy,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "Wildcard permissions are required for ML operations: "
                        "1) CloudWatch logs require wildcard for dynamic log group/stream creation "
                        "2) ECR Describe* actions are needed for container image discovery "
                        "3) KMS ReEncrypt* actions are required for cross-region key operations "
                        "4) S3 and SageMaker resources use dynamic naming patterns in ML pipelines"
                    ),
                }
            ],
        )

        # Grant extra permissions for the SageMaker role
        sagemaker_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateModel",
                    "sagemaker:DeleteModel",
                    "sagemaker:DescribeModel",
                    "sagemaker:AddTags",
                    "sagemaker:DeleteTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model/*",
                ],
            ),
        )
        sagemaker_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateModelPackageGroup",
                    "sagemaker:DeleteModelPackageGroup",
                    "sagemaker:DescribeModelPackageGroup",
                    "sagemaker:AddTags",
                    "sagemaker:DeleteTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package-group/{model_package_group_name}"
                ],
            ),
        )
        sagemaker_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateModelPackage",
                    "sagemaker:DeleteModelPackage",
                    "sagemaker:UpdateModelPackage",
                    "sagemaker:DescribeModelPackage",
                    "sagemaker:ListModelPackages",
                    "sagemaker:AddTags",
                    "sagemaker:DeleteTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/{model_package_group_name}/*"
                ],
            ),
        )

        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            aws_cdk.Stack.of(self),
            f"{self.node.path}/SageMaker Execution Role/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "Wildcard permissions are required for SageMaker execution role: "
                        "1) SageMaker model resources use dynamic naming during model creation "
                        "2) Model package resources require wildcard for versioned packages "
                        "These permissions are scoped to specific resource types and the project's model package group."
                    ),
                }
            ],
        )

        # Grant extra permissions for the CodeBuild role
        codebuild_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:DescribeModelPackage",
                    "sagemaker:ListModelPackages",
                    "sagemaker:UpdateModelPackage",
                    "sagemaker:AddTags",
                    "sagemaker:DeleteTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/{model_package_group_name}/*"
                ],
            ),
        )
        codebuild_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreatePipeline",
                    "sagemaker:UpdatePipeline",
                    "sagemaker:DeletePipeline",
                    "sagemaker:StartPipelineExecution",
                    "sagemaker:StopPipelineExecution",
                    "sagemaker:DescribePipelineExecution",
                    "sagemaker:ListPipelineExecutionSteps",
                    "sagemaker:AddTags",
                    "sagemaker:DeleteTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:pipeline/{sagemaker_pipeline_name}",
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:pipeline/{sagemaker_pipeline_name}/execution/*",
                ],
            ),
        )
        codebuild_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:CreateBucket",
                ],
                resources=[sagemaker_seedcode_bucket.bucket_arn],
            )
        )
        codebuild_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:secretsmanager:{Aws.REGION}:{Aws.ACCOUNT_ID}:secret:{hf_access_token_secret}-??????"
                ],
            )
        )

        # Create the CodeBuild project
        sm_pipeline_build = codebuild.PipelineProject(
            self,
            "SM Pipeline Build",
            project_name=f"{project_name}-{construct_id}",
            role=codebuild_role,
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables={
                    "SAGEMAKER_PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=project_name),
                    "SAGEMAKER_PROJECT_ID": codebuild.BuildEnvironmentVariable(value=project_id),
                    "SAGEMAKER_DOMAIN_ID": codebuild.BuildEnvironmentVariable(value=domain_id),
                    "SAGEMAKER_DOMAIN_ARN": codebuild.BuildEnvironmentVariable(value=domain_arn),
                    "MODEL_PACKAGE_GROUP_NAME": codebuild.BuildEnvironmentVariable(value=model_package_group_name),
                    "AWS_REGION": codebuild.BuildEnvironmentVariable(value=Aws.REGION),
                    "SAGEMAKER_PIPELINE_NAME": codebuild.BuildEnvironmentVariable(
                        value=sagemaker_pipeline_name,
                    ),
                    "SAGEMAKER_PIPELINE_DESCRIPTION": codebuild.BuildEnvironmentVariable(
                        value=sagemaker_pipeline_description,
                    ),
                    "SAGEMAKER_PIPELINE_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                        value=sagemaker_execution_role.role_arn,
                    ),
                    "ARTIFACT_BUCKET": codebuild.BuildEnvironmentVariable(value=s3_artifact.bucket_name),
                    "ARTIFACT_BUCKET_KMS_ID": codebuild.BuildEnvironmentVariable(
                        value=s3_artifact.encryption_key.key_id  # type: ignore[union-attr]
                    ),
                    "HUGGING_FACE_ACCESS_TOKEN_SECRET": codebuild.BuildEnvironmentVariable(
                        value=hf_access_token_secret
                    ),  # pass secret
                    "HUGGING_FACE_MODEL_ID": codebuild.BuildEnvironmentVariable(value=hf_model_id),
                },
            ),
        )

        source_artifact = codepipeline.Artifact(artifact_name="GitSource")

        build_pipeline = codepipeline.Pipeline(
            self, "Pipeline", pipeline_name=codepipeline_name, artifact_bucket=s3_artifact
        )

        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            aws_cdk.Stack.of(self),
            f"{self.node.path}/Pipeline/Role/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "CodePipeline service role requires wildcard permissions for S3 operations "
                        "to manage artifacts across different pipeline stages. These permissions are "
                        "scoped to the artifact bucket and necessary for pipeline functionality."
                    ),
                }
            ],
        )

        # add a source stage
        source_stage = build_pipeline.add_stage(stage_name="Source")
        if repository_type == RepositoryType.CODECOMMIT:
            source_stage.add_action(
                codepipeline_actions.CodeCommitSourceAction(
                    action_name="Source",
                    output=source_artifact,
                    repository=build_app_repository,
                    branch="main",
                )
            )
        elif repository_type == RepositoryType.GITHUB:
            source_stage.add_action(
                codepipeline_actions.CodeStarConnectionsSourceAction(
                    action_name="Source",
                    owner=cast(str, repository_owner),
                    repo=f"{project_name}-{construct_id}",
                    output=source_artifact,
                    branch="main",
                    connection_arn=cast(str, aws_codeconnection_arn),
                )
            )

        # add a build stage
        build_stage = build_pipeline.add_stage(stage_name="Build")
        build_stage.add_action(
            codepipeline_actions.CodeBuildAction(
                action_name="SMPipeline",
                input=source_artifact,
                project=sm_pipeline_build,
            )
        )

        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            aws_cdk.Stack.of(self),
            f"{self.node.path}/Pipeline/Source/Source/CodePipelineActionRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "CodePipeline source action role requires wildcard permissions for S3 operations "
                        "to access source artifacts and manage pipeline artifacts. These permissions are "
                        "necessary for CodeCommit/GitHub integration and artifact management."
                    ),
                }
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            sm_pipeline_build,
            [
                {
                    "id": "AwsSolutions-CB4",
                    "reason": (
                        "CodeBuild project uses the default AWS managed encryption which is "
                        "sufficient for ML pipeline builds. Customer managed KMS keys are "
                        "not required for this use case."
                    ),
                }
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            aws_cdk.Stack.of(self),
            f"{self.node.path}/CodeBuild Role/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "Wildcard permissions are required for SageMaker model packages, pipeline "
                        "executions, and image versions as the exact resource names are generated "
                        "dynamically during ML pipeline execution."
                    ),
                }
            ],
        )
