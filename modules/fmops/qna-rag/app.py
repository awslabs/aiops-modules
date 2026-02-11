# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag
from aws_cdk import App
from pydantic import ValidationError

from settings import ApplicationSettings
from stack import RAGResources

app = App()

try:
    app_settings = ApplicationSettings()
except ValidationError as e:
    print(e)
    raise e

stack = RAGResources(
    scope=app,
    id=app_settings.seedfarmer_settings.app_prefix,
    vpc_id=app_settings.module_settings.vpc_id,
    cognito_pool_id=app_settings.module_settings.cognito_pool_id,
    os_domain_endpoint=app_settings.module_settings.os_domain_endpoint,
    os_domain_port=app_settings.module_settings.os_domain_port,
    os_security_group_id=app_settings.module_settings.os_security_group_id,
    os_index_name="rag-index",
    input_asset_bucket_name=app_settings.module_settings.input_asset_bucket_name,
    permissions_boundary_name=app_settings.module_settings.permissions_boundary_name,
    env=aws_cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
    tags=app_settings.module_settings.tags,
)

assert stack.rag_ingest_resource.s3_input_assets_bucket is not None
assert stack.rag_ingest_resource.s3_processed_assets_bucket is not None

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "IngestionGraphqlApiId": stack.rag_ingest_resource.graphql_api.api_id,
            "IngestionGraphqlArn": stack.rag_ingest_resource.graphql_api.arn,
            "QnAGraphqlApiId": stack.rag_resource.graphql_api.api_id,
            "QnAGraphqlArn": stack.rag_resource.graphql_api.arn,
            "InputAssetBucket": stack.rag_ingest_resource.s3_input_assets_bucket.bucket_name,
            "ProcessedInputBucket": stack.rag_ingest_resource.s3_processed_assets_bucket.bucket_name,
        }
    ),
)

aws_cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth(force=True)
