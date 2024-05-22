import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


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
    vpc_id = "vpc-123"
    cognito_pool_id = "us-east-1_XXXXX"
    os_domain_endpoint = "sample-endpoint.com"
    os_security_group_id = "sg-a1b2c3d4"

    return stack.RAGResources(
        scope=app,
        id=app_prefix,
        vpc_id=vpc_id,
        cognito_pool_id=cognito_pool_id,
        os_domain_endpoint=os_domain_endpoint,
        os_security_group_id=os_security_group_id,
        os_index_name="sample",
        input_asset_bucket_name="input-bucket",
        env=cdk.Environment(
            account="111111111111",
            region="us-east-1",
        ),
    )


@pytest.fixture(params=["stack_model_package_input"], scope="function")
def stack(request, stack_model_package_input) -> cdk.Stack:  # type: ignore[no-untyped-def]
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


def test_synthesize_stack(stack: cdk.Stack) -> None:
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::AppSync::Resolver", 4)
