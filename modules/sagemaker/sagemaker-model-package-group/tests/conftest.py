import os

import pytest


@pytest.fixture(scope="function")
def env_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["SEEDFARMER_PARAMETER_model_package_group_name"] = "dummy123"
    os.environ["SEEDFARMER_PARAMETER_retain_on_delete"] = "False"
    os.environ[
        "SEEDFARMER_PARAMETER_target_event_bus_arn"
    ] = "arn:aws:events:xx-xxxxx-xx:xxxxxxxxxxxx:event-bus/default"
    os.environ["SEEDFARMER_PARAMETER_model_package_group_description"] = "dummy123"
    os.environ["SEEDFARMER_PARAMETER_target_account_ids"] = '["dummy123"]'
    os.environ["SEEDFARMER_PARAMETER_sagemaker_project_id"] = "dummy321"
    os.environ["SEEDFARMER_PARAMETER_sagemaker_project_name"] = "dummy321"
