#!/usr/bin/env python3
"""
Cross-account deployment role for SageMaker model deployment pipeline.
Creates IAM role that allows a pipeline in another account to deploy SageMaker endpoints.
"""
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_iam as iam,
    Stack,
)


class CrossAccountDeployRoleStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        trusted_account_id: str,
        trusted_role_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create deployment role with trust to pipeline role in source account
        deploy_role = iam.Role(
            self,
            "DeployRole",
            role_name=f"sagemaker-model-deploy-role-{self.region}",
            assumed_by=iam.ArnPrincipal(
                f"arn:aws:iam::{trusted_account_id}:role/{trusted_role_name}"
            ),
            description=f"Cross-account deployment role for SageMaker model deployment from account {trusted_account_id}",
        )

        # Grant permissions for SageMaker endpoint deployment
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="SageMakerEndpointDeployment",
                actions=[
                    "sagemaker:CreateEndpoint",
                    "sagemaker:CreateEndpointConfig",
                    "sagemaker:CreateModel",
                    "sagemaker:DeleteEndpoint",
                    "sagemaker:DeleteEndpointConfig",
                    "sagemaker:DeleteModel",
                    "sagemaker:DescribeEndpoint",
                    "sagemaker:DescribeEndpointConfig",
                    "sagemaker:DescribeModel",
                    "sagemaker:UpdateEndpoint",
                    "sagemaker:UpdateEndpointWeightsAndCapacities",
                    "sagemaker:AddTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/*",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint-config/*",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:model/*",
                ],
            )
        )

        # Grant permissions for IAM role creation (for SageMaker execution role)
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="IAMRoleManagement",
                actions=[
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:GetRole",
                    "iam:PassRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",
                    "iam:GetRolePolicy",
                    "iam:TagRole",
                    "iam:UntagRole",
                ],
                resources=[
                    f"arn:aws:iam::{self.account}:role/sagemaker-*",
                ],
            )
        )

        # Grant CloudFormation permissions
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudFormationDeployment",
                actions=[
                    "cloudformation:CreateStack",
                    "cloudformation:UpdateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:DescribeStacks",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:DescribeStackResources",
                    "cloudformation:GetTemplate",
                    "cloudformation:ValidateTemplate",
                ],
                resources=[
                    f"arn:aws:cloudformation:{self.region}:{self.account}:stack/*/*",
                ],
            )
        )

        # Grant S3 permissions for model artifacts
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ModelArtifacts",
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    "arn:aws:s3:::sagemaker-*",
                ],
            )
        )

        # Grant ECR permissions for container images
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRImageAccess",
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:GetAuthorizationToken",
                ],
                resources=["*"],
            )
        )

        # Output the role ARN
        cdk.CfnOutput(
            self,
            "DeployRoleArn",
            value=deploy_role.role_arn,
            description="ARN of the cross-account deployment role",
        )


app = cdk.App()
CrossAccountDeployRoleStack(
    app,
    "sagemaker-model-deploy-cross-account-role",
    trusted_account_id=app.node.try_get_context("trusted_account_id"),
    trusted_role_name=app.node.try_get_context("trusted_role_name"),
)
app.synth()
