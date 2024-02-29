# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    portfolio_name = "portfolio"
    portfolio_owner = "owner"
    portfolio_access_role_arn = "arn:aws:iam::xxxxxxxxxxxx:role/role"

    stack = stack.ServiceCatalogStack(
        app,
        f"{project_name}-{dep_name}-{mod_name}",
        portfolio_name=portfolio_name,
        portfolio_owner=portfolio_owner,
        portfolio_access_role_arn=portfolio_access_role_arn,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(stack)

    template.resource_count_is("AWS::ServiceCatalog::Portfolio", 1)
    template.resource_count_is("AWS::ServiceCatalog::Product", 1)
