# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any

from aws_cdk import Stack, Tags
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sagemaker as sagemaker
from aws_cdk.aws_ecr_assets import DockerImageAsset
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct


class CustomKernelStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_prefix: str,
        sagemaker_image_name: str,
        ecr_repo_name: str,
        app_image_config_name: str,
        custom_kernel_name: str,
        kernel_user_uid: int,
        kernel_user_gid: int,
        mount_path: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        Tags.of(self).add(key="Deployment", value=app_prefix[:64])

        # ECR Image deployment
        repo = ecr.Repository.from_repository_name(self, id=f"{app_prefix}-ecr-repo", repository_name=ecr_repo_name)

        local_image = DockerImageAsset(
            self,
            "ImageExtractionDockerImage",
            directory=os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                f"docker/{sagemaker_image_name}",
            ),
        )

        self.image_uri = f"{repo.repository_uri}:latest"
        deployment = ECRDeployment(
            self,
            "ImageURI",
            src=DockerImageName(local_image.image_uri),
            dest=DockerImageName(self.image_uri),
        )

        # SageMaker Studio Image Role
        self.sagemaker_studio_image_role = iam.Role(
            self,
            f"{app_prefix}-image-role",
            role_name=f"{app_prefix}-image-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
        )

        # Image
        image = sagemaker.CfnImage(
            self,
            f"{app_prefix}-image",
            image_name=sagemaker_image_name,
            image_role_arn=self.sagemaker_studio_image_role.role_arn,
        )
        image.node.add_dependency(deployment)

        # Image Version
        image_version = sagemaker.CfnImageVersion(
            self,
            f"{app_prefix}-image-version",
            image_name=sagemaker_image_name,
            base_image=self.image_uri,
        )
        image_version.node.add_dependency(image)

        # App Image Config
        app_image_config = sagemaker.CfnAppImageConfig(
            self,
            f"{app_prefix}-app-image-config",
            app_image_config_name=app_image_config_name,
            kernel_gateway_image_config=sagemaker.CfnAppImageConfig.KernelGatewayImageConfigProperty(
                kernel_specs=[
                    sagemaker.CfnAppImageConfig.KernelSpecProperty(
                        name=custom_kernel_name, display_name=sagemaker_image_name
                    )
                ],
                file_system_config=sagemaker.CfnAppImageConfig.FileSystemConfigProperty(
                    default_uid=kernel_user_uid,
                    default_gid=kernel_user_gid,
                    mount_path=mount_path,
                ),
            ),
        )
        app_image_config.node.add_dependency(image_version)

        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Image Role needs Sagemaker Full Access",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonSageMakerFullAccess",
                    ],
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="ECR Deployment Service Role needs Full Access",
                ),
            ],
        )
