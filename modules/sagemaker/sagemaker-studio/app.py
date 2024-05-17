# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag
from aws_cdk import CfnOutput

from settings import ApplicationSettings
from stack import SagemakerStudioStack

app = aws_cdk.App()
app_settings = ApplicationSettings()

stack = SagemakerStudioStack(
    scope=app,
    construct_id=app_settings.settings.app_prefix,
    vpc_id=app_settings.parameters.vpc_id,
    subnet_ids=app_settings.parameters.private_subnet_ids,
    studio_domain_name=app_settings.parameters.studio_domain_name,
    studio_bucket_name=app_settings.parameters.studio_bucket_name,
    data_science_users=app_settings.parameters.data_science_users,
    lead_data_science_users=app_settings.parameters.lead_data_science_users,
    app_image_config_name=app_settings.parameters.app_image_config_name,
    image_name=app_settings.parameters.image_name,
    enable_custom_sagemaker_projects=app_settings.parameters.enable_custom_sagemaker_projects,
    auth_mode=app_settings.parameters.auth_mode,
    env=aws_cdk.Environment(
        account=app_settings.default.account,
        region=app_settings.default.region,
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "StudioDomainName": stack.studio_domain.domain_name,
            "StudioDomainEFSId": stack.studio_domain.attr_home_efs_file_system_id,
            "StudioDomainId": stack.studio_domain.attr_domain_id,
            "StudioBucketName": app_settings.parameters.studio_bucket_name,
            "DataScientistRoleArn": stack.sm_roles.data_scientist_role.role_arn,
            "LeadDataScientistRoleArn": stack.sm_roles.lead_data_scientist_role.role_arn,
            "SageMakerExecutionRoleArn": stack.sm_roles.sagemaker_studio_role.role_arn,
        }
    ),
)

aws_cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

if app_settings.parameters.tags:
    for tag_key, tag_value in app_settings.parameters.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.settings.project_name)

app.synth()
