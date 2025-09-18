# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import ProjectStack

app = aws_cdk.App()
app_settings = ApplicationSettings()

stack = ProjectStack(
    app,
    id=app_settings.seedfarmer_settings.app_prefix,
    env=aws_cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
    **app_settings.module_settings.model_dump(),
    xgboost_abalone_project_settings=app_settings.xgboost_abalone_project_settings,
    model_deploy_project_settings=app_settings.model_deploy_project_settings,
    hf_import_models_project_settings=app_settings.hf_import_models_project_settings,
    batch_inference_project_settings=app_settings.batch_inference_project_settings,
)

aws_cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth()
