import sys

import pytest


@pytest.fixture(scope="function")
def app_defaults(env_defaults):
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(app_defaults):
    import app  # noqa: F401
