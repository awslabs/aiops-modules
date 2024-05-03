import os
from unittest import mock

import pytest

from sagemaker_model_package_promote_pipeline.settings import ApplicationSettings


@pytest.fixture(scope="function")
def env_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["SEEDFARMER_PARAMETER_source_model_package_group_arn"] = (
        "arn:aws:sagemaker:us-east-1:111111111111:model-package-group/dummy123"
    )
    os.environ["SEEDFARMER_PARAMETER_target_bucket_name"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_event_bus_name"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_target_model_package_group_name"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_sagemaker_project_id"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_sagemaker_project_name"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_kms_key_arn"] = (
        "arn:aws:xxx:us-east-1:111111111111:xxx/asd2313-asdx-123-xa-asdasd12334123"
    )
    os.environ["SEEDFARMER_PARAMETER_retain_on_delete"] = "False"


@mock.patch("time.time")
def test_settings_inputs(mock_time, env_defaults) -> None:
    mock_time.return_value = 1234567

    settings = ApplicationSettings()

    param_value = os.environ["SEEDFARMER_PARAMETER_source_model_package_group_arn"]
    assert settings.parameters.source_model_package_group_arn == param_value

    project_name = os.environ["SEEDFARMER_PROJECT_NAME"]
    deployment_name = os.environ["SEEDFARMER_DEPLOYMENT_NAME"]
    module_name = os.environ["SEEDFARMER_MODULE_NAME"]
    prefix = f"{project_name}-{deployment_name}-{module_name}"
    assert settings.settings.app_prefix == prefix

    account = os.environ["CDK_DEFAULT_ACCOUNT"]
    assert settings.default.account == account


def test_settings_required_parameters(env_defaults) -> None:
    del os.environ["SEEDFARMER_PARAMETER_source_model_package_group_arn"]
    del os.environ["SEEDFARMER_PARAMETER_target_bucket_name"]

    with pytest.raises(ValueError) as excinfo:
        ApplicationSettings()

    assert "2 validation errors for SeedFarmerParameters" in str(excinfo.value)
