# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk
import cdk_nag
from aws_cdk import CfnOutput
from pydantic import ValidationError

from settings import ApplicationSettings
from stack import CustomKernelStack

app = cdk.App()

try:
    app_settings = ApplicationSettings()
except ValidationError as e:
    print(e)
    raise e

app_image_config_name = (
    app_settings.module_settings.app_image_config_name or f"{app_settings.seedfarmer_settings.app_prefix}-app-config"
)
sagemaker_image_name = (
    app_settings.module_settings.sagemaker_image_name or f"{app_settings.seedfarmer_settings.app_prefix}-echo-kernel"
)
custom_kernel_name = (
    app_settings.module_settings.custom_kernel_name or f"{app_settings.seedfarmer_settings.app_prefix}-echo-kernel"
)

stack = CustomKernelStack(
    scope=app,
    construct_id=app_settings.seedfarmer_settings.app_prefix,
    sagemaker_image_name=sagemaker_image_name,
    ecr_repo_name=app_settings.module_settings.ecr_repo_name,
    app_image_config_name=app_image_config_name,
    custom_kernel_name=custom_kernel_name,
    kernel_user_uid=app_settings.module_settings.kernel_user_uid,
    kernel_user_gid=app_settings.module_settings.kernel_user_gid,
    mount_path=app_settings.module_settings.kernel_user_home_mount_path,
    permissions_boundary_name=app_settings.module_settings.permissions_boundary_name,
    env=cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
    tags=app_settings.module_settings.tags,
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ECRRepositoryName": app_settings.module_settings.ecr_repo_name,
            "CustomKernelImageName": sagemaker_image_name,
            "CustomKernelImageURI": stack.image_uri,
            "AppImageConfigName": app_image_config_name,
            "SageMakerCustomKernelRoleArn": stack.sagemaker_studio_image_role.role_arn,
        }
    ),
)

cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth()
