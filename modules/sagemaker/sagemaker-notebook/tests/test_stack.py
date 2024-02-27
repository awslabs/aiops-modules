import aws_cdk as cdk
from aws_cdk.assertions import Template


def test_synthesize_stack() -> None:
    from sagemaker_notebook import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.SagemakerNotebookStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        notebook_name="dummy123",
        instance_type="dummy123",
        direct_internet_access="Enabled",
        root_access="Enabled",
        volume_size_in_gb=8,
        imds_version="1",
        subnet_id="subnet-id-123123",
        vpc_id="vpc-12345",
        kms_key_arn="arn:aws:kms:*:*:*",
        code_repository="https://",
        additional_code_repositories=["https://", "https://", "https://"],
        role_arn="arn:aws:iam::*:role/*",
        tags={"test": "True"},
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::NotebookInstance", 1)
