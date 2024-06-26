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
    if "sagemaker_model_monitoring" in sys.modules:
        del sys.modules["sagemaker_model_monitoring"]


def stack_model_package_input(
    enable_data_quality_monitor: bool = False,
    enable_model_quality_monitor: bool = False,
    enable_model_bias_monitor: bool = False,
    enable_model_explainability_monitor: bool = False,
) -> cdk.Stack:
    from sagemaker_model_monitoring import settings, stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    sagemaker_project_id = "12345"
    sagemaker_project_name = "sagemaker-project"
    endpoint_name = "example-endpoint-name"
    security_group_id = "example-security-group-id"
    model_package_arn = "example-package-arn"
    model_bucket_arn = "arn:aws:s3:::test-bucket"
    kms_key_id = "example-kms-key-id"

    # Instantiate a settings object to avoid needing to pass default parameters.
    app_settings = settings.ModuleSettings(
        sagemaker_project_id=sagemaker_project_id,
        sagemaker_project_name=sagemaker_project_name,
        endpoint_name=endpoint_name,
        security_group_id=security_group_id,
        subnet_ids=[],
        model_package_arn=model_package_arn,
        model_bucket_arn=model_bucket_arn,
        kms_key_id=kms_key_id,
        enable_data_quality_monitor=enable_data_quality_monitor,
        enable_model_quality_monitor=enable_model_quality_monitor,
        enable_model_bias_monitor=enable_model_bias_monitor,
        enable_model_explainability_monitor=enable_model_explainability_monitor,
    )

    return stack.SageMakerModelMonitoringStack(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        **app_settings.model_dump(),
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


def test_synthesize_stack_data_quality(stack_defaults: None) -> None:
    stack = stack_model_package_input(enable_data_quality_monitor=True)
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::DataQualityJobDefinition", 1)


def test_synthesize_stack_model_quality(stack_defaults: None) -> None:
    stack = stack_model_package_input(enable_model_quality_monitor=True)
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::ModelQualityJobDefinition", 1)


def test_synthesize_stack_model_bias(stack_defaults: None) -> None:
    stack = stack_model_package_input(enable_model_bias_monitor=True)
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::ModelBiasJobDefinition", 1)


def test_synthesize_stack_model_explainability(stack_defaults: None) -> None:
    stack = stack_model_package_input(enable_model_explainability_monitor=True)
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::ModelExplainabilityJobDefinition", 1)


def test_no_cdk_nag_errors(stack_defaults: None) -> None:
    stack = stack_model_package_input(
        enable_data_quality_monitor=True,
        enable_model_quality_monitor=True,
        enable_model_bias_monitor=True,
        enable_model_explainability_monitor=True,
    )
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
