# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import RayImagePublishingStack

app_settings = ApplicationSettings()

app = aws_cdk.App()
stack = RayImagePublishingStack(
    scope=app,
    id=app_settings.settings.app_prefix,
    app_prefix=app_settings.settings.app_prefix,
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
            "RayImageUri": stack.image_uri,
        }
    ),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

app.synth()
