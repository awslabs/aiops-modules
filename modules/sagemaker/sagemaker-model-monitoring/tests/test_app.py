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

    os.environ["SEEDFARMER_PARAMETER_SAGEMAKER_PROJECT_ID"] = "12345"
    os.environ["SEEDFARMER_PARAMETER_SAGEMAKER_PROJECT_NAME"] = "sagemaker-project"
    os.environ["SEEDFARMER_PARAMETER_SECURITY_GROUP_ID"] = "example-security-group-id"
    os.environ["SEEDFARMER_PARAMETER_SUBNET_IDS"] = "[]"
    os.environ["SEEDFARMER_PARAMETER_ENDPOINT_NAME"] = "example-endpoint-name"
    os.environ["SEEDFARMER_PARAMETER_MODEL_BUCKET_ARN"] = "example-bucket-arn"
    os.environ["SEEDFARMER_PARAMETER_KMS_KEY_ID"] = "example-kms-key-id"

    os.environ["SEEDFARMER_PARAMETER_ENABLE_DATA_QUALITY_MONITOR"] = "true"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_all_disabled(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_ENABLE_DATA_QUALITY_MONITOR"] = "false"
    os.environ["SEEDFARMER_PARAMETER_ENABLE_MODEL_QUALITY_MONITOR"] = "false"
    os.environ["SEEDFARMER_PARAMETER_ENABLE_MODEL_BIAS_MONITOR"] = "false"
    os.environ["SEEDFARMER_PARAMETER_ENABLE_MODEL_EXPLAINABILITY_MONITOR"] = "false"

    with pytest.raises(Exception, match="At least one of enable_data_quality_monitor, .+ must be True"):
        import app  # noqa: F401
