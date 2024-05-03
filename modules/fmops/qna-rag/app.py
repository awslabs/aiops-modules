# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App, CfnOutput
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

app = App()

stack = RAGResources(
    scope=app,
    id=app_prefix,
    vpc_id=vpc_id,
    cognito_pool_id=cognito_pool_id,
    os_domain_endpoint=os_domain_endpoint,
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
            "GraphqlApiId": stack.rag_resource.graphql_api.api_id,
            "GraphqlArn": stack.rag_resource.graphql_api.arn
        }
    ),
)

app.synth(force=True)
