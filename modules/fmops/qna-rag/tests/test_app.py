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
        os.environ["SEEDFARMER_PARAMETER_COGNITO_POOL_ID"] = "12345"
        os.environ["SEEDFARMER_PARAMETER_OS_DOMAIN_ENDPOINT"] = "sample-endpoint.com"
        os.environ["SEEDFARMER_PARAMETER_OS_SECURITY_GROUP_ID"] = "sg-1234abcd"

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield


def test_app():
    import app  # noqa: F401


def test_vpc_id():
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_cognito_pool_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_COGNITO_POOL_ID"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_os_domain_endpoint(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_OS_DOMAIN_ENDPOINT"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_os_security_group(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_OS_SECURITY_GROUP_ID"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401
