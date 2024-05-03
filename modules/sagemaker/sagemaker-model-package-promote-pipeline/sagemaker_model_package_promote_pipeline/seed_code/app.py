#!/usr/bin/env python3
"""Create a Sagemaker Model Stack."""

import aws_cdk as cdk
from stack.settings import ApplicationSettings
from stack.stack import SagemakerModelPackageStack

# Load application settings from env vars.
app_settings = ApplicationSettings()

env = cdk.Environment(
    account=app_settings.default.account,
    region=app_settings.default.region,
)

app = cdk.App()

stack = SagemakerModelPackageStack(
    scope=app,
    construct_id=app_settings.parameters.app_prefix,
    env=env,
    **app_settings.parameters.model_dump(),
)

app.synth()
