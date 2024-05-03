import os

import pytest


@pytest.fixture(scope="function")
def env_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["SEEDFARMER_PARAMETER_event_bus_name"] = "dummy123"
    os.environ["SEEDFARMER_PARAMETER_source_accounts"] = '["dummy123"]'
    os.environ["SEEDFARMER_PARAMETER_tags"] = '{"dummy321": "dummy321"}'
