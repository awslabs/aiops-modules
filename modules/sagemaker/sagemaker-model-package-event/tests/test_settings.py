import os

import pytest

from sagemaker_model_package_event.settings import ApplicationSettings


@pytest.fixture(scope="function")
def env_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["SEEDFARMER_PARAMETER_model_package_group_name"] = "dummy123"
    os.environ["SEEDFARMER_PARAMETER_target_event_bus_name"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_target_account_id"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_sagemaker_project_id"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_sagemaker_project_name"] = "dummy321"


def test_settings_inputs(env_defaults) -> None:
    settings = ApplicationSettings()

    assert settings.parameters.target_account_id == "dummy321"

    project_name = os.environ["SEEDFARMER_PROJECT_NAME"]
    deployment_name = os.environ["SEEDFARMER_DEPLOYMENT_NAME"]
    module_name = os.environ["SEEDFARMER_MODULE_NAME"]
    prefix = f"{project_name}-{deployment_name}-{module_name}"

    assert settings.settings.app_prefix == prefix

    account = os.environ["CDK_DEFAULT_ACCOUNT"]
    assert settings.default.account == account


def test_settings_required_parameters(env_defaults) -> None:
    del os.environ["SEEDFARMER_PARAMETER_target_event_bus_name"]
    del os.environ["SEEDFARMER_PARAMETER_target_account_id"]
    del os.environ["SEEDFARMER_PARAMETER_model_package_group_name"]

    with pytest.raises(ValueError) as excinfo:
        ApplicationSettings()

    assert "3 validation errors for SeedFarmerParameters" in str(excinfo.value)
