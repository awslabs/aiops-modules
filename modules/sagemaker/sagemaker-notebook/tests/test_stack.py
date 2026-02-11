import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def stack() -> cdk.Stack:
    from sagemaker_notebook import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"
    permissions_boundary_name = None

    return stack.SagemakerNotebookStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        notebook_name="dummy123",
        instance_type="dummy123",
        direct_internet_access="Enabled",
        root_access="Enabled",
        volume_size_in_gb=8,
        imds_version="1",
        subnet_ids=["subnet-id-a", "subnet-id-b"],
        vpc_id="vpc-12345",
        kms_key_arn="arn:aws:kms:*:*:*",
        code_repository="https://",
        additional_code_repositories=["https://", "https://", "https://"],
        role_arn="arn:aws:iam::*:role/*",
        tags={"test": "True"},
        permissions_boundary_name=permissions_boundary_name,
    )


def test_synthesize_stack(stack) -> None:
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::NotebookInstance", 1)


def test_no_cdk_nag_errors(stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
