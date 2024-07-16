import sys

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import cloud_assembly_schema as cas
from aws_cdk import integ_tests_alpha as integration

sys.path.append("../")

import stack  # noqa: E402

app = cdk.App()

setup_stack = cdk.Stack(app, "sagemaker-studio-integ-setup-stack")
vpc = ec2.Vpc(setup_stack, "VPC")

studio_stack = stack.SagemakerStudioStack(
    app,
    "sagemaker-studio-integ-stack",
    vpc_id=vpc.vpc_id,
    subnet_ids=vpc.private_subnets,
    studio_domain_name="test-domain",
    studio_bucket_name="test-bucket",
    data_science_users=["ds-user-1"],
    lead_data_science_users=["lead-ds-user-1"],
    app_image_config_name=None,
    image_name=None,
    enable_custom_sagemaker_projects=False,
    auth_mode="IAM",
)

integration.IntegTest(
    app,
    "Integration Tests SageMaker Studio Module",
    test_cases=[
        studio_stack,
    ],
    diff_assets=True,
    stack_update_workflow=True,
    cdk_command_options=cas.CdkCommands(
        deploy=cas.DeployCommand(args=cas.DeployOptions(require_approval=cas.RequireApproval.NEVER, json=True)),
        destroy=cas.DestroyCommand(args=cas.DestroyOptions(force=True)),
    ),
)
app.synth()