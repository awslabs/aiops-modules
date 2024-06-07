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
    id=app_settings.settings.app_prefix,
    env=environment,
    **app_settings.parameters.model_dump(),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=False))

app.synth()
