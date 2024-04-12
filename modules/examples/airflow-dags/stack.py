# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Optional, cast

import aws_cdk.aws_iam as aws_iam
import cdk_nag
import aws_cdk.aws_s3 as aws_s3
from aws_cdk import Aspects, Stack, Tags, RemovalPolicy, Aws
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class DagResources(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        deployment_name: str,
        module_name: str,
        mwaa_exec_role: str,
        bucket_policy_arn: Optional[str] = None,
        permission_boundary_arn: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # MLOPS Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.mwaa_exec_role = mwaa_exec_role

        super().__init__(
            scope,
            id,
            description="This stack deploys Example DAGs resources for MLOps",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment", value=f"mlops-{deployment_name}"
        )
        dep_mod = f"{project_name}-{deployment_name}-{module_name}"
        account: str = Aws.ACCOUNT_ID
        region: str = Aws.REGION

        mlops_assets_bucket = aws_s3.Bucket(
            self,
            id="mlops-assets-bucket",
            versioned=False,
            bucket_name=f"{dep_mod}-{account}-{region}",
            removal_policy=RemovalPolicy.DESTROY,
            encryption=aws_s3.BucketEncryption.KMS_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        self.mlops_assets_bucket = mlops_assets_bucket
        # Create Dag IAM Role and policy
        dag_statement = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=["s3:List*", "s3:Get*", "s3:Put*"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[
                        mlops_assets_bucket.bucket_arn,
                        f"{mlops_assets_bucket.bucket_arn}/*",
                    ],
                )
            ]
        )

        managed_policies = (
            [
                aws_iam.ManagedPolicy.from_managed_policy_arn(
                    self, "bucket-policy", bucket_policy_arn
                )
            ]
            if bucket_policy_arn
            else []
        )

        # Role with Permission Boundary
        r_name = f"mlops-{self.deployment_name}-{self.module_name}-dag-role"
        dag_role = aws_iam.Role(
            self,
            f"dag-role-{self.deployment_name}-{self.module_name}",
            assumed_by=aws_iam.ArnPrincipal(self.mwaa_exec_role),
            inline_policies={"DagPolicyDocument": dag_statement},
            managed_policies=managed_policies,
            permissions_boundary=(
                aws_iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    f"perm-boundary-{self.deployment_name}-{self.module_name}",
                    permission_boundary_arn,
                )
                if permission_boundary_arn
                else None
            ),
            role_name=r_name,
            path="/",
        )

        dag_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSageMakerFullAccess"
            )
        )
        dag_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "CloudWatchLogsFullAccess"
            )
        )

        # Define the IAM role
        sagemaker_execution_role = aws_iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                )
            ],
            path="/",
            role_name=f"SageMakerExecutionRole-{self.stack_name}",
        )

        # Add policy to allow access to S3 bucket
        sagemaker_execution_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["s3:*"],
                resources=[
                    mlops_assets_bucket.bucket_arn,
                    f"{mlops_assets_bucket.bucket_arn}/*",
                ],
            )
        )

        dag_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["iam:PassRole"], resources=[sagemaker_execution_role.role_arn]
            )
        )

        self.dag_role = dag_role
        self.sagemaker_execution_role = sagemaker_execution_role

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Logs are disabled for demo purposes",
                },
                {
                    "id": "AwsSolutions-S5",
                    "reason": "No OAI needed - no one is accessing this data without explicit permissions",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to MLOPS resources",
                },
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Managed Policies are for service account roles only",
                },
            ],
        )
