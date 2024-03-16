import aws_cdk as cdk
from aws_cdk.assertions import Template


def test_synthesize_stack() -> None:
    from sagemaker_model_package_event import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.SagemakerModelPackageEventStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        target_event_bus_name="dummy123",
        target_account_id="dummy123",
        model_package_group_name="dummy745",
        sagemaker_project_id="id",
        sagemaker_project_name="project-name",
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::Events::Rule", 1)
    template.resource_count_is("AWS::IAM::Role", 2)
