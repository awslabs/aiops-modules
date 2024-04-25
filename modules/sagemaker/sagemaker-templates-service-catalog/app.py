# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
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

DEFAULT_DEV_VPC_ID = ""
DEFAULT_DEV_SUBNET_IDS = "[]"
DEFAULT_DEV_SECURITY_GROUP_IDS = "[]"

DEFAULT_PRE_PROD_ACCOUNT_ID = ""
DEFAULT_PRE_PROD_REGION = ""
DEFAULT_PRE_PROD_VPC_ID = ""
DEFAULT_PRE_PROD_SUBNET_IDS = "[]"
DEFAULT_PRE_PROD_SECURITY_GROUP_IDS = "[]"

DEFAULT_PROD_ACCOUNT_ID = ""
DEFAULT_PROD_REGION = ""
DEFAULT_PROD_VPC_ID = ""
DEFAULT_PROD_SUBNET_IDS = "[]"
DEFAULT_PROD_SECURITY_GROUP_IDS = "[]"


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

portfolio_name = os.getenv(_param("PORTFOLIO_NAME"), DEFAULT_PORTFOLIO_NAME)
portfolio_owner = os.getenv(_param("PORTFOLIO_OWNER"), DEFAULT_PORTFOLIO_OWNER)
portfolio_access_role_arn = os.getenv(_param("PORTFOLIO_ACCESS_ROLE_ARN"))

dev_vpc_id = os.getenv(_param("DEV_VPC_ID"), DEFAULT_DEV_VPC_ID)
dev_subnet_ids = json.loads(os.getenv(_param("DEV_SUBNET_IDS"), DEFAULT_DEV_SUBNET_IDS))
dev_security_group_ids = json.loads(os.getenv(_param("DEV_SECURITY_GROUP_IDS"), DEFAULT_DEV_SECURITY_GROUP_IDS))

pre_prod_account_id = os.getenv(_param("PRE_PROD_ACCOUNT_ID"), DEFAULT_PRE_PROD_ACCOUNT_ID)
pre_prod_region = os.getenv(_param("PRE_PROD_REGION"), DEFAULT_PRE_PROD_REGION)
pre_prod_vpc_id = os.getenv(_param("PRE_PROD_VPC_ID"), DEFAULT_PRE_PROD_VPC_ID)
pre_prod_subnet_ids = json.loads(os.getenv(_param("PRE_PROD_SUBNET_IDS"), DEFAULT_PRE_PROD_SUBNET_IDS))
pre_prod_security_group_ids = json.loads(
    os.getenv(_param("PRE_PROD_SECURITY_GROUP_IDS"), DEFAULT_PROD_SECURITY_GROUP_IDS)
)

prod_account_id = os.getenv(_param("PROD_ACCOUNT_ID"), DEFAULT_PROD_ACCOUNT_ID)
prod_region = os.getenv(_param("PROD_REGION"), DEFAULT_PROD_REGION)
prod_vpc_id = os.getenv(_param("PROD_VPC_ID"), DEFAULT_PROD_VPC_ID)
prod_subnet_ids = json.loads(os.getenv(_param("PROD_SUBNET_IDS"), DEFAULT_PROD_SUBNET_IDS))
prod_security_group_ids = json.loads(os.getenv(_param("PROD_SECURITY_GROUP_IDS"), DEFAULT_PROD_SECURITY_GROUP_IDS))


if not portfolio_access_role_arn:
    raise ValueError("Missing input parameter portfolio-access-role-arn")


app = aws_cdk.App()
stack = ServiceCatalogStack(
    app,
    app_prefix,
    portfolio_name=portfolio_name,
    portfolio_owner=portfolio_owner,
    portfolio_access_role_arn=portfolio_access_role_arn,
    dev_vpc_id=dev_vpc_id,
    dev_subnet_ids=dev_subnet_ids,
    dev_security_group_ids=dev_security_group_ids,
    pre_prod_account_id=pre_prod_account_id,
    pre_prod_region=pre_prod_region,
    pre_prod_vpc_id=pre_prod_vpc_id,
    pre_prod_subnet_ids=pre_prod_subnet_ids,
    pre_prod_security_group_ids=pre_prod_security_group_ids,
    prod_account_id=prod_account_id,
    prod_region=prod_region,
    prod_vpc_id=prod_vpc_id,
    prod_subnet_ids=prod_subnet_ids,
    prod_security_group_ids=prod_security_group_ids,
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

aws_cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

app.synth()
