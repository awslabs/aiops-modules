#!/usr/bin/env python3
"""Create a Sagemaker Model Event Bus Stack."""

import aws_cdk as cdk

from sagemaker_model_event_bus.settings import ApplicationSettings
from sagemaker_model_event_bus.stack import SagemakerModelEventBusStack

# Load application settings from env vars.
app_settings = ApplicationSettings()

env = cdk.Environment(
    account=app_settings.default.account,
    region=app_settings.default.region,
)

app = cdk.App()

stack = SagemakerModelEventBusStack(
    scope=app,
    construct_id=app_settings.settings.app_prefix,
    env=env,
    **app_settings.parameters.model_dump(),
)

app.synth()
