# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest import mock

import pytest
from pydantic import ValidationError


@pytest.fixture(scope="function", autouse=True)
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
        os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
        os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        os.environ["SEEDFARMER_PARAMETER_PORTFOLIO_ACCESS_ROLE_ARN"] = "arn:aws:iam::xxxxxxxxxxxx:role/role"

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield


def test_app() -> None:
    import app  # noqa: F401


def test_portfolio_access_role() -> None:
    del os.environ["SEEDFARMER_PARAMETER_PORTFOLIO_ACCESS_ROLE_ARN"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401
