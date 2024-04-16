#!/usr/bin/env python3
"""Create a Sagemaker Model Package Promote Pipeline Stack."""

import aws_cdk as cdk

from sagemaker_model_package_promote_pipeline.settings import ApplicationSettings
from sagemaker_model_package_promote_pipeline.stack import (
    SagemakerModelPackagePipelineStack,
)

# Load application settings from env vars.
app_settings = ApplicationSettings()

env = cdk.Environment(
    account=app_settings.default.account,
    region=app_settings.default.region,
)

app = cdk.App()

stack = SagemakerModelPackagePipelineStack(
    scope=app,
    construct_id=app_settings.settings.app_prefix,
    env=env,
    **app_settings.parameters.model_dump(),
)

app.synth()
