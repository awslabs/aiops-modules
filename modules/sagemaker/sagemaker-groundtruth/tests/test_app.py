import os
import sys
from typing import Any

import pytest

@pytest.fixture(scope="function", autouse=True)
def set_env_vars() -> None:
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    if "app" in sys.modules:
        del sys.modules["app"]

def test_app() -> None:
    import app  # noqa: F401