# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["SEEDFARMER_PARAMETER_PORTFOLIO_ACCESS_ROLE_ARN"] = "arn:aws:iam::xxxxxxxxxxxx:role/role"
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_portfolio_access_role(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_PORTFOLIO_ACCESS_ROLE_ARN"]

    with pytest.raises(Exception, match="Missing input parameter portfolio-access-role-arn"):
        import app  # noqa: F401
