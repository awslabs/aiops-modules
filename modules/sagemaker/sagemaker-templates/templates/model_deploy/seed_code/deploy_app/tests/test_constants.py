# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest import mock

import pytest


@pytest.fixture(scope="function")
def clean_constants_module():
    """Remove cached constants module to ensure fresh imports with mocked env vars."""
    modules_to_remove = [k for k in sys.modules if k.startswith("config")]
    for mod in modules_to_remove:
        del sys.modules[mod]

    yield

    modules_to_remove = [k for k in sys.modules if k.startswith("config")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture(scope="function")
def base_env_vars():
    """Base environment variables required for constants module to load."""
    return {
        "DEV_ACCOUNT_ID": "111111111111",
        "DEV_REGION": "us-east-1",
        "DEV_VPC_ID": "vpc-dev",
        "DEV_SUBNET_IDS": '["subnet-dev"]',
        "DEV_SECURITY_GROUP_IDS": '["sg-dev"]',
        "MODEL_BUCKET_ARN": "arn:aws:s3:::test-bucket",
    }


# Tests for get_env_with_fallback helper function


def test_get_env_with_fallback_returns_value_when_set(clean_constants_module, base_env_vars):
    """Should return the environment variable value when it's set."""
    with mock.patch.dict(os.environ, {**base_env_vars, "TEST_VAR": "test_value"}, clear=True):
        from config.constants import get_env_with_fallback

        result = get_env_with_fallback("TEST_VAR", "fallback")
        assert result == "test_value"


def test_get_env_with_fallback_returns_fallback_when_not_set(clean_constants_module, base_env_vars):
    """Should return fallback when environment variable is not set."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        from config.constants import get_env_with_fallback

        result = get_env_with_fallback("TEST_VAR", "fallback")
        assert result == "fallback"


def test_get_env_with_fallback_returns_fallback_when_empty_string(clean_constants_module, base_env_vars):
    """Should return fallback when environment variable is empty string."""
    with mock.patch.dict(os.environ, {**base_env_vars, "TEST_VAR": ""}, clear=True):
        from config.constants import get_env_with_fallback

        result = get_env_with_fallback("TEST_VAR", "fallback")
        assert result == "fallback"


def test_get_env_with_fallback_parses_json_list(clean_constants_module, base_env_vars):
    """Should parse JSON list when is_json_list=True."""
    with mock.patch.dict(os.environ, {**base_env_vars, "TEST_LIST": '["a", "b", "c"]'}, clear=True):
        from config.constants import get_env_with_fallback

        result = get_env_with_fallback("TEST_LIST", ["default"], is_json_list=True)
        assert result == ["a", "b", "c"]


def test_get_env_with_fallback_json_list_fallback_when_empty(clean_constants_module, base_env_vars):
    """Should return fallback when JSON list is empty."""
    with mock.patch.dict(os.environ, {**base_env_vars, "TEST_LIST": "[]"}, clear=True):
        from config.constants import get_env_with_fallback

        result = get_env_with_fallback("TEST_LIST", ["default"], is_json_list=True)
        assert result == ["default"]


def test_get_env_with_fallback_warns_when_enabled(clean_constants_module, base_env_vars, capsys):
    """Should print warning when warn=True and fallback is used."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        from config.constants import get_env_with_fallback

        get_env_with_fallback("TEST_VAR", "fallback", warn=True)
        captured = capsys.readouterr()
        assert "INFO: TEST_VAR not provided, using fallback" in captured.out


def test_get_env_with_fallback_no_warning_by_default(clean_constants_module, base_env_vars, capsys):
    """Should not print warning when warn=False (default)."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        from config.constants import get_env_with_fallback

        # Clear any output from module load (PRE_PROD/PROD fallback warnings)
        capsys.readouterr()

        get_env_with_fallback("TEST_VAR", "fallback")
        captured = capsys.readouterr()
        assert "TEST_VAR" not in captured.out


# Tests for PRE_PROD/PROD fallback behavior


def test_preprod_falls_back_to_dev_when_not_set(clean_constants_module, base_env_vars):
    """PRE_PROD should use DEV values when not provided."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        import config.constants as constants

        assert constants.PRE_PROD_ACCOUNT_ID == "111111111111"
        assert constants.PRE_PROD_REGION == "us-east-1"
        assert constants.PRE_PROD_VPC_ID == "vpc-dev"
        assert constants.PRE_PROD_SUBNET_IDS == ["subnet-dev"]
        assert constants.PRE_PROD_SECURITY_GROUP_IDS == ["sg-dev"]


def test_prod_falls_back_to_dev_when_not_set(clean_constants_module, base_env_vars):
    """PROD should use DEV values when not provided."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        import config.constants as constants

        assert constants.PROD_ACCOUNT_ID == "111111111111"
        assert constants.PROD_REGION == "us-east-1"
        assert constants.PROD_VPC_ID == "vpc-dev"
        assert constants.PROD_SUBNET_IDS == ["subnet-dev"]
        assert constants.PROD_SECURITY_GROUP_IDS == ["sg-dev"]


def test_preprod_uses_own_values_when_set(clean_constants_module, base_env_vars):
    """PRE_PROD should use its own values when provided."""
    env = {
        **base_env_vars,
        "PRE_PROD_ACCOUNT_ID": "222222222222",
        "PRE_PROD_REGION": "us-west-2",
        "PRE_PROD_VPC_ID": "vpc-preprod",
        "PRE_PROD_SUBNET_IDS": '["subnet-preprod"]',
        "PRE_PROD_SECURITY_GROUP_IDS": '["sg-preprod"]',
    }
    with mock.patch.dict(os.environ, env, clear=True):
        import config.constants as constants

        assert constants.PRE_PROD_ACCOUNT_ID == "222222222222"
        assert constants.PRE_PROD_REGION == "us-west-2"
        assert constants.PRE_PROD_VPC_ID == "vpc-preprod"
        assert constants.PRE_PROD_SUBNET_IDS == ["subnet-preprod"]
        assert constants.PRE_PROD_SECURITY_GROUP_IDS == ["sg-preprod"]


def test_prod_uses_own_values_when_set(clean_constants_module, base_env_vars):
    """PROD should use its own values when provided."""
    env = {
        **base_env_vars,
        "PROD_ACCOUNT_ID": "333333333333",
        "PROD_REGION": "eu-west-1",
        "PROD_VPC_ID": "vpc-prod",
        "PROD_SUBNET_IDS": '["subnet-prod"]',
        "PROD_SECURITY_GROUP_IDS": '["sg-prod"]',
    }
    with mock.patch.dict(os.environ, env, clear=True):
        import config.constants as constants

        assert constants.PROD_ACCOUNT_ID == "333333333333"
        assert constants.PROD_REGION == "eu-west-1"
        assert constants.PROD_VPC_ID == "vpc-prod"
        assert constants.PROD_SUBNET_IDS == ["subnet-prod"]
        assert constants.PROD_SECURITY_GROUP_IDS == ["sg-prod"]


def test_empty_string_treated_as_not_set(clean_constants_module, base_env_vars):
    """Empty string values should fall back to DEV."""
    env = {
        **base_env_vars,
        "PRE_PROD_ACCOUNT_ID": "",
        "PRE_PROD_REGION": "",
        "PROD_ACCOUNT_ID": "",
        "PROD_REGION": "",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        import config.constants as constants

        assert constants.PRE_PROD_ACCOUNT_ID == "111111111111"
        assert constants.PRE_PROD_REGION == "us-east-1"
        assert constants.PROD_ACCOUNT_ID == "111111111111"
        assert constants.PROD_REGION == "us-east-1"


def test_warns_for_account_and_region_fallback(clean_constants_module, base_env_vars, capsys):
    """Should print warnings when ACCOUNT_ID and REGION fall back."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        import config.constants  # noqa: F401

        captured = capsys.readouterr()
        assert "PRE_PROD_ACCOUNT_ID not provided" in captured.out
        assert "PRE_PROD_REGION not provided" in captured.out
        assert "PROD_ACCOUNT_ID not provided" in captured.out
        assert "PROD_REGION not provided" in captured.out


def test_no_warning_for_vpc_subnet_sg_fallback(clean_constants_module, base_env_vars, capsys):
    """Should NOT print warnings when VPC/subnet/SG fall back."""
    with mock.patch.dict(os.environ, base_env_vars, clear=True):
        import config.constants  # noqa: F401

        captured = capsys.readouterr()
        assert "VPC_ID not provided" not in captured.out
        assert "SUBNET_IDS not provided" not in captured.out
        assert "SECURITY_GROUP_IDS not provided" not in captured.out
