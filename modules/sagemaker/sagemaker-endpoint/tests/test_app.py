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

    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ["SEEDFARMER_PARAMETER_SAGEMAKER_PROJECT_ID"] = "12345"
    os.environ["SEEDFARMER_PARAMETER_SAGEMAKER_PROJECT_NAME"] = "sagemaker-project"
    os.environ["SEEDFARMER_PARAMETER_MODEL_PACKAGE_ARN"] = "example-arn"
    os.environ["SEEDFARMER_PARAMETER_MODEL_BUCKET_ARN"] = "arn:aws:s3:::test-bucket"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(Exception, match="Missing input parameter vpc-id"):
        import app  # noqa: F401
