# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import MlflowFargateStack

app_settings = ApplicationSettings()
app = aws_cdk.App()

stack = MlflowFargateStack(
    scope=app,
    id=app_settings.settings.app_prefix,
    vpc_id=app_settings.parameters.vpc_id,
    subnet_ids=app_settings.parameters.subnet_ids,
    ecs_cluster_name=app_settings.parameters.ecs_cluster_name,
    service_name=app_settings.parameters.service_name,
    ecr_repo_name=app_settings.parameters.ecr_repository_name,
    task_cpu_units=app_settings.parameters.task_cpu_units,
    task_memory_limit_mb=app_settings.parameters.task_memory_limit_mb,
    autoscale_max_capacity=app_settings.parameters.autoscale_max_capacity,
    artifacts_bucket_name=app_settings.parameters.artifacts_bucket_name,
    lb_access_logs_bucket_name=app_settings.parameters.lb_access_logs_bucket_name,
    lb_access_logs_bucket_prefix=app_settings.parameters.lb_access_logs_bucket_prefix,
    efs_removal_policy=app_settings.parameters.efs_removal_policy,
    rds_settings=app_settings.parameters.rds_settings,
    tags=app_settings.parameters.tags,
    env=aws_cdk.Environment(
        account=app_settings.default.account,
        region=app_settings.default.region,
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

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

if app_settings.parameters.tags:
    for tag_key, tag_value in app_settings.parameters.tags.items():
        aws_cdk.Tags.of(app).add(tag_key, tag_value)

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.settings.project_name)

app.synth()
