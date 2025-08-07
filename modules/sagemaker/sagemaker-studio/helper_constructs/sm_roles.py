# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional

from aws_cdk import Aws
from aws_cdk import aws_iam as iam
from constructs import Construct


class SMRoles(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        s3_bucket_prefix: str,
        mlflow_artifact_store_bucket_name: Optional[str],
        role_path: Optional[str],
        permissions_boundary_arn: Optional[str],
        env: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        permissions_boundary = (
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "Boundary",
                permissions_boundary_arn,
            )
            if permissions_boundary_arn
            else None
        )

        cdk_deploy_policy = iam.Policy(
            self,
            "cdk_deploy_policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:*",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iam:PassRole"],
                    resources=[f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:role/cdk*"],
                ),
            ],
        )
        sm_deny_policy = iam.Policy(
            self,
            "sm-deny-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=[
                        "sagemaker:CreateProject",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=["sagemaker:UpdateModelPackage"],
                    resources=["*"],
                ),
            ],
        )

        services_policy = iam.Policy(
            self,
            "services-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "lambda:Create*",
                        "lambda:Update*",
                        "lambda:Invoke*",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker:ListTags",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "codecommit:GitPull",
                        "codecommit:GitPush",
                        "codecommit:*Branch*",
                        "codecommit:*PullRequest*",
                        "codecommit:*Commit*",
                        "codecommit:GetDifferences",
                        "codecommit:GetReferences",
                        "codecommit:GetRepository",
                        "codecommit:GetMerge*",
                        "codecommit:Merge*",
                        "codecommit:DescribeMergeConflicts",
                        "codecommit:*Comment*",
                        "codecommit:*File",
                        "codecommit:GetFolder",
                        "codecommit:GetBlob",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:GetRepositoryPolicy",
                        "ecr:DescribeRepositories",
                        "ecr:DescribeImages",
                        "ecr:ListImages",
                        "ecr:GetAuthorizationToken",
                        "ecr:GetLifecyclePolicy",
                        "ecr:GetLifecyclePolicyPreview",
                        "ecr:ListTagsForResource",
                        "ecr:DescribeImageScanFindings",
                        "ecr:CreateRepository",
                        "ecr:CompleteLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:InitiateLayerUpload",
                        "ecr:PutImage",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "servicecatalog:*",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:CreateStack",
                    ],
                    resources=["*"],
                ),
            ],
        )

        kms_policy = iam.Policy(
            self,
            "kms-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "kms:CreateGrant",
                        "kms:Decrypt",
                        "kms:DescribeKey",
                        "kms:Encrypt",
                        "kms:ReEncrypt",
                        "kms:GenerateDataKey",
                    ],
                    resources=["*"],
                ),
            ],
        )

        s3_policy = iam.Policy(
            self,
            "s3-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject",
                        "s3:Describe*",
                        "s3:GetObject",
                        "s3:PutBucket*",
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetBucketAcl",
                        "s3:GetBucketLocation",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:s3:::{s3_bucket_prefix}*/*",
                        f"arn:{Aws.PARTITION}:s3:::{s3_bucket_prefix}*",
                        f"arn:{Aws.PARTITION}:s3:::cdk*/*",
                        f"arn:{Aws.PARTITION}:s3:::cdk*",
                        f"arn:{Aws.PARTITION}:s3:::sagemaker*",
                        f"arn:{Aws.PARTITION}:s3:::sagemaker*/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:ListBucket"],
                    resources=[
                        f"arn:{Aws.PARTITION}:s3:::{s3_bucket_prefix}*",
                        f"arn:{Aws.PARTITION}:s3:::cdk*",
                        f"arn:{Aws.PARTITION}:s3:::sagemaker*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=["s3:DeleteBucket*"],
                    resources=["*"],
                ),
            ],
        )
        mlflow_policy = iam.Policy(
            self,
            "mlflow_policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker-mlflow:*",
                    ],
                    resources=["*"],
                ),
            ],
        )

        # create role for each persona

        # role for Data Scientist persona
        self.data_scientist_role = iam.Role(
            self,
            "data-scientist-role",
            path=role_path,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            permissions_boundary=permissions_boundary,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_ReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
            ],
        )

        sm_deny_policy.attach_to_role(self.data_scientist_role)
        services_policy.attach_to_role(self.data_scientist_role)
        kms_policy.attach_to_role(self.data_scientist_role)
        s3_policy.attach_to_role(self.data_scientist_role)
        mlflow_policy.attach_to_role(self.data_scientist_role)

        # role for Lead Data Scientist persona
        self.lead_data_scientist_role = iam.Role(
            self,
            "lead-data-scientist-role",
            path=role_path,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            permissions_boundary=permissions_boundary,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_ReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSCodeCommitPowerUser",
                ),
            ],
        )

        services_policy.attach_to_role(self.lead_data_scientist_role)
        kms_policy.attach_to_role(self.lead_data_scientist_role)
        s3_policy.attach_to_role(self.lead_data_scientist_role)
        cdk_deploy_policy.attach_to_role(self.lead_data_scientist_role)
        mlflow_policy.attach_to_role(self.lead_data_scientist_role)

        # default role for sagemaker persona
        self.sagemaker_studio_role = iam.Role(
            self,
            "sagemaker-studio-role",
            path=role_path,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            permissions_boundary=permissions_boundary,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_ReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
            ],
            inline_policies={
                "DescribeImageVersion": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:DescribeImageVersion",
                            ],
                            resources=[f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:image-version/*"],
                        )
                    ]
                )
            },
        )

        services_policy.attach_to_role(self.sagemaker_studio_role)
        kms_policy.attach_to_role(self.sagemaker_studio_role)
        s3_policy.attach_to_role(self.sagemaker_studio_role)

        mlflow_tracking_server_policy = iam.Policy(
            self,
            "mlflow-server-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:Get*",
                        "s3:Put*",
                        "s3:List*",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:s3:::{mlflow_artifact_store_bucket_name}*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker:AddTags",
                        "sagemaker:CreateModelPackageGroup",
                        "sagemaker:CreateModelPackage",
                        "sagemaker:UpdateModelPackage",
                        "sagemaker:DescribeModelPackageGroup",
                    ],
                    resources=["*"],
                ),
            ],
        )

        # Role for Mlflow Tracking Server
        self.mlflow_tracking_server_role = iam.Role(
            self,
            "mlflow-role",
            path=role_path,
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            permissions_boundary=permissions_boundary,
        )
        mlflow_tracking_server_policy.attach_to_role(self.mlflow_tracking_server_role)
