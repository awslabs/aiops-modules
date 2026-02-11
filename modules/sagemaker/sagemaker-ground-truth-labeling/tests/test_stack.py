# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def stack(task_type: str, labeling_workflow_schedule: str, sqs_dlq_alarm_threshold: int) -> cdk.Stack:
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    job_name = "job-name"
    sqs_queue_retention_period = 1
    sqs_queue_visibility_timeout = 1
    sqs_queue_max_receive_count = 1
    sqs_dlq_retention_period = 1
    sqs_dlq_visibility_timeout = 1
    labeling_workteam_arn = "labeling_workteam"
    labeling_instructions_template_s3_uri = "s3://bucket/labeling_instructions"
    labeling_categories_s3_uri = "s3://bucket/labeling_categories"
    labeling_task_title = "labeling_title"
    labeling_task_description = "labeling_description"
    labeling_task_keywords = ["labeling_keywords"]
    labeling_human_task_config = {"key": "value"}
    labeling_task_price = {"key": {"nested_key": "value"}}
    verification_workteam_arn = "verification_workteam"
    verification_instructions_template_s3_uri = "s3://bucket/verification_instructions"
    verification_categories_s3_uri = "s3://bucket/verification_categories"
    verification_task_title = "verification_title"
    verification_task_description = "verification_description"
    verification_task_keywords = ["verification_keywords"]
    verification_human_task_config = {"key": "value"}
    verification_task_price = {"key": {"nested_key": "value"}}
    permissions_boundary_name = None

    return stack.DeployGroundTruthLabelingStack(
        app,
        f"{project_name}-{dep_name}-{mod_name}",
        job_name=job_name,
        task_type=task_type,
        sqs_queue_retention_period=sqs_queue_retention_period,
        sqs_queue_visibility_timeout=sqs_queue_visibility_timeout,
        sqs_queue_max_receive_count=sqs_queue_max_receive_count,
        sqs_dlq_retention_period=sqs_dlq_retention_period,
        sqs_dlq_visibility_timeout=sqs_dlq_visibility_timeout,
        sqs_dlq_alarm_threshold=sqs_dlq_alarm_threshold,
        labeling_workteam_arn=labeling_workteam_arn,
        labeling_instructions_template_s3_uri=labeling_instructions_template_s3_uri,
        labeling_categories_s3_uri=labeling_categories_s3_uri,
        labeling_task_title=labeling_task_title,
        labeling_task_description=labeling_task_description,
        labeling_task_keywords=labeling_task_keywords,
        labeling_human_task_config=labeling_human_task_config,
        labeling_task_price=labeling_task_price,
        verification_workteam_arn=verification_workteam_arn,
        verification_instructions_template_s3_uri=verification_instructions_template_s3_uri,
        verification_categories_s3_uri=verification_categories_s3_uri,
        verification_task_title=verification_task_title,
        verification_task_description=verification_task_description,
        verification_task_keywords=verification_task_keywords,
        verification_human_task_config=verification_human_task_config,
        verification_task_price=verification_task_price,
        labeling_workflow_schedule=labeling_workflow_schedule,
        permissions_boundary_name=permissions_boundary_name,
    )


@pytest.mark.parametrize(
    "task_type", ["text_single_label_classification", "image_single_label_classification", "image_bounding_box"]
)
@pytest.mark.parametrize("labeling_workflow_schedule", ["cron(0 0 * * ? *)", ""])
@pytest.mark.parametrize("sqs_dlq_alarm_threshold", [0, 1])
def test_synthesize_stack(
    stack: cdk.Stack, task_type: str, labeling_workflow_schedule: str, sqs_dlq_alarm_threshold: int
) -> None:
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::S3::Bucket", 4)
    template.resource_count_is("AWS::SQS::Queue", 2)
    template.resource_count_is("AWS::SageMaker::FeatureGroup", 1)

    lambda_function_count = {
        "text_single_label_classification": 7,
        "image_single_label_classification": 6,  # one less as no lambda to convert text files to SQS message
        "image_bounding_box": 7,  # one additional to run verification job
    }.get(task_type)
    template.resource_count_is("AWS::Lambda::Function", lambda_function_count)

    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    template.resource_count_is("AWS::Scheduler::Schedule", 0 if labeling_workflow_schedule == "" else 1)
    template.resource_count_is("AWS::CloudWatch::Alarm", 0 if sqs_dlq_alarm_threshold == 0 else 1)


@pytest.mark.parametrize(
    "task_type", ["text_single_label_classification", "image_single_label_classification", "image_bounding_box"]
)
@pytest.mark.parametrize("labeling_workflow_schedule", ["cron(0 0 * * ? *)", ""])
@pytest.mark.parametrize("sqs_dlq_alarm_threshold", [0, 1])
def test_no_cdk_nag_errors(
    stack: cdk.Stack, task_type: str, labeling_workflow_schedule: str, sqs_dlq_alarm_threshold: int
) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
