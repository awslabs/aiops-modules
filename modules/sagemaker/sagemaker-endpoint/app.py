# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import DeployEndpointStack

app = aws_cdk.App()
app_settings = ApplicationSettings()

stack = DeployEndpointStack(
    scope=app,
    id=app_settings.seedfarmer_settings.app_prefix,
    sagemaker_project_id=app_settings.module_settings.sagemaker_project_id,
    sagemaker_project_name=app_settings.module_settings.sagemaker_project_name,
    model_package_arn=app_settings.module_settings.model_package_arn,
    model_package_group_name=app_settings.module_settings.model_package_group_name,
    model_execution_role_arn=app_settings.module_settings.model_execution_role_arn,
    vpc_id=app_settings.module_settings.vpc_id,
    subnet_ids=app_settings.module_settings.subnet_ids,
    model_artifacts_bucket_arn=app_settings.module_settings.model_artifacts_bucket_arn,
    ecr_repo_arn=app_settings.module_settings.ecr_repo_arn,
    endpoint_config_prod_variant={
        "initial_instance_count": app_settings.module_settings.initial_instance_count,
        "initial_variant_weight": app_settings.module_settings.initial_variant_weight,
        "instance_type": app_settings.module_settings.instance_type,
        "variant_name": app_settings.module_settings.variant_name,
    },
    managed_instance_scaling=app_settings.module_settings.managed_instance_scaling,
    scaling_min_instance_count=app_settings.module_settings.scaling_min_instance_count,
    scaling_max_instance_count=app_settings.module_settings.scaling_max_instance_count,
    env=aws_cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
)

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ModelExecutionRoleArn": stack.model_execution_role.role_arn,
            "ModelName": stack.model.model_name,
            "ModelPackageArn": stack.model_package_arn,
            "EndpointName": stack.endpoint.attr_endpoint_name,
            "EndpointUrl": stack.endpoint_url,
        }
    ),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

if app_settings.module_settings.tags:
    for tag_key, tag_value in app_settings.module_settings.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth()
