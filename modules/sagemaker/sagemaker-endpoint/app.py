# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import aws_cdk

from stack import DeployEndpointStack


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"

DEFAULT_SAGEMAKER_PROJECT_ID = None
DEFAULT_SAGEMAKER_PROJECT_NAME = None
DEFAULT_MODEL_PACKAGE_ARN = None
DEFAULT_MODEL_PACKAGE_GROUP_NAME = None
DEFAULT_MODEL_EXECUTION_ROLE_ARN = None
DEFAULT_MODEL_ARTIFACTS_BUCKET_ARN = None
DEFAULT_ECR_REPO_ARN = None
DEFAULT_VARIANT_NAME = "AllTraffic"
DEFAULT_INITIAL_INSTANCE_COUNT = 1
DEFAULT_INITIAL_VARIANT_WEIGHT = 1
DEFAULT_INSTANCE_TYPE = "ml.m4.xlarge"

environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

vpc_id = os.getenv(_param("VPC_ID"))
subnet_ids = json.loads(os.getenv(_param("SUBNET_IDS"), "[]"))
sagemaker_project_id = os.getenv(_param("SAGEMAKER_PROJECT_ID"), DEFAULT_SAGEMAKER_PROJECT_ID)
sagemaker_project_name = os.getenv(_param("SAGEMAKER_PROJECT_NAME"), DEFAULT_SAGEMAKER_PROJECT_NAME)
model_package_arn = os.getenv(_param("MODEL_PACKAGE_ARN"), DEFAULT_MODEL_PACKAGE_ARN)
model_package_group_name = os.getenv(_param("MODEL_PACKAGE_GROUP_NAME"), DEFAULT_MODEL_PACKAGE_GROUP_NAME)
model_execution_role_arn = os.getenv(_param("MODEL_EXECUTION_ROLE_ARN"), DEFAULT_MODEL_EXECUTION_ROLE_ARN)
model_artifacts_bucket_arn = os.getenv(_param("MODEL_ARTIFACTS_BUCKET_ARN"), DEFAULT_MODEL_ARTIFACTS_BUCKET_ARN)
ecr_repo_arn = os.getenv(_param("ECR_REPO_ARN"), DEFAULT_ECR_REPO_ARN)
variant_name = os.getenv(_param("VARIANT_NAME"), DEFAULT_VARIANT_NAME)
initial_instance_count = int(os.getenv(_param("INITIAL_INSTANCE_COUNT"), DEFAULT_INITIAL_INSTANCE_COUNT))
initial_variant_weight = int(os.getenv(_param("INITIAL_VARIANT_WEIGHT"), DEFAULT_INITIAL_VARIANT_WEIGHT))
instance_type = os.getenv(_param("INSTANCE_TYPE"), DEFAULT_INSTANCE_TYPE)

if not vpc_id:
    raise ValueError("Missing input parameter vpc-id")

if not model_package_arn and not model_package_group_name:
    raise ValueError("Parameter model-package-arn or model-package-group-name is required")


app = aws_cdk.App()
stack = DeployEndpointStack(
    scope=app,
    id=app_prefix,
    app_prefix=app_prefix,
    sagemaker_project_id=sagemaker_project_id,
    sagemaker_project_name=sagemaker_project_name,
    model_package_arn=model_package_arn,
    model_package_group_name=model_package_group_name,
    model_execution_role_arn=model_execution_role_arn,
    vpc_id=vpc_id,
    subnet_ids=subnet_ids,
    model_artifacts_bucket_arn=model_artifacts_bucket_arn,
    ecr_repo_arn=ecr_repo_arn,
    endpoint_config_prod_variant={
        "initial_instance_count": initial_instance_count,
        "initial_variant_weight": initial_variant_weight,
        "instance_type": instance_type,
        "variant_name": variant_name,
    },
    env=environment,
)

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ModelExecutionRoleArn": stack.model_execution_role_arn,
            "ModelName": stack.model.model_name,
            "ModelPackageArn": stack.model_package_arn,
            "EndpointName": stack.endpoint.attr_endpoint_name,
            "EndpointUrl": stack.endpoint_url,
        }
    ),
)


app.synth()
