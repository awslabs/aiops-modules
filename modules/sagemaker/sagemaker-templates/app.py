# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk

from stack import ServiceCatalogStack

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"

DEFAULT_PORTFOLIO_NAME = "MLOps SageMaker Project Templates"
DEFAULT_PORTFOLIO_OWNER = "administrator"


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

portfolio_name = os.getenv(_param("PORTFOLIO_NAME"), DEFAULT_PORTFOLIO_NAME)
portfolio_owner = os.getenv(_param("PORTFOLIO_OWNER"), DEFAULT_PORTFOLIO_OWNER)
portfolio_access_role_arn = os.getenv(_param("PORTFOLIO_ACCESS_ROLE_ARN"))

if not portfolio_access_role_arn:
    raise ValueError("Missing input parameter portfolio-access-role-arn")

app = aws_cdk.App()
stack = ServiceCatalogStack(
    app,
    app_prefix,
    portfolio_name=portfolio_name,
    portfolio_owner=portfolio_owner,
    portfolio_access_role_arn=portfolio_access_role_arn,
)


aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ServiceCatalogPortfolioName": stack.portfolio_name,
            "ServiceCatalogPortfolioOwner": stack.portfolio_owner,
        }
    ),
)

app.synth()
