import aws_cdk as cdk
from aws_cdk.assertions import Template


def test_synthesize_stack() -> None:
    from sagemaker_model_package_promote_pipeline import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.SagemakerModelPackagePipelineStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        source_model_package_group_arn="arn:aws:sagemaker:us-east-1:111111111111:model-package-group/dummy123",
        target_bucket_name="dummy123",
        event_bus_name="dummy123",
        target_model_package_group_name="dummy123",
        sagemaker_project_id="dummy123",
        sagemaker_project_name="dummy123",
        kms_key_arn="arn:aws:xxx:us-east-1:111111111111:xxx/asd2313-asdx-123-xa-asdasd12334123",
        retain_on_delete=False,
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)
    template.resource_count_is("AWS::Events::Rule", 1)


def test_synthesize_stack_without_eventbus() -> None:
    from sagemaker_model_package_promote_pipeline import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    stack = stack.SagemakerModelPackagePipelineStack(
        scope=app,
        construct_id=app_prefix,
        env=cdk.Environment(account="111111111111", region="us-east-1"),
        source_model_package_group_arn="arn:aws:sagemaker:us-east-1:111111111111:model-package-group/dummy123",
        target_bucket_name="dummy123",
    )

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)
    template.resource_count_is("AWS::Events::Rule", 0)
