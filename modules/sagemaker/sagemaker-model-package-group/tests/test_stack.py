import aws_cdk as cdk
from aws_cdk.assertions import Template


def test_synthesize_stack() -> None:
    from sagemaker_model_package_group import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.SagemakerModelPackageGroupStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        model_package_group_name="dummy123",
        retain_on_delete=False,
        target_event_bus_arn="arn:aws:events:xx-xxxxx-xx:xxxxxxxxxxxx:event-bus/default",
        model_package_group_description="dummy123",
        target_account_ids=["dummy123", "321dummy"],
        sagemaker_project_id="id",
        sagemaker_project_name="project-name",
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::Events::Rule", 1)
    template.resource_count_is("AWS::SageMaker::ModelPackageGroup", 1)


def test_synthesize_stack_when_event_bus_not_defined() -> None:
    from sagemaker_model_package_group import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.SagemakerModelPackageGroupStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        model_package_group_name="dummy123",
        retain_on_delete=False,
        model_package_group_description="dummy123",
        target_account_ids=["dummy123", "321dummy"],
        sagemaker_project_id="id",
        sagemaker_project_name="project-name",
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::Events::Rule", 0)
    template.resource_count_is("AWS::SageMaker::ModelPackageGroup", 1)
