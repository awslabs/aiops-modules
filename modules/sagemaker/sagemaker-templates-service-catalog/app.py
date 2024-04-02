# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
import cdk_nag

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
pre_prod_vpc_id = os.getenv(_param("PRE_PROD_VPC_ID"))
pre_prod_private_subnet_ids = os.getenv(_param("PRE_PROD_PRIVATE_SUBNET_IDS"), "subnet-0b0b482eb3c8d1093,subnet-06871fc0a01b37291").split(",")
pre_prod_public_subnet_ids = os.getenv(_param("PRE_PROD_PUBLIC_SUBNET_IDS"), "subnet-006c070eb830ae59d,subnet-0da90f3194a1c76de").split(",")
prod_vpc_id = os.getenv(_param("PROD_VPC_ID"),'vpc-02e5ecf77ca03e093')
prod_private_subnet_ids = os.getenv(_param("PROD_PRIVATE_SUBNET_IDS"), "subnet-0b0b482eb3c8d1093,subnet-06871fc0a01b37291").split(",")
prod_public_subnet_ids = os.getenv(_param("PROD_PUBLIC_SUBNET_IDS"), "subnet-006c070eb830ae59d,subnet-0da90f3194a1c76de").split(",")

if not portfolio_access_role_arn:
    raise ValueError("Missing input parameter portfolio-access-role-arn")


app = aws_cdk.App()
stack = ServiceCatalogStack(
    app,
    app_prefix,
    portfolio_name=portfolio_name,
    portfolio_owner=portfolio_owner,
    portfolio_access_role_arn=portfolio_access_role_arn,
    pre_prod_vpcid=pre_prod_vpc_id,
    pre_prod_private_subnetids=pre_prod_private_subnet_ids,
    pre_prod_public_subnetids=pre_prod_public_subnet_ids,
    prod_vpcid=prod_vpc_id,
    prod_private_subnetids=prod_private_subnet_ids,
    prod_public_subnetids=prod_public_subnet_ids,
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
aws_cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))