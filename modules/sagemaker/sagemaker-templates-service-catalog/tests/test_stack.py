# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest import mock

import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        # Unload the app import so that subsequent tests don't reuse

        if "stack" in sys.modules:
            del sys.modules["stack"]

        yield


@pytest.fixture(scope="function")
def stack(stack_defaults) -> cdk.Stack:
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    portfolio_name = "portfolio"
    portfolio_owner = "owner"
    portfolio_access_role_arn = "arn:aws:iam::xxxxxxxxxxxx:role/role"
    dev_vpc_id = "vpc"
    dev_subnet_ids = ["sub"]
    dev_security_group_ids = ["sg"]
    pre_prod_account_id = "pre_prod_account_id"
    pre_prod_region = "us-east-1"
    pre_prod_vpc_id = "vpc"
    pre_prod_subnet_ids = ["sub"]
    pre_prod_security_group_ids = ["sg"]
    prod_account_id = "prod_account_id"
    prod_region = "us-east-1"
    prod_vpc_id = "vpc"
    prod_subnet_ids = ["sub"]
    prod_security_group_ids = ["sg"]

    return stack.ServiceCatalogStack(
        app,
        f"{project_name}-{dep_name}-{mod_name}",
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
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


def test_synthesize_stack(stack: cdk.Stack) -> None:
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::ServiceCatalog::Portfolio", 1)
    template.resource_count_is("AWS::ServiceCatalog::CloudFormationProduct", 4)


def test_no_cdk_nag_errors(stack: cdk.Stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
