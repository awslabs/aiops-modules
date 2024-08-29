# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag
from aws_cdk import App
from sagemaker import image_uris  # type: ignore[import-untyped]
from sagemaker.sklearn import defaults  # type: ignore[import-untyped]

from settings import ApplicationSettings
from stack import MLOPSSFNResources

app = App()

app_settings = ApplicationSettings()


stack = MLOPSSFNResources(
    scope=app,
    id=app_settings.seedfarmer_settings.app_prefix,
    project_name=app_settings.seedfarmer_settings.project_name,
    deployment_name=app_settings.seedfarmer_settings.deployment_name,
    module_name=app_settings.seedfarmer_settings.module_name,
    model_name=app_settings.module_settings.model_name,
    schedule=app_settings.module_settings.schedule,
    env=aws_cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
)


image_uri = image_uris.retrieve(defaults.SKLEARN_NAME, region=app_settings.cdk_settings.region, version="1.2-1")

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "MlOpsBucket": stack.mlops_assets_bucket.bucket_name,
            "SageMakerExecutionRole": stack.sagemaker_execution_role.role_arn,
            "ImageUri": image_uri,
            "StateMachine": stack.state_machine_arn,
            "LambdaFunction": stack.lambda_function_arn,
        }
    ),
)

aws_cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

if app_settings.module_settings.tags:
    for tag_key, tag_value in app_settings.module_settings.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth(force=True)
