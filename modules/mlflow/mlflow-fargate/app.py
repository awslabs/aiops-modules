# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import aws_cdk

from stack import MlflowFargateStack


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"

DEFAULT_ECS_CLUSTER_NAME = None
DEFAULT_SERVICE_NAME = None
DEFAULT_TASK_CPU_UNITS = 4 * 1024
DEFAULT_TASK_MEMORY_LIMIT_MB = 8 * 1024

environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

vpc_id = os.getenv(_param("VPC_ID"))
subnet_ids = json.loads(os.getenv(_param("SUBNET_IDS"), "[]"))
ecs_cluster_name = os.getenv(_param("ECS_CLUSTER_NAME"), DEFAULT_ECS_CLUSTER_NAME)
service_name = os.getenv(_param("SERVICE_NAME"), DEFAULT_SERVICE_NAME)
ecr_repo_name = os.getenv(_param("ECR_REPOSITORY_NAME"))
task_cpu_units = os.getenv(_param("TASK_CPU_UNITS"), DEFAULT_TASK_CPU_UNITS)
task_memory_limit_mb = os.getenv(_param("TASK_MEMORY_LIMIT_MB"), DEFAULT_TASK_MEMORY_LIMIT_MB)
artifacts_bucket_name = os.getenv(_param("ARTIFACTS_BUCKET_NAME"))
# TODO: add persistent backend store

if not ecr_repo_name:
    raise ValueError("Missing input parameter ecr-repository-name")

if not vpc_id:
    raise ValueError("Missing input parameter vpc-id")

app = aws_cdk.App()
stack = MlflowFargateStack(
    scope=app,
    id=app_prefix,
    app_prefix=app_prefix,
    vpc_id=vpc_id,
    subnet_ids=subnet_ids,
    ecs_cluster_name=ecs_cluster_name,
    service_name=service_name,
    ecr_repo_name=ecr_repo_name,
    task_cpu_units=int(task_cpu_units),
    task_memory_limit_mb=int(task_memory_limit_mb),
    artifacts_bucket_name=artifacts_bucket_name,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ECSClusterName": stack.cluster.cluster_name,
            "ServiceName": stack.service.service.service_name,
            "LoadBalancerDNSName": stack.service.load_balancer.load_balancer_dns_name,
        }
    ),
)

app.synth()
