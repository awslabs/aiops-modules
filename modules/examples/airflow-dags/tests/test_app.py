import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["MLOPS_PROJECT_NAME"] = "test-project"
    os.environ["MLOPS_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["MLOPS_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["MLOPS_PARAMETER_MWAA_EXEC_ROLE_ARN"] = "vpc-12345"
    os.environ["MLOPS_PARAMETER_BUCKET_POLICY_ARN"] = "12345"
    os.environ["MLOPS_PERMISSION_BOUNDARY_ARN"] = "sagemaker-project"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401
