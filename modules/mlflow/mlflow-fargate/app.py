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
DEFAULT_AUTOSCALE_MAX_CAPACITY = 2
DEFAULT_LB_ACCESS_LOGS_BUCKET_NAME = None
DEFAULT_LB_ACCESS_LOGS_BUCKET_PREFIX = None

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
autoscale_max_capacity = os.getenv(_param("AUTOSCALE_MAX_CAPACITY"), DEFAULT_AUTOSCALE_MAX_CAPACITY)
artifacts_bucket_name = os.getenv(_param("ARTIFACTS_BUCKET_NAME"))
lb_access_logs_bucket_name = os.getenv(_param("LB_ACCESS_LOGS_BUCKET_NAME"), DEFAULT_LB_ACCESS_LOGS_BUCKET_NAME)
lb_access_logs_bucket_prefix = os.getenv(_param("LB_ACCESS_LOGS_BUCKET_PREFIX"), DEFAULT_LB_ACCESS_LOGS_BUCKET_PREFIX)
rds_hostname = os.getenv(_param("RDS_HOSTNAME"))
rds_port = os.getenv(_param("RDS_PORT"))
rds_credentials_secret_arn = os.getenv(_param("RDS_CREDENTIALS_SECRET_ARN"))

if not vpc_id:
    raise ValueError("Missing input parameter vpc-id")

if not ecr_repo_name:
    raise ValueError("Missing input parameter ecr-repository-name")

if not artifacts_bucket_name:
    raise ValueError("Missing input parameter artifacts-bucket-name")


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
    autoscale_max_capacity=int(autoscale_max_capacity),
    artifacts_bucket_name=artifacts_bucket_name,
    lb_access_logs_bucket_name=lb_access_logs_bucket_name,
    lb_access_logs_bucket_prefix=lb_access_logs_bucket_prefix,
    rds_hostname=rds_hostname,
    rds_port=rds_port,
    rds_credentials_secret_arn=rds_credentials_secret_arn,
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
            "ServiceName": stack.fargate_service.service.service_name,
            "LoadBalancerDNSName": stack.fargate_service.load_balancer.load_balancer_dns_name,
            "LoadBalancerAccessLogsBucketArn": stack.lb_access_logs_bucket.bucket_arn,
            "EFSFileSystemId": stack.fs.file_system_id,
        }
    ),
)

app.synth()
