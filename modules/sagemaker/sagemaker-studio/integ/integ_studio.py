import json
import os
import sys
from typing import Dict, List

import aws_cdk as cdk
import boto3
from aws_cdk import cloud_assembly_schema as cas
from aws_cdk import integ_tests_alpha as integration

sys.path.append("../")

import stack  # noqa: E402

app = cdk.App()


def get_module_dependencies(resource_keys: List[str]) -> Dict[str, str]:
    ssm = boto3.client("ssm", region_name="us-east-1")
    dependencies = {}
    try:
        for key in resource_keys:
            dependencies[key] = ssm.get_parameter(Name=f"/module-integration-tests/{key}")["Parameter"]["Value"]
    except Exception as e:
        print(f"issue getting dependencies: {e}")
    return dependencies


dependencies = get_module_dependencies(
    # Add any required resource identifiers here
    resource_keys=["vpc-id", "vpc-private-subnets"]
)

studio_stack = stack.SagemakerStudioStack(
    app,
    "sagemaker-studio-integ-stack",
    vpc_id=dependencies["vpc-id"],
    subnet_ids=json.loads(dependencies["vpc-private-subnets"]),
    studio_domain_name="test-domain",
    studio_bucket_name="test-bucket",
    data_science_users=["ds-user-1"],
    lead_data_science_users=["lead-ds-user-1"],
    app_image_config_name=None,
    image_name=None,
    enable_custom_sagemaker_projects=False,
    enable_domain_resource_isolation=True,
    enable_jupyterlab_app=False,
    enable_jupyterlab_app_sharing=False,
    jupyterlab_app_instance_type=None,
    auth_mode="IAM",
    role_path=None,
    policy_path=None,
    permissions_boundary_arn=None,
    mlflow_enabled=False,
    mlflow_server_name="mlflow",
    mlflow_server_version=None,
    mlflow_server_size=None,
    mlflow_artifact_store_bucket_name=None,
    mlflow_artifact_store_bucket_prefix="/",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="us-east-1"),
)

integration.IntegTest(
    app,
    "Integration Tests SageMaker Studio Module",
    test_cases=[
        studio_stack,
    ],
    diff_assets=True,
    stack_update_workflow=True,
    enable_lookups=True,
    cdk_command_options=cas.CdkCommands(
        deploy=cas.DeployCommand(args=cas.DeployOptions(require_approval=cas.RequireApproval.NEVER, json=True)),
        destroy=cas.DestroyCommand(args=cas.DestroyOptions(force=True)),
    ),
)
app.synth()
