#!/usr/bin/env python3
"""Create a Event Bus Stack."""

import aws_cdk as cdk

from event_bus.settings import ApplicationSettings
from event_bus.stack import EventBusStack

# Load application settings from env vars.
app_settings = ApplicationSettings()

env = cdk.Environment(
    account=app_settings.default.account,
    region=app_settings.default.region,
)

app = cdk.App()

stack = EventBusStack(
    scope=app,
    construct_id=app_settings.settings.app_prefix,
    env=env,
    **app_settings.parameters.model_dump(),
)

app.synth()
