# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App
from stack import RAGResources


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"
vpc_id = os.getenv(_param("VPC_ID"))
cognito_pool_id = os.getenv(_param("COGNITO_POOL_ID"))
os_domain_endpoint = os.getenv(_param("OS_DOMAIN_ENDPOINT"))
os_security_group_id = os.getenv(_param("OS_SECURITY_GROUP_ID"))


if not vpc_id:
    raise ValueError("Missing input parameter vpc-id")

if not cognito_pool_id:
    raise ValueError("Missing input parameter cognito-pool-id")

if not os_domain_endpoint:
    raise ValueError("Missing input parameter os-domain-endpoint")

if not os_security_group_id:
    raise ValueError("Missing input parameter os-security-group-id")

app = App()

stack = RAGResources(
    scope=app,
    id=app_prefix,
    vpc_id=vpc_id,
    cognito_pool_id=cognito_pool_id,
    os_domain_endpoint=os_domain_endpoint,
    os_security_group_id=os_security_group_id,
    os_index_name="rag-index",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

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

app.synth(force=True)
