# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List

import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_assets as s3_assets
import aws_cdk.aws_servicecatalog as servicecatalog
from aws_cdk import Aws, CfnParameter, RemovalPolicy, Tags
from constructs import Construct

from templates.model_deploy.pipeline_constructs.deploy_pipeline_construct import (
    DeployPipelineConstruct,
)


class Product(servicecatalog.ProductStack):
    DESCRIPTION: str = "Creates a CodePipeline that deploys a model endpoint to dev, pre-prod, and prod environments."
    TEMPLATE_NAME: str = "Model deployment pipeline that deploys to dev, pre-prod, and prod"

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

        Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)

        pre_prod_account_id = Aws.ACCOUNT_ID if not pre_prod_account_id else pre_prod_account_id
        prod_account_id = Aws.ACCOUNT_ID if not prod_account_id else prod_account_id
        pre_prod_region = Aws.REGION if not pre_prod_region else pre_prod_region
        prod_region = Aws.REGION if not prod_region else prod_region

        # Import model bucket
        model_bucket = s3.Bucket.from_bucket_name(self, "ModelBucket", bucket_name=model_bucket_name)

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
            "PipelineBucket",
            bucket_name=f"pipeline-{sagemaker_project_name}-{sagemaker_project_id}-{Aws.ACCOUNT_ID}",
            encryption_key=kms_key,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        DeployPipelineConstruct(
            self,
            "deploy",
            project_name=sagemaker_project_name,
            project_id=sagemaker_project_id,
            model_bucket=model_bucket,
            pipeline_artifact_bucket=pipeline_artifact_bucket,
            model_package_group_name=model_package_group_name,
            repo_asset=deploy_app_asset,
            dev_vpc_id=dev_vpc_id,
            dev_subnet_ids=dev_subnet_ids,
            dev_security_group_ids=dev_security_group_ids,
            pre_prod_account_id=pre_prod_account_id,
            pre_prod_region=pre_prod_region,
            pre_prod_vpc_id=pre_prod_vpc_id,
            pre_prod_subnet_ids=pre_prod_subnet_ids,
            pre_prod_security_group_ids=pre_prod_security_group_ids,
            prod_account_id=prod_account_id,
            prod_region=prod_region,
            prod_vpc_id=prod_vpc_id,
            prod_subnet_ids=prod_subnet_ids,
            prod_security_group_ids=prod_security_group_ids,
        )
