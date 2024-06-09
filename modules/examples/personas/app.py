# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
from settings import ApplicationSettings
from stack import Personas


app = aws_cdk.App()
# Load application settings from env vars.
app_settings = ApplicationSettings()


stack = Personas(
    scope=app,
    construct_id=app_settings.settings.app_prefix,
    bucket_name=app_settings.parameters.bucket_name,
    env=aws_cdk.Environment(
        account=app_settings.default.account,
        region=app_settings.default.region,
    )
)

app.synth()
