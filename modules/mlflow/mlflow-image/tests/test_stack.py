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
def stack(stack_defaults) -> cdk.Stack:
    import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    ecr_repo_name = "repo"

    return stack.MlflowImagePublishingStack(
        scope=app,
        id=app_prefix,
        app_prefix=app_prefix,
        ecr_repo_name=ecr_repo_name,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


def test_synthesize_stack(stack: cdk.Stack) -> None:
    template = Template.from_stack(stack)
    template.resource_count_is("Custom::CDKBucketDeployment", 1)


def test_no_cdk_nag_errors(stack: cdk.Stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
