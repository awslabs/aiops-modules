# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import ServiceCatalogStack

app = aws_cdk.App()
app_settings = ApplicationSettings()

stack = ServiceCatalogStack(
    app,
    app_settings.seedfarmer_settings.app_prefix,
    portfolio_name=app_settings.module_settings.portfolio_name,
    portfolio_owner=app_settings.module_settings.portfolio_owner,
    portfolio_access_role_arn=app_settings.module_settings.portfolio_access_role_arn,
    dev_vpc_id=app_settings.module_settings.dev_vpc_id,
    dev_subnet_ids=app_settings.module_settings.dev_subnet_ids,
    dev_security_group_ids=app_settings.module_settings.dev_security_group_ids,
    pre_prod_account_id=app_settings.module_settings.pre_prod_account_id,
    pre_prod_region=app_settings.module_settings.pre_prod_region,
    pre_prod_vpc_id=app_settings.module_settings.pre_prod_vpc_id,
    pre_prod_subnet_ids=app_settings.module_settings.pre_prod_subnet_ids,
    pre_prod_security_group_ids=app_settings.module_settings.pre_prod_security_group_ids,
    prod_account_id=app_settings.module_settings.prod_account_id,
    prod_region=app_settings.module_settings.prod_region,
    prod_vpc_id=app_settings.module_settings.prod_vpc_id,
    prod_subnet_ids=app_settings.module_settings.prod_subnet_ids,
    prod_security_group_ids=app_settings.module_settings.prod_security_group_ids,
    env=aws_cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
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

if app_settings.module_settings.tags:
    for tag_key, tag_value in app_settings.module_settings.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth()
