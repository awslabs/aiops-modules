import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults() -> None:
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ["SEEDFARMER_PARAMETER_COGNITO_POOL_ID"] = "12345"
    os.environ["SEEDFARMER_PARAMETER_OS_DOMAIN_ENDPOINT"] = "sample-endpoint.com"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):  # type: ignore[no-untyped-def]
    import app  # noqa: F401


def test_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(ValueError, match="Missing input parameter vpc-id"):
        import app  # noqa: F401


def test_cognito_pool_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_COGNITO_POOL_ID"]

    with pytest.raises(ValueError, match="Missing input parameter cognito-pool-id"):
        import app  # noqa: F401


def test_os_domain_endpoint(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_OS_DOMAIN_ENDPOINT"]

    with pytest.raises(ValueError, match="Missing input parameter os-domain-endpoint"):
        import app  # noqa: F401
