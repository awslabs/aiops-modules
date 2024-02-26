import os
import sys
from unittest import mock

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
        os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
        os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
        os.environ["SEEDFARMER_PARAMETER_ECR_REPOSITORY_NAME"] = "repo5"
        os.environ["SEEDFARMER_PARAMETER_ARTIFACTS_BUCKET_NAME"] = "bucket"

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield


def test_app(stack_defaults):
    import app  # noqa: F401


def test_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(ValueError, match="Missing input parameter vpc-id"):
        import app  # noqa: F401


def test_ecr_repository_name(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_ECR_REPOSITORY_NAME"]

    with pytest.raises(ValueError, match="Missing input parameter ecr-repository-name"):
        import app  # noqa: F401


def test_artifacts_bucket_name(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_ARTIFACTS_BUCKET_NAME"]

    with pytest.raises(ValueError, match="Missing input parameter artifacts-bucket-name"):
        import app  # noqa: F401


def test_rds_settings(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_RDS_HOSTNAME"] = "xxxxx"
    os.environ["SEEDFARMER_PARAMETER_RDS_CREDENTIALS_SECRET_ARN"] = (
        "arn:aws:secretsmanager:us-east-1:111111111111:secret:xxxxxx/xxxxxx-yyyyyy"
    )

    import app  # noqa: F401


def test_rds_settings_missing_hostname(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_RDS_CREDENTIALS_SECRET_ARN"] = (
        "arn:aws:secretsmanager:us-east-1:111111111111:secret:xxxxxx/xxxxxx-yyyyyy"
    )

    with pytest.raises(
        ValueError, match="Either both rds-hostname and rds-credentials-secret-arn need to be defined or neither."
    ):
        import app  # noqa: F401


def test_rds_settings_missing_credentials(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_RDS_HOSTNAME"] = "xxxxx"

    with pytest.raises(
        ValueError, match="Either both rds-hostname and rds-credentials-secret-arn need to be defined or neither."
    ):
        import app  # noqa: F401
