# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import cast

import aws_cdk
from aws_cdk import CfnOutput

from stack import SagemakerStudioStack

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"

DEFAULT_STUDIO_DOMAIN_NAME = f"{app_prefix}-studio-domain"
DEFAULT_STUDIO_BUCKET_NAME = f"{app_prefix}-bucket"
DEFAULT_CUSTOM_KERNEL_APP_CONFIG_NAME = None
DEFAULT_CUSTOM_KERNEL_IMAGE_NAME = None
DEFAULT_ENABLE_CUSTOM_SAGEMAKER_PROJECTS = False


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
subnet_ids = json.loads(os.getenv(_param("SUBNET_IDS"), "[]"))
studio_domain_name = os.getenv(_param("STUDIO_DOMAIN_NAME"), DEFAULT_STUDIO_DOMAIN_NAME)
studio_bucket_name = os.getenv(_param("STUDIO_BUCKET_NAME"), DEFAULT_STUDIO_BUCKET_NAME)
app_image_config_name = os.getenv(_param("CUSTOM_KERNEL_APP_CONFIG_NAME"), DEFAULT_CUSTOM_KERNEL_APP_CONFIG_NAME)
image_name = os.getenv(_param("CUSTOM_KERNEL_IMAGE_NAME"), DEFAULT_CUSTOM_KERNEL_IMAGE_NAME)
enable_custom_sagemaker_projects = bool(
    os.getenv(_param("ENABLE_CUSTOM_SAGEMAKER_PROJECTS"), DEFAULT_ENABLE_CUSTOM_SAGEMAKER_PROJECTS)
)

environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

data_science_users = json.loads(os.getenv(_param("DATA_SCIENCE_USERS"), "[]"))
lead_data_science_users = json.loads(os.getenv(_param("LEAD_DATA_SCIENCE_USERS"), "[]"))

app = aws_cdk.App()
stack = SagemakerStudioStack(
    app,
    app_prefix,
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=cast(str, vpc_id),
    subnet_ids=subnet_ids,
    studio_domain_name=studio_domain_name,
    studio_bucket_name=studio_bucket_name,
    data_science_users=data_science_users,
    lead_data_science_users=lead_data_science_users,
    env=environment,
    app_image_config_name=cast(str, app_image_config_name),
    image_name=cast(str, image_name),
    enable_custom_sagemaker_projects=enable_custom_sagemaker_projects,
)


CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "StudioDomainName": stack.studio_domain.domain_name,
            "StudioDomainEFSId": stack.studio_domain.attr_home_efs_file_system_id,
            "StudioDomainId": stack.studio_domain.attr_domain_id,
            "StudioBucketName": studio_bucket_name,
            "DataScientistRoleArn": stack.sm_roles.data_scientist_role.role_arn,
            "LeadDataScientistRoleArn": stack.sm_roles.lead_data_scientist_role.role_arn,
            "SageMakerExecutionRoleArn": stack.sm_roles.sagemaker_studio_role.role_arn,
        }
    ),
)

app.synth()
