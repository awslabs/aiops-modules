# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App, CfnOutput
from stack import DagResources

project_name = os.getenv("MLOPS_PROJECT_NAME", "")
deployment_name = os.getenv("MLOPS_DEPLOYMENT_NAME", "")
module_name = os.getenv("MLOPS_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"

mwaa_exec_role = os.getenv("MLOPS_PARAMETER_MWAA_EXEC_ROLE_ARN", "")
bucket_policy_arn = os.getenv("MLOPS_PARAMETER_BUCKET_POLICY_ARN")
permission_boundary_arn = os.getenv("MLOPS_PERMISSION_BOUNDARY_ARN")

app = App()

stack = DagResources(
    scope=app,
    id=app_prefix,
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    mwaa_exec_role=mwaa_exec_role,
    bucket_policy_arn=bucket_policy_arn,
    permission_boundary_arn=permission_boundary_arn,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "DagRoleArn": stack.dag_role.role_arn,
            "MlOpsBucket": stack.mlops_assets_bucket.bucket_name,
            "SageMakerExecutionRole": stack.sagemaker_execution_role.role_arn,
        }
    ),
)

app.synth(force=True)
