# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest

from settings import ModelDeployProjectSettings


class TestModelDeployProjectSettings:
    """Tests for ModelDeployProjectSettings parameter handling."""

    def test_default_values(self) -> None:
        """Test that enable_manual_approval and enable_eventbridge_trigger default to True."""
        settings = ModelDeployProjectSettings(
            model_package_group_name="test-group",
            model_bucket_name="test-bucket",
        )
        assert settings.enable_manual_approval is True
        assert settings.enable_eventbridge_trigger is True
        assert settings.enable_network_isolation is False

    def test_explicit_true_values(self) -> None:
        """Test that explicit True values are accepted."""
        settings = ModelDeployProjectSettings(
            model_package_group_name="test-group",
            model_bucket_name="test-bucket",
            enable_manual_approval=True,
            enable_eventbridge_trigger=True,
        )
        assert settings.enable_manual_approval is True
        assert settings.enable_eventbridge_trigger is True

    def test_explicit_false_values(self) -> None:
        """Test that explicit False values are accepted."""
        settings = ModelDeployProjectSettings(
            model_package_group_name="test-group",
            model_bucket_name="test-bucket",
            enable_manual_approval=False,
            enable_eventbridge_trigger=False,
        )
        assert settings.enable_manual_approval is False
        assert settings.enable_eventbridge_trigger is False

    def test_required_parameters(self) -> None:
        """Test that required parameters raise validation errors when missing."""
        with pytest.raises(ValueError) as excinfo:
            ModelDeployProjectSettings()

        assert "validation error" in str(excinfo.value).lower()

    def test_model_package_group_name_required(self) -> None:
        """Test that model_package_group_name is required."""
        with pytest.raises(ValueError):
            ModelDeployProjectSettings(
                model_bucket_name="test-bucket",
            )

    def test_model_bucket_name_required(self) -> None:
        """Test that model_bucket_name is required."""
        with pytest.raises(ValueError):
            ModelDeployProjectSettings(
                model_package_group_name="test-group",
            )
