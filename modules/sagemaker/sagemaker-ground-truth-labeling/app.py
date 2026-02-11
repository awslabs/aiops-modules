# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk
import cdk_nag

from settings import ApplicationSettings
from stack import DeployGroundTruthLabelingStack

app = aws_cdk.App()
app_settings = ApplicationSettings()

stack = DeployGroundTruthLabelingStack(
    scope=app,
    id=app_settings.seedfarmer_settings.app_prefix,
    job_name=app_settings.module_settings.job_name,
    task_type=app_settings.module_settings.task_type,
    sqs_queue_retention_period=app_settings.module_settings.sqs_queue_retention_period,
    sqs_queue_visibility_timeout=app_settings.module_settings.sqs_queue_visibility_timeout,
    sqs_queue_max_receive_count=app_settings.module_settings.sqs_queue_max_receive_count,
    sqs_dlq_retention_period=app_settings.module_settings.sqs_dlq_retention_period,
    sqs_dlq_visibility_timeout=app_settings.module_settings.sqs_dlq_visibility_timeout,
    sqs_dlq_alarm_threshold=app_settings.module_settings.sqs_dlq_alarm_threshold,
    labeling_workteam_arn=app_settings.module_settings.labeling_workteam_arn,
    labeling_instructions_template_s3_uri=app_settings.module_settings.labeling_instructions_template_s3_uri,
    labeling_categories_s3_uri=app_settings.module_settings.labeling_categories_s3_uri,
    labeling_task_title=app_settings.module_settings.labeling_task_title,
    labeling_task_description=app_settings.module_settings.labeling_task_description,
    labeling_task_keywords=app_settings.module_settings.labeling_task_keywords,
    labeling_human_task_config=app_settings.module_settings.labeling_human_task_config,
    labeling_task_price=app_settings.module_settings.labeling_task_price,
    verification_workteam_arn=app_settings.module_settings.verification_workteam_arn,
    verification_instructions_template_s3_uri=app_settings.module_settings.verification_instructions_template_s3_uri,
    verification_categories_s3_uri=app_settings.module_settings.verification_categories_s3_uri,
    verification_task_title=app_settings.module_settings.verification_task_title,
    verification_task_description=app_settings.module_settings.verification_task_description,
    verification_task_keywords=app_settings.module_settings.verification_task_keywords,
    verification_human_task_config=app_settings.module_settings.verification_human_task_config,
    verification_task_price=app_settings.module_settings.verification_task_price,
    labeling_workflow_schedule=app_settings.module_settings.labeling_workflow_schedule,
    permissions_boundary_name=app_settings.module_settings.permissions_boundary_name,
    env=aws_cdk.Environment(
        account=app_settings.cdk_settings.account,
        region=app_settings.cdk_settings.region,
    ),
)

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "DataStoreBucketName": stack.upload_bucket.bucket_name,
            "DataStoreBucketArn": stack.upload_bucket.bucket_arn,
            "SqsQueueName": stack.upload_queue.queue_name,
            "SqsQueueArn": stack.upload_queue.queue_arn,
            "SqsDlqName": stack.upload_dlq.queue_name,
            "SqsDlqArn": stack.upload_dlq.queue_arn,
            "LabelingStateMachineName": stack.labeling_state_machine.state_machine_name,
            "LabelingStateMachineArn": stack.labeling_state_machine.state_machine_arn,
            "FeatureGroupName": stack.feature_group.feature_group_name,
        }
    ),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

aws_cdk.Tags.of(app).add("SeedFarmerDeploymentName", app_settings.seedfarmer_settings.deployment_name)
aws_cdk.Tags.of(app).add("SeedFarmerModuleName", app_settings.seedfarmer_settings.module_name)
aws_cdk.Tags.of(app).add("SeedFarmerProjectName", app_settings.seedfarmer_settings.project_name)

app.synth()
