# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import MlflowImagePublishingStack

# Load application settings from env vars.
app_settings = ApplicationSettings()

app = aws_cdk.App()
stack = MlflowImagePublishingStack(
    scope=app,
    id=app_settings.settings.app_prefix,
    ecr_repo_name=app_settings.parameters.ecr_repository_name,
    env=aws_cdk.Environment(
        account=app_settings.default.account,
        region=app_settings.default.region,
    ),
)


aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "MlflowImageUri": stack.image_uri,
        }
    ),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

if app_settings.parameters.tags:
    for tag_key, tag_value in app_settings.parameters.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.settings.project_name)

app.synth()
