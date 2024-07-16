import sys

import aws_cdk as cdk
from aws_cdk import aws_ecr as ecr
from aws_cdk import cloud_assembly_schema as cas
from aws_cdk import integ_tests_alpha as integration

sys.path.append("../")

import stack  # noqa: E402

app = cdk.App()

setup_stack = cdk.Stack(app, "base-resources-stack")
ecr_repo = ecr.Repository(setup_stack, "repo", image_scan_on_push=True, removal_policy=cdk.RemovalPolicy.DESTROY)

mlflow_image_stack = stack.MlflowImagePublishingStack(
    app,
    "mlflow-image",
    ecr_repository=ecr_repo,
)

integration.IntegTest(
    app,
    "Integration Tests Buckets Module",
    test_cases=[
        setup_stack,
        mlflow_image_stack,
    ],
    diff_assets=True,
    stack_update_workflow=True,
    cdk_command_options=cas.CdkCommands(
        deploy=cas.DeployCommand(args=cas.DeployOptions(require_approval=cas.RequireApproval.NEVER, json=True)),
        destroy=cas.DestroyCommand(args=cas.DestroyOptions(force=True)),
    ),
)
app.synth()
