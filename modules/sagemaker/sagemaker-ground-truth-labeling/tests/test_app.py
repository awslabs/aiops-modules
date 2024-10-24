# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest import mock

import pytest
from pydantic import ValidationError


@pytest.fixture(scope="function", autouse=True)
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
        os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
        os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        os.environ["SEEDFARMER_PARAMETER_JOB_NAME"] = "job-name"
        os.environ["SEEDFARMER_PARAMETER_TASK_TYPE"] = "image_bounding_box"
        os.environ["SEEDFARMER_PARAMETER_LABELING_WORKTEAM_ARN"] = "labeling-workteam"
        os.environ["SEEDFARMER_PARAMETER_LABELING_CATEGORIES_S3_URI"] = "s3://bucket/labeling-categories"
        os.environ["SEEDFARMER_PARAMETER_LABELING_TASK_TITLE"] = "labeling-title"
        os.environ["SEEDFARMER_PARAMETER_LABELING_TASK_DESCRIPTION"] = "labeling-description"
        os.environ["SEEDFARMER_PARAMETER_LABELING_TASK_KEYWORDS"] = '["labeling-keywords"]'

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield


def test_app() -> None:
    import app  # noqa: F401


def test_job_name() -> None:
    del os.environ["SEEDFARMER_PARAMETER_JOB_NAME"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_task_type() -> None:
    del os.environ["SEEDFARMER_PARAMETER_TASK_TYPE"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_task_type_invalid_value() -> None:
    os.environ["SEEDFARMER_PARAMETER_TASK_TYPE"] = "task_type"

    with pytest.raises(Exception):
        import app  # noqa: F401


def test_labeling_workteam_arn() -> None:
    del os.environ["SEEDFARMER_PARAMETER_LABELING_WORKTEAM_ARN"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_labeling_categories_s3_uri() -> None:
    del os.environ["SEEDFARMER_PARAMETER_LABELING_CATEGORIES_S3_URI"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_labeling_task_title() -> None:
    del os.environ["SEEDFARMER_PARAMETER_LABELING_TASK_TITLE"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_labeling_task_description() -> None:
    del os.environ["SEEDFARMER_PARAMETER_LABELING_TASK_DESCRIPTION"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401


def test_labeling_task_keywords() -> None:
    del os.environ["SEEDFARMER_PARAMETER_LABELING_TASK_KEYWORDS"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401
