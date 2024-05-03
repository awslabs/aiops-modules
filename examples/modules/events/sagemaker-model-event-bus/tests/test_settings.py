import os

import pytest

from sagemaker_model_event_bus.settings import ApplicationSettings


def test_settings_inputs(env_defaults) -> None:
    settings = ApplicationSettings()

    project_name = os.environ["SEEDFARMER_PROJECT_NAME"]
    deployment_name = os.environ["SEEDFARMER_DEPLOYMENT_NAME"]
    module_name = os.environ["SEEDFARMER_MODULE_NAME"]
    prefix = f"{project_name}-{deployment_name}-{module_name}"

    assert settings.settings.app_prefix == prefix

    account = os.environ["CDK_DEFAULT_ACCOUNT"]
    assert settings.default.account == account


def test_settings_required_parameters(env_defaults) -> None:
    del os.environ["SEEDFARMER_PARAMETER_event_bus_name"]

    with pytest.raises(ValueError) as excinfo:
        ApplicationSettings()

    assert "1 validation error for SeedFarmerParameters" in str(excinfo.value)
