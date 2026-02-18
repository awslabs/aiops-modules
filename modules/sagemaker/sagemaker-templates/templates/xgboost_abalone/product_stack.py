# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List, Optional

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_assets as s3_assets
import aws_cdk.aws_sagemaker as sagemaker
import cdk_nag
from aws_cdk import Aws, CfnOutput, RemovalPolicy, Tags
from constructs import Construct

from settings import RepositoryType
from templates.xgboost_abalone.pipeline_constructs.build_pipeline_construct import (
    BuildPipelineConstruct,
)


class XGBoostAbaloneProject(Construct):
    DESCRIPTION: str = "Creates a SageMaker pipeline which trains a model on Abalone dataset."
    TEMPLATE_NAME: str = "Train a model on Abalone dataset using XGBoost"

    def __init__(
        self,
        scope: Construct,
        id: str,
        build_app_asset: s3_assets.Asset,
        dev_account_id: str,
        pre_prod_account_id: str,
        prod_account_id: str,
        sagemaker_domain_id: str,
        sagemaker_domain_arn: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        dev_vpc_id: str,
        dev_subnet_ids: List[str],
        enable_network_isolation: str,
        encrypt_inter_container_traffic: str,
        repository_type: RepositoryType,
        access_token_secret_name: Optional[str],
        aws_codeconnection_arn: Optional[str],
        repository_owner: Optional[str],
        s3_access_logs_bucket_arn: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id)

        s3_access_logs_bucket: Optional[s3.IBucket] = None
        if s3_access_logs_bucket_arn:
            s3_access_logs_bucket = s3.Bucket.from_bucket_arn(self, "AccessLogsBucket", s3_access_logs_bucket_arn)

        dev_account_id = Aws.ACCOUNT_ID if not dev_account_id else dev_account_id
        pre_prod_account_id = Aws.ACCOUNT_ID if not pre_prod_account_id else pre_prod_account_id
        prod_account_id = Aws.ACCOUNT_ID if not prod_account_id else prod_account_id

        # Deduplicate account IDs to avoid "Duplicate principal" errors in single-account deployments
        unique_account_ids = list(dict.fromkeys([dev_account_id, pre_prod_account_id, prod_account_id]))
        # Deduplicate cross-account IDs (pre-prod and prod) for KMS and S3 policies
        unique_cross_account_ids = list(dict.fromkeys([pre_prod_account_id, prod_account_id]))

        dev_vpc = None
        if dev_vpc_id:
            dev_vpc = ec2.Vpc.from_lookup(self, "dev-vpc", vpc_id=dev_vpc_id)

        Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)
        if sagemaker_domain_id:
            Tags.of(self).add("sagemaker:domain-id", sagemaker_domain_id)
        if sagemaker_domain_arn:
            Tags.of(self).add("sagemaker:domain-arn", sagemaker_domain_arn)

        # create kms key to be used by the assets bucket
        kms_key = kms.Key(
            self,
            "Artifacts Bucket KMS Key",
            description="key used for encryption of data in Amazon S3",
            enable_key_rotation=True,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["kms:*"],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                        principals=[iam.AccountRootPrincipal()],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "kms:Encrypt",
                            "kms:Decrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:DescribeKey",
                        ],
                        resources=[
                            "*",
                        ],
                        principals=[iam.AccountPrincipal(account_id) for account_id in unique_cross_account_ids],
                    ),
                ]
            ),
        )

        model_bucket = s3.Bucket(
            self,
            "S3 Artifact",
            bucket_name=f"mlops-{sagemaker_project_name}-{Aws.ACCOUNT_ID}",
            encryption_key=kms_key,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,  # Blocks insecure requests to the bucket
            server_access_logs_bucket=s3_access_logs_bucket,
            server_access_logs_prefix=(
                f"mlops-{sagemaker_project_name}-model-artifacts/" if s3_access_logs_bucket else None
            ),
        )

        # DEV account access to objects in the bucket
        model_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AddDevPermissions",
                actions=["s3:*"],
                resources=[
                    model_bucket.arn_for_objects(key_pattern="*"),
                    model_bucket.bucket_arn,
                ],
                principals=[
                    iam.AccountRootPrincipal(),
                ],
            )
        )

        # PROD account access to objects in the bucket
        model_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AddCrossAccountPermissions",
                actions=["s3:List*", "s3:Get*", "s3:Put*"],
                resources=[
                    model_bucket.arn_for_objects(key_pattern="*"),
                    model_bucket.bucket_arn,
                ],
                principals=[iam.AccountPrincipal(account_id) for account_id in unique_cross_account_ids],
            )
        )

        model_package_group_name = f"{sagemaker_project_name}-{sagemaker_project_id}"

        # cross account model registry resource policy
        model_package_group_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    sid="ModelPackageGroup",
                    actions=[
                        "sagemaker:DescribeModelPackageGroup",
                    ],
                    resources=[
                        (
                            f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package-group/"
                            f"{model_package_group_name}"
                        )
                    ],
                    principals=[
                        iam.ArnPrincipal(f"arn:{Aws.PARTITION}:iam::{account_id}:root")
                        for account_id in unique_account_ids
                    ],
                ),
                iam.PolicyStatement(
                    sid="ModelPackage",
                    actions=[
                        "sagemaker:DescribeModelPackage",
                        "sagemaker:ListModelPackages",
                        "sagemaker:UpdateModelPackage",
                        "sagemaker:CreateModel",
                    ],
                    resources=[
                        (
                            f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/"
                            f"{model_package_group_name}/*"
                        )
                    ],
                    principals=[
                        iam.ArnPrincipal(f"arn:{Aws.PARTITION}:iam::{account_id}:root")
                        for account_id in unique_account_ids
                    ],
                ),
            ]
        ).to_json()

        sagemaker.CfnModelPackageGroup(
            self,
            "Model Package Group",
            model_package_group_name=model_package_group_name,
            model_package_group_description=f"Model Package Group for {sagemaker_project_name}",
            model_package_group_policy=model_package_group_policy,
        )

        kms_key = kms.Key(
            self,
            "Pipeline Bucket KMS Key",
            description="key used for encryption of data in Amazon S3",
            enable_key_rotation=True,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["kms:*"],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                        principals=[iam.AccountRootPrincipal()],
                    )
                ]
            ),
        )

        pipeline_artifact_bucket = s3.Bucket(
            self,
            "Pipeline Bucket",
            bucket_name=f"pipeline-{sagemaker_project_name}-{Aws.ACCOUNT_ID}",
            encryption_key=kms_key,
            versioned=True,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            server_access_logs_bucket=s3_access_logs_bucket,
            server_access_logs_prefix=(
                f"pipeline-{sagemaker_project_name}-artifacts/" if s3_access_logs_bucket else None
            ),
        )

        security_group_ids = []
        if dev_vpc and dev_subnet_ids:
            security_group_ids = [ec2.SecurityGroup(self, "Security Group", vpc=dev_vpc).security_group_id]
        else:
            dev_subnet_ids = []

        BuildPipelineConstruct(
            self,
            "build",
            project_name=sagemaker_project_name,
            project_id=sagemaker_project_id,
            domain_id=sagemaker_domain_id,
            domain_arn=sagemaker_domain_arn,
            model_package_group_name=model_package_group_name,
            model_bucket=model_bucket,
            pipeline_artifact_bucket=pipeline_artifact_bucket,
            repo_asset=build_app_asset,
            enable_network_isolation=enable_network_isolation,
            encrypt_inter_container_traffic=encrypt_inter_container_traffic,
            subnet_ids=dev_subnet_ids,
            security_group_ids=security_group_ids,
            repository_type=repository_type,
            access_token_secret_name=access_token_secret_name,
            aws_codeconnection_arn=aws_codeconnection_arn,
            repository_owner=repository_owner,
        )

        if not s3_access_logs_bucket:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                model_bucket,
                [
                    {
                        "id": "AwsSolutions-S1",
                        "reason": "S3 access logging is optional and was not configured for this deployment.",
                    }
                ],
            )
            cdk_nag.NagSuppressions.add_resource_suppressions(
                pipeline_artifact_bucket,
                [
                    {
                        "id": "AwsSolutions-S1",
                        "reason": "S3 access logging is optional and was not configured for this deployment.",
                    }
                ],
            )

        CfnOutput(
            self,
            "Model Bucket Name",
            value=model_bucket.bucket_name,
        )

        CfnOutput(
            self,
            "Model Package Group Name",
            value=model_package_group_name,
        )
