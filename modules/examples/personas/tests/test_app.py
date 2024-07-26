import os
import sys
from typing import Any

import pytest
from pydantic import ValidationError


@pytest.fixture(scope="function", autouse=True)
def stack_defaults() -> None:
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

    os.environ["SEEDFARMER_PARAMETER_BUCKET_NAME"] = "test-bucket"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app() -> None:
    import app  # noqa: F401


def test_bucket_name(stack_defaults: Any) -> None:
    del os.environ["SEEDFARMER_PARAMETER_BUCKET_NAME"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401
