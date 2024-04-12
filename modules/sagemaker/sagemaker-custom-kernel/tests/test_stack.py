# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse

    if "stack" in sys.modules:
        del sys.modules["stack"]


@pytest.fixture(scope="function")
def stack(stack_defaults) -> cdk.Stack:
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"
    sagemaker_image_name = "echo-kernel"
    ecr_repo_name = "repo"
    app_image_config_name = "conf"
    custom_kernel_name = "echo-kernel"
    kernel_user_uid = 1000
    kernel_user_gid = 100
    mount_path = "/root"

    return stack.CustomKernelStack(
        app,
        app_prefix,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
        app_prefix=app_prefix,
        sagemaker_image_name=sagemaker_image_name,
        ecr_repo_name=ecr_repo_name,
        app_image_config_name=app_image_config_name,
        custom_kernel_name=custom_kernel_name,
        kernel_user_uid=int(kernel_user_uid),
        kernel_user_gid=int(kernel_user_gid),
        mount_path=mount_path,
    )


def test_synthesize_stack(stack: cdk.Stack) -> None:
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::IAM::Role", 2)
    template.resource_count_is("AWS::SageMaker::Image", 1)
    template.resource_count_is("AWS::SageMaker::ImageVersion", 1)
    template.resource_count_is("AWS::SageMaker::AppImageConfig", 1)


def test_no_cdk_nag_errors(stack: cdk.Stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
