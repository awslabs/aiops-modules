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

    return stack.MLOPSSFNResources(
        scope=app,
        id=app_prefix,
        project_name=project_name,
        deployment_name=deployment_name,
        module_name=module_name,
        model_name="demo",
        schedule="0 6 * * ? *",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


@pytest.fixture(params=["stack_model_package_input"], scope="function")
def stack(request, stack_model_package_input) -> cdk.Stack:  # type: ignore[no-untyped-def]
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


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
