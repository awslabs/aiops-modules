# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest
from pydantic import ValidationError


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ["SEEDFARMER_PARAMETER_SUBNET_IDS"] = '["subnet-12345", "subnet-54321"]'
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_subnet_ids(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_SUBNET_IDS"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_auth_mode(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_AUTH_MODE"] = "DUMMY"

    with pytest.raises(ValidationError):
        import app  # noqa: F401

    del os.environ["SEEDFARMER_PARAMETER_AUTH_MODE"]


def test_default_synthesizer(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_QUALIFIER"] = "dummy"
    os.environ["SEEDFARMER_PARAMETER_CLOUD_FORMATION_EXECUTION_ROLE"] = "dummy"
    os.environ["SEEDFARMER_PARAMETER_DEPLOY_ROLE_ARN"] = "dummy"
    os.environ["SEEDFARMER_PARAMETER_FILE_ASSET_PUBLISHING_ROLE_ARN"] = "dummy"
    os.environ["SEEDFARMER_PARAMETER_IMAGE_ASSET_PUBLISHING_ROLE_ARN"] = "dummy"
    os.environ["SEEDFARMER_PARAMETER_LOOKUP_ROLE_ARN"] = "dummy"

    import app as my_app  # noqa: F401
