"""Verify that cdk synth produces the expected S3 permission statements.

This test mocks the SageMaker API call (get_approved_package) and all
required environment variables, then synthesizes the DeployEndpointStack
and asserts the ManagedPolicy contains the correct S3 actions.
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
_fake_get_approved = MagicMock(return_value="arn:aws:sagemaker:us-east-1:111111111111:model-package/test-group/1")
_fake_module = MagicMock()
_fake_module.get_approved_package = _fake_get_approved
sys.modules["deploy_app.get_approved_package"] = _fake_module

import aws_cdk as cdk  # noqa: E402
from aws_cdk import assertions  # noqa: E402
from deploy_app.deploy_endpoint_stack import DeployEndpointStack  # noqa: E402


def _synth_deploy_endpoint_stack() -> assertions.Template:
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
        "test-endpoint",
        vpc_id="vpc-abc123",
        subnet_ids=["subnet-aaa"],
        security_group_ids=["sg-aaa"],
    )

    return assertions.Template.from_stack(stack)


def test_managed_policy_has_s3_read_write_actions():
    """The ModelExecutionPolicy must contain S3 read/write actions on the model bucket."""
    template = _synth_deploy_endpoint_stack()

    template.has_resource_properties(
        "AWS::IAM::ManagedPolicy",
        assertions.Match.object_like(
            {
                "PolicyDocument": {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Action": assertions.Match.array_with(
                                        [
                                            "s3:GetObject*",
                                            "s3:GetBucket*",
                                            "s3:List*",
                                            "s3:PutObject",
                                        ]
                                    ),
                                    "Effect": "Allow",
                                    "Resource": [
                                        "arn:aws:s3:::test-model-bucket",
                                        "arn:aws:s3:::test-model-bucket/*",
                                    ],
                                }
                            ),
                        ]
                    ),
                }
            }
        ),
    )


def test_managed_policy_has_data_capture_write_actions():
    """The ModelExecutionPolicy must contain S3 write actions for data capture."""
    template = _synth_deploy_endpoint_stack()

    template.has_resource_properties(
        "AWS::IAM::ManagedPolicy",
        assertions.Match.object_like(
            {
                "PolicyDocument": {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Action": assertions.Match.array_with(
                                        [
                                            "s3:PutObject",
                                        ]
                                    ),
                                    "Effect": "Allow",
                                    "Resource": "arn:aws:s3:::test-model-bucket/endpoint-data-capture/*",
                                }
                            ),
                        ]
                    ),
                }
            }
        ),
    )


def test_no_separate_default_policy():
    """There must be NO DefaultPolicy (inline AWS::IAM::Policy) for S3 permissions.

    S3 permissions must be in the ManagedPolicy, not a separate inline policy,
    to preserve the CloudFormation dependency chain.
    """
    template = _synth_deploy_endpoint_stack()

    # Count all IAM::Policy resources -- there should be none with S3 actions
    resources = template.find_resources("AWS::IAM::Policy")
    for logical_id, resource in resources.items():
        policy_doc = resource.get("Properties", {}).get("PolicyDocument", {})
        statements = policy_doc.get("Statement", [])
        for stmt in statements:
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            s3_actions = [a for a in actions if a.startswith("s3:")]
            assert not s3_actions, (
                f"Found S3 actions {s3_actions} in inline IAM::Policy '{logical_id}'. "
                f"S3 permissions must be in the ManagedPolicy to ensure correct "
                f"CloudFormation dependency ordering."
            )


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
