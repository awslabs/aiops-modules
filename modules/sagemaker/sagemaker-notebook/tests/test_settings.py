import os
from unittest import mock

import pytest

from sagemaker_notebook.settings import ApplicationSettings


@pytest.fixture(scope="function")
def env_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["SEEDFARMER_PARAMETER_NOTEBOOK_NAME"] = "dummy123"
    os.environ["SEEDFARMER_PARAMETER_INSTANCE_TYPE"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_DIRECT_INTERNET_ACCESS"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_ROOT_ACCESS"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_VOLUME_SIZE_IN_GB"] = "20"
    os.environ["SEEDFARMER_PARAMETER_IMDS_VERSION"] = "2"
    os.environ["SEEDFARMER_PARAMETER_SUBNET_ID"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_CODE_REPOSITORY"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_ADDITIONAL_CODE_REPOSITORIES"] = '["dummy321", "dummy321"]'
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_KMS_KEY_ARN"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_ROLE_ARN"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_TAGS"] = '{"dummy321": "dummy321"}'


@mock.patch("time.time")
def test_settings_inputs(mock_time, env_defaults) -> None:
    mock_time.return_value = 1234567

    settings = ApplicationSettings()

    nb_name = os.environ["SEEDFARMER_PARAMETER_NOTEBOOK_NAME"]
    assert settings.parameters.notebook_name == f"{nb_name}-1234567"

    project_name = os.environ["SEEDFARMER_PROJECT_NAME"]
    deployment_name = os.environ["SEEDFARMER_DEPLOYMENT_NAME"]
    module_name = os.environ["SEEDFARMER_MODULE_NAME"]
    prefix = f"{project_name}-{deployment_name}-{module_name}"
    assert settings.settings.app_prefix == prefix

    account = os.environ["CDK_DEFAULT_ACCOUNT"]
    assert settings.default.account == account


@mock.patch("time.time")
def test_settings_nb_name_parameter_length(mock_time, env_defaults) -> None:
    n = 60
    nb_name = "a" * n
    os.environ["SEEDFARMER_PARAMETER_NOTEBOOK_NAME"] = nb_name

    with pytest.raises(ValueError, match=f"'name' length must be <= 50, got '{n}'"):
        ApplicationSettings()

    n = 50
    nb_name = "a" * n
    mock_time.return_value = 1234567
    os.environ["SEEDFARMER_PARAMETER_NOTEBOOK_NAME"] = nb_name
    settings = ApplicationSettings()

    assert settings.parameters.notebook_name == f"{nb_name}-1234567"


def test_settings_required_parameters(env_defaults) -> None:
    del os.environ["SEEDFARMER_PARAMETER_NOTEBOOK_NAME"]
    del os.environ["SEEDFARMER_PARAMETER_INSTANCE_TYPE"]

    with pytest.raises(ValueError) as excinfo:
        ApplicationSettings()

    assert "2 validation errors for SeedFarmerParameters" in str(excinfo.value)
