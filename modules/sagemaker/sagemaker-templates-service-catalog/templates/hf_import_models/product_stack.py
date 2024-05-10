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

from typing import Any

import aws_cdk
import aws_cdk.aws_servicecatalog as servicecatalog
from aws_cdk import Aws, CfnOutput, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct

from templates.hf_import_models.pipeline_constructs.build_pipeline_construct import BuildPipelineConstruct


class Product(servicecatalog.ProductStack):
    DESCRIPTION: str = "Enables the import of Hugging Face models"
    TEMPLATE_NAME: str = "Hugging Face Model Import"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        build_app_asset: s3_assets.Asset,
        deploy_app_asset: s3_assets.Asset,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id)

        # Define required parmeters
        project_name = aws_cdk.CfnParameter(
            self,
            "SageMakerProjectName",
            type="String",
            description="The name of the SageMaker project.",
            min_length=1,
            max_length=32,
        ).value_as_string

        project_id = aws_cdk.CfnParameter(
            self,
            "SageMakerProjectId",
            type="String",
            min_length=1,
            max_length=16,
            description="Service generated Id of the project.",
        ).value_as_string

        staging_account = aws_cdk.CfnParameter(
            self,
            "StgAccountId",
            type="String",
            min_length=1,
            max_length=16,
            description="Staging account id.",
        ).value_as_string

        prod_account = aws_cdk.CfnParameter(
            self,
            "ProdAccountId",
            type="String",
            min_length=1,
            max_length=16,
            description="Prod account id.",
        ).value_as_string

        hf_access_token_secret = aws_cdk.CfnParameter(
            self,
            "HFAccessTokenSecret",
            type="String",
            min_length=1,
            description="AWS Secret Of Hugging Face Access Token",
        ).value_as_string

        hf_model_id = aws_cdk.CfnParameter(
            self,
            "HFModelID",
            type="String",
            min_length=1,
            description="Model ID from hf.co/models",
        ).value_as_string

        Tags.of(self).add("sagemaker:project-id", project_id)
        Tags.of(self).add("sagemaker:project-name", project_name)

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
                    )
                ]
            ),
        )

        # allow cross account access to the kms key
        kms_key_artifact.add_to_resource_policy(
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
                    iam.AccountPrincipal(staging_account),
                    iam.AccountPrincipal(prod_account),
                ],
            )
        )

        s3_artifact = s3.Bucket(
            self,
            "S3 Artifact",
            bucket_name=f"mlops-{project_name}-{Aws.ACCOUNT_ID}",  # Bucket name has a limit of 63 characters
            encryption_key=kms_key_artifact,
            versioned=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            enforce_ssl=True,  # Blocks insecure requests to the bucket
        )

        # DEV account access to objects in the bucket
        s3_artifact.grant_read_write(iam.AccountRootPrincipal())

        # PROD account access to objects in the bucket
        s3_artifact.grant_read_write(iam.AccountPrincipal(staging_account))
        s3_artifact.grant_read_write(iam.AccountPrincipal(prod_account))

        # cross account model registry resource policy
        model_package_group_name = f"{project_name}-{project_id}"
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
                        iam.AccountPrincipal(staging_account),
                        iam.AccountPrincipal(prod_account),
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
                        iam.AccountPrincipal(staging_account),
                        iam.AccountPrincipal(prod_account),
                    ],
                ),
            ]
        ).to_json()

        sagemaker.CfnModelPackageGroup(
            self,
            "Model Package Group",
            model_package_group_name=model_package_group_name,
            model_package_group_description=f"Model Package Group for {project_name}",
            model_package_group_policy=model_package_group_policy,
            tags=[
                aws_cdk.CfnTag(key="sagemaker:project-id", value=project_id),
                aws_cdk.CfnTag(key="sagemaker:project-name", value=project_name),
            ],
        )

        BuildPipelineConstruct(
            self,
            "build",
            project_name=project_name,
            project_id=project_id,
            s3_artifact=s3_artifact,
            repo_asset=build_app_asset,
            model_package_group_name=model_package_group_name,
            hf_access_token_secret=hf_access_token_secret,
            hf_model_id=hf_model_id,
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
