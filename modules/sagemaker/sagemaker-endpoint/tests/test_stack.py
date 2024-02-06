import os
import sys
from unittest import mock

import aws_cdk as cdk
import botocore.session
import pytest
from aws_cdk.assertions import Template
from botocore.stub import Stubber


@pytest.fixture(scope="function")
def stack_defaults() -> None:
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse
    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack_model_package_input() -> None:
    import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    sagemaker_project_id = "12345"
    sagemaker_project_name = "sagemaker-project"
    vpc_id = "vpc-12345"
    model_package_arn = "example-arn"
    model_artifacts_bucket_arn = "arn:aws:s3:::test-bucket"

    endpoint_stack = stack.DeployEndpointStack(
        scope=app,
        id=app_prefix,
        app_prefix=app_prefix,
        sagemaker_project_id=sagemaker_project_id,
        sagemaker_project_name=sagemaker_project_name,
        model_package_arn=model_package_arn,
        model_package_group_name=None,
        model_execution_role_arn=None,
        vpc_id=vpc_id,
        subnet_ids=[],
        model_artifacts_bucket_arn=model_artifacts_bucket_arn,
        ecr_repo_arn=None,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
        endpoint_config_prod_variant={
            "initial_variant_weight": 1,
            "variant_name": "AllTraffic",
        },
    )

    template = Template.from_stack(endpoint_stack)
    template.resource_count_is("AWS::SageMaker::Endpoint", 1)


@mock.patch("scripts.get_approved_package.boto3.client")
def test_synthesize_stack_latest_approved_model_package(mock_s3_client, stack_defaults) -> None:
    import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    sagemaker_project_id = "12345"
    sagemaker_project_name = "sagemaker-project"
    vpc_id = "vpc-12345"
    model_package_group_name = "example-group"
    model_artifacts_bucket_arn = "arn:aws:s3:::test-bucket"

    sagemaker_client = botocore.session.get_session().create_client("sagemaker", region_name="us-east-1")
    mock_s3_client.return_value = sagemaker_client

    with Stubber(sagemaker_client) as stubber:
        expected_params = {
            "ModelPackageGroupName": model_package_group_name,
            "ModelApprovalStatus": "Approved",
            "SortBy": "CreationTime",
            "MaxResults": 100,
        }
        response = {
            "ModelPackageSummaryList": [
                {
                    "ModelPackageArn": f"arn:aws:sagemaker:us-east-1:111:model-package/{model_package_group_name}/1",
                    "ModelPackageStatus": "Completed",
                    "ModelPackageName": model_package_group_name,
                    "CreationTime": "2021-01-01T00:00:00Z",
                },
            ],
        }
        stubber.add_response("list_model_packages", response, expected_params)

        endpoint_stack = stack.DeployEndpointStack(
            scope=app,
            id=app_prefix,
            app_prefix=app_prefix,
            sagemaker_project_id=sagemaker_project_id,
            sagemaker_project_name=sagemaker_project_name,
            model_package_arn=None,
            model_package_group_name=model_package_group_name,
            model_execution_role_arn=None,
            vpc_id=vpc_id,
            subnet_ids=[],
            model_artifacts_bucket_arn=model_artifacts_bucket_arn,
            ecr_repo_arn=None,
            env=cdk.Environment(
                account=os.environ["CDK_DEFAULT_ACCOUNT"],
                region=os.environ["CDK_DEFAULT_REGION"],
            ),
            endpoint_config_prod_variant={
                "initial_variant_weight": 1,
                "variant_name": "AllTraffic",
            },
        )

    template = Template.from_stack(endpoint_stack)
    template.resource_count_is("AWS::SageMaker::Endpoint", 1)
