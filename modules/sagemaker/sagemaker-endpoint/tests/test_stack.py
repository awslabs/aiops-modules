import os
import sys
from unittest import mock

import aws_cdk as cdk
import botocore.session
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template
from botocore.stub import Stubber


@pytest.fixture(scope="function", autouse=True)
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        # Unload the app import so that subsequent tests don't reuse
        if "stack" in sys.modules:
            del sys.modules["stack"]

        yield


@pytest.fixture(scope="function")
def stack_model_package_input() -> cdk.Stack:
    import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    sagemaker_project_id = "12345"
    sagemaker_project_name = "sagemaker-project"
    sagemaker_domain_id = "ABCDE"
    sagemaker_domain_arn = f"arn:aws:sagemaker:::domain/{sagemaker_domain_id}"
    vpc_id = "vpc-12345"
    model_package_arn = "example-arn"
    model_artifacts_bucket_arn = "arn:aws:s3:::test-bucket"
    managed_instance_scaling = True
    scaling_min_instance_count = 1
    scaling_max_instance_count = 2
    permissions_boundary_name = None

    return stack.DeployEndpointStack(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        sagemaker_project_id=sagemaker_project_id,
        sagemaker_project_name=sagemaker_project_name,
        sagemaker_domain_id=sagemaker_domain_id,
        sagemaker_domain_arn=sagemaker_domain_arn,
        model_package_arn=model_package_arn,
        model_package_group_name=None,
        model_execution_role_arn=None,
        vpc_id=vpc_id,
        subnet_ids=[],
        model_artifacts_bucket_arn=model_artifacts_bucket_arn,
        ecr_repo_arn=None,
        endpoint_config_prod_variant={
            "initial_variant_weight": 1,
            "variant_name": "AllTraffic",
        },
        managed_instance_scaling=managed_instance_scaling,
        scaling_min_instance_count=scaling_min_instance_count,
        scaling_max_instance_count=scaling_max_instance_count,
        data_capture_sampling_percentage=0,
        data_capture_prefix="",
        permissions_boundary_name=permissions_boundary_name,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
        enable_network_isolation=True,
    )


@pytest.fixture(scope="function")
@mock.patch("scripts.get_approved_package.boto3.client")
def stack_latest_approved_model_package(mock_s3_client) -> cdk.Stack:
    import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    sagemaker_project_id = "12345"
    sagemaker_project_name = "sagemaker-project"
    sagemaker_domain_id = "ABCDE"
    sagemaker_domain_arn = f"arn:aws:sagemaker:::domain/{sagemaker_domain_id}"
    vpc_id = "vpc-12345"
    model_package_group_name = "example-group"
    model_artifacts_bucket_arn = "arn:aws:s3:::test-bucket"
    managed_instance_scaling = True
    scaling_min_instance_count = 1
    scaling_max_instance_count = 2

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

        return stack.DeployEndpointStack(
            scope=app,
            id=f"{project_name}-{dep_name}-{mod_name}",
            sagemaker_project_id=sagemaker_project_id,
            sagemaker_project_name=sagemaker_project_name,
            sagemaker_domain_id=sagemaker_domain_id,
            sagemaker_domain_arn=sagemaker_domain_arn,
            model_package_arn=None,
            model_package_group_name=model_package_group_name,
            model_execution_role_arn=None,
            vpc_id=vpc_id,
            subnet_ids=[],
            model_artifacts_bucket_arn=model_artifacts_bucket_arn,
            ecr_repo_arn=None,
            endpoint_config_prod_variant={
                "initial_variant_weight": 1,
                "variant_name": "AllTraffic",
            },
            managed_instance_scaling=managed_instance_scaling,
            scaling_min_instance_count=scaling_min_instance_count,
            scaling_max_instance_count=scaling_max_instance_count,
            data_capture_sampling_percentage=0,
            data_capture_prefix="",
            permissions_boundary_name=None,
            env=cdk.Environment(
                account=os.environ["CDK_DEFAULT_ACCOUNT"],
                region=os.environ["CDK_DEFAULT_REGION"],
            ),
            enable_network_isolation=True,
        )


@pytest.fixture(params=["stack_model_package_input", "stack_latest_approved_model_package"], scope="function")
def stack(request, stack_model_package_input, stack_latest_approved_model_package) -> cdk.Stack:
    return request.getfixturevalue(request.param)


def test_synthesize_stack(stack: cdk.Stack) -> None:
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::SageMaker::Endpoint", 1)


def test_no_cdk_nag_errors(stack: cdk.Stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
