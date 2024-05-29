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

        os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
        os.environ["SEEDFARMER_PARAMETER_SUBNET_IDS"] = '["subnet-1","subnet-2","subnet-3"]'
        os.environ["SEEDFARMER_PARAMETER_SAGEMAKER_PROJECT_ID"] = "12345"
        os.environ["SEEDFARMER_PARAMETER_SAGEMAKER_PROJECT_NAME"] = "sagemaker-project"
        os.environ["SEEDFARMER_PARAMETER_MODEL_PACKAGE_ARN"] = "example-arn"

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield None


def test_app() -> None:
    import app  # noqa: F401


def test_vpc_id() -> None:
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401
