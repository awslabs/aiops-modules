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

    os.environ["SEEDFARMER_PARAMETER_BUCKET_POLICY_ARN"] = "12345"
    os.environ["SEEDFARMER_PERMISSION_BOUNDARY_ARN"] = "sagemaker-project"

    os.environ["SEEDFARMER_PARAMETER_SCHEDULE"] = "0 6 * * ? *"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):  # type: ignore[no-untyped-def]
    import app  # noqa: F401
