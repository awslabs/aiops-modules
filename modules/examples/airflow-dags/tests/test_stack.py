import os
import sys

import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def stack_defaults() -> None:
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse
    if "stack" in sys.modules:
        del sys.modules["stack"]


@pytest.fixture(scope="function")
def stack_model_package_input() -> cdk.Stack:
    import stack

    app = cdk.App()

    project_name = "test-project"
    deployment_name = "test-deployment"
    module_name = "test-module"

    app_prefix = f"{project_name}-{deployment_name}-{module_name}"
    mwaa_exec_role = "arn:aws:iam::123456789012:role/mwaarole"
    bucket_policy_arn = "arn:aws:iam::123456789012:policy/bucketPolicy"
    permission_boundary_arn = "arn:aws:iam::123456789012:policy/boundary"

    return stack.DagResources(
        scope=app,
        id=app_prefix,
        project_name=project_name,
        deployment_name=deployment_name,
        module_name=module_name,
        mwaa_exec_role=mwaa_exec_role,
        bucket_policy_arn=bucket_policy_arn,
        permission_boundary_arn=permission_boundary_arn,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


@pytest.fixture(params=["stack_model_package_input"], scope="function")
def stack(request, stack_model_package_input) -> cdk.Stack:
    return request.getfixturevalue(request.param)


def test_synthesize_stack(stack: cdk.Stack) -> None:
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::S3::Bucket", 1)


def test_no_cdk_nag_errors(stack: cdk.Stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
