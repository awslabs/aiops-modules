"""Verify that cdk synth produces correct SageMaker resource names.

This test mocks the SageMaker API call (get_approved_package) and all
required environment variables, then synthesizes the DeployEndpointStack
and asserts that stage_name drives unique SageMaker resource names.
"""

import json
import os
import sys
from unittest.mock import MagicMock

# -- Dummy environment variables (must be set before importing constants) ----
_ENV = {
    "MODEL_BUCKET_ARN": "arn:aws:s3:::test-model-bucket",
    "MODEL_PACKAGE_GROUP_NAME": "test-model-group",
    "DEV_ACCOUNT_ID": "111111111111",
    "DEV_REGION": "us-east-1",
    "DEV_VPC_ID": "vpc-abc123",
    "DEV_SUBNET_IDS": json.dumps(["subnet-aaa"]),
    "DEV_SECURITY_GROUP_IDS": json.dumps(["sg-aaa"]),
    "PRE_PROD_ACCOUNT_ID": "222222222222",
    "PRE_PROD_REGION": "us-east-1",
    "PRE_PROD_VPC_ID": "vpc-def456",
    "PRE_PROD_SUBNET_IDS": json.dumps(["subnet-bbb"]),
    "PRE_PROD_SECURITY_GROUP_IDS": json.dumps(["sg-bbb"]),
    "PROD_ACCOUNT_ID": "333333333333",
    "PROD_REGION": "us-east-1",
    "PROD_VPC_ID": "vpc-ghi789",
    "PROD_SUBNET_IDS": json.dumps(["subnet-ccc"]),
    "PROD_SECURITY_GROUP_IDS": json.dumps(["sg-ccc"]),
    "PROJECT_NAME": "test-project",
    "PROJECT_ID": "test-id",
    "ENABLE_NETWORK_ISOLATION": "true",
    "ENABLE_DATA_CAPTURE": "true",
    "ENABLE_MANUAL_APPROVAL": "false",
    "ENABLE_EVENTBRIDGE_TRIGGER": "false",
}

# Set env vars before any imports that read them
os.environ.update(_ENV)

# Stub out the get_approved_package module before it tries to create a boto3 client.
# The module creates a boto3.client("sagemaker") at import time, so we must
# intercept it before deploy_endpoint_stack imports it.
_fake_get_approved = MagicMock(
    return_value="arn:aws:sagemaker:us-east-1:111111111111:model-package/test-group/1"
)
_fake_module = MagicMock()
_fake_module.get_approved_package = _fake_get_approved
sys.modules["deploy_app.get_approved_package"] = _fake_module

import aws_cdk as cdk  # noqa: E402
from aws_cdk import assertions  # noqa: E402
from deploy_app.deploy_endpoint_stack import DeployEndpointStack  # noqa: E402


def _synth_deploy_endpoint_stack(stage_name: str = "dev") -> assertions.Template:
    """Synthesize a standalone DeployEndpointStack and return its Template."""
    # Reset the mock so each test gets a fresh call count
    _fake_get_approved.reset_mock()

    # Use a Stage with a concrete account (matches real usage in pipeline_stack.py)
    app = cdk.App()
    stage = cdk.Stage(
        app,
        "TestStage",
        env=cdk.Environment(account="111111111111", region="us-east-1"),
    )
    stack = DeployEndpointStack(
        stage,
        "test-project-endpoint",
        stage_name=stage_name,
        vpc_id="vpc-abc123",
        subnet_ids=["subnet-aaa"],
        security_group_ids=["sg-aaa"],
    )

    return assertions.Template.from_stack(stack)


def _get_endpoint_name(template: assertions.Template) -> str:
    """Extract the SageMaker endpoint name from a synthesized template."""
    endpoints = template.find_resources("AWS::SageMaker::Endpoint")
    assert len(endpoints) == 1, f"Expected 1 endpoint, found {len(endpoints)}"
    props = next(iter(endpoints.values()))["Properties"]
    return props["EndpointName"]


def test_stage_name_produces_unique_endpoint_names():
    """Different stage_name values must produce different SageMaker endpoint names."""
    dev_template = _synth_deploy_endpoint_stack(stage_name="dev")
    prod_template = _synth_deploy_endpoint_stack(stage_name="prod")

    dev_ep = _get_endpoint_name(dev_template)
    prod_ep = _get_endpoint_name(prod_template)

    assert dev_ep != prod_ep, f"dev and prod endpoint names should differ, both are '{dev_ep}'"
    assert "-dev-" in dev_ep, f"Expected '-dev-' in endpoint name, got '{dev_ep}'"
    assert "-prod-" in prod_ep, f"Expected '-prod-' in endpoint name, got '{prod_ep}'"


def test_role_references_managed_policy():
    """The ModelExecutionRole must reference the ManagedPolicy (dependency chain)."""
    template = _synth_deploy_endpoint_stack()

    template.has_resource_properties(
        "AWS::IAM::Role",
        assertions.Match.object_like(
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "sagemaker.amazonaws.com"},
                        }
                    ],
                },
                "ManagedPolicyArns": assertions.Match.array_with(
                    [{"Ref": assertions.Match.string_like_regexp("ModelExecutionPolicy.*")}]
                ),
            }
        ),
    )
