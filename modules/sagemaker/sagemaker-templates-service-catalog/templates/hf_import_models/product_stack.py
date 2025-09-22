# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional

import aws_cdk
from aws_cdk import Aws, CfnOutput, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct

from settings import RepositoryType
from templates.hf_import_models.pipeline_constructs.build_pipeline_construct import BuildPipelineConstruct


class HfImportModelsProject(Construct):
    DESCRIPTION: str = "Enables the import of Hugging Face models"
    TEMPLATE_NAME: str = "Hugging Face Model Import"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        build_app_asset: s3_assets.Asset,
        sagemaker_domain_id: str,
        sagemaker_domain_arn: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        pre_prod_account_id: str,
        prod_account_id: str,
        hf_access_token_secret: str,
        hf_model_id: str,
        repository_type: RepositoryType,
        access_token_secret_name: Optional[str],
        aws_codeconnection_arn: Optional[str],
        repository_owner: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id)

        pre_prod_account_id = Aws.ACCOUNT_ID if not pre_prod_account_id else pre_prod_account_id
        prod_account_id = Aws.ACCOUNT_ID if not prod_account_id else prod_account_id

        Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)
        if sagemaker_domain_id:
            Tags.of(self).add("sagemaker:domain-id", sagemaker_domain_id)
        if sagemaker_domain_arn:
            Tags.of(self).add("sagemaker:domain-arn", sagemaker_domain_arn)

        # create kms key to be used by the assets bucket
        kms_key_artifact = kms.Key(
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
                        principals=[
                            iam.AccountPrincipal(pre_prod_account_id),
                            iam.AccountPrincipal(prod_account_id),
                        ],
                    ),
                ]
            ),
        )

        s3_artifact = s3.Bucket(
            self,
            "S3 Artifact",
            bucket_name=f"mlops-{sagemaker_project_name}-{Aws.ACCOUNT_ID}",  # Bucket name has a limit of 63 characters
            encryption_key=kms_key_artifact,
            versioned=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            enforce_ssl=True,  # Blocks insecure requests to the bucket
        )

        # DEV account access to objects in the bucket
        s3_artifact.grant_read_write(iam.AccountRootPrincipal())

        # PROD account access to objects in the bucket
        s3_artifact.grant_read_write(iam.AccountPrincipal(pre_prod_account_id))
        s3_artifact.grant_read_write(iam.AccountPrincipal(prod_account_id))

        # cross account model registry resource policy
        model_package_group_name = f"{sagemaker_project_name}-{sagemaker_project_id}"
        model_package_group_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    sid="ModelPackageGroup",
                    actions=[
                        "sagemaker:DescribeModelPackageGroup",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package-group/{model_package_group_name}"
                    ],
                    principals=[
                        iam.AccountPrincipal(pre_prod_account_id),
                        iam.AccountPrincipal(prod_account_id),
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
                        f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/{model_package_group_name}/*"
                    ],
                    principals=[
                        iam.AccountPrincipal(pre_prod_account_id),
                        iam.AccountPrincipal(prod_account_id),
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
            tags=[
                aws_cdk.CfnTag(key="sagemaker:project-id", value=sagemaker_project_id),
                aws_cdk.CfnTag(key="sagemaker:project-name", value=sagemaker_project_name),
            ],
        )

        BuildPipelineConstruct(
            self,
            "build",
            project_name=sagemaker_project_name,
            project_id=sagemaker_project_id,
            domain_id=sagemaker_domain_id,
            domain_arn=sagemaker_domain_arn,
            s3_artifact=s3_artifact,
            repo_asset=build_app_asset,
            model_package_group_name=model_package_group_name,
            hf_access_token_secret=hf_access_token_secret,
            hf_model_id=hf_model_id,
            repository_type=repository_type,
            access_token_secret_name=access_token_secret_name,
            aws_codeconnection_arn=aws_codeconnection_arn,
            repository_owner=repository_owner,
        )

        CfnOutput(
            self,
            "Model Bucket Name",
            value=s3_artifact.bucket_name,
        )

        CfnOutput(
            self,
            "Model Package Group Name",
            value=model_package_group_name,
        )
