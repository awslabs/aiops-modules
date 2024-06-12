# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
import cdk_nag

from sagemaker_model_monitoring.settings import ApplicationSettings
from sagemaker_model_monitoring.stack import SageMakerModelMonitoringStack

# Load application settings from env vars.
app_settings = ApplicationSettings()

environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

app = aws_cdk.App()
stack = SageMakerModelMonitoringStack(
    scope=app,
    id=app_settings.seedfarmer_settings.app_prefix,
    env=environment,
    **app_settings.module_settings.model_dump(),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=False))

if app_settings.module_settings.tags:
    for tag_key, tag_value in app_settings.module_settings.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth()
