import json
from typing import Any, Dict, List, Optional, Tuple

import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_scheduler as scheduler
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_stepfunctions as sfn
import aws_cdk.aws_stepfunctions_tasks as tasks
from aws_cdk import Duration, RemovalPolicy, Stack
from cdk_nag import NagSuppressions

from constants import (
    AC_ARN_MAP,
    LAMBDA_RUNTIME,
    MAX_BUCKET_NAME_LENGTH,
    MAX_LAMBDA_FUNCTION_NAME_LENGTH,
    MAX_STATE_MACHINE_NAME_LENGTH,
)
from task_type_config import TaskTypeConfig, get_task_type_config

LAMBDA_ASSET_FOLDER = "labeling_step_function/lambda"


def setup_and_create_state_machine(
    scope: Stack,
    id: str,
    job_name: str,
    queue: sqs.Queue,
    queue_kms_key_arn: str,
    upload_bucket_arn: str,
    upload_bucket_kms_key_arn: str,
    log_bucket: s3.Bucket,
    task_type: str,
    feature_group_name: str,
    labeling_workteam_arn: str,
    labeling_instructions_template_s3_uri: str,
    labeling_categories_s3_uri: str,
    labeling_task_title: str,
    labeling_task_description: str,
    labeling_task_keywords: List[str],
    labeling_human_task_config: Dict[str, Any],
    labeling_task_price: Dict[str, Dict[str, int]],
    verification_workteam_arn: str,
    verification_instructions_template_s3_uri: str,
    verification_categories_s3_uri: str,
    verification_task_title: str,
    verification_task_description: str,
    verification_task_keywords: List[str],
    verification_human_task_config: Dict[str, Any],
    verification_task_price: Dict[str, Dict[str, int]],
    labeling_workflow_schedule: str,
) -> sfn.StateMachine:
    ground_truth_output_bucket, ground_truth_output_bucket_kms_key = create_ground_truth_output_bucket(
        scope=scope, job_name=job_name, id=id, log_bucket=log_bucket
    )

    task_type_config = get_task_type_config(task_type)

    poll_sqs_queue_lambda = create_poll_sqs_queue_lambda(
        scope=scope,
        queue=queue,
        queue_kms_key_arn=queue_kms_key_arn,
        ground_truth_output_bucket=ground_truth_output_bucket,
        ground_truth_output_bucket_kms_key_arn=ground_truth_output_bucket_kms_key.key_arn,
        job_name=job_name,
        id=id,
        task_type=task_type,
        task_media_type=task_type_config.media_type,
    )

    ground_truth_role = create_ground_truth_role(
        scope=scope,
        upload_bucket_arn=upload_bucket_arn,
        ground_truth_output_bucket_arn=ground_truth_output_bucket.bucket_arn,
        labeling_instructions_template_s3_uri=labeling_instructions_template_s3_uri,
        labeling_categories_s3_uri=labeling_categories_s3_uri,
        task_type_config_verification_attribute_name=task_type_config.verification_attribute_name,
        verification_instructions_template_s3_uri=verification_instructions_template_s3_uri,
        verification_categories_s3_uri=verification_categories_s3_uri,
        ground_truth_output_bucket_kms_key_arn=ground_truth_output_bucket_kms_key.key_arn,
        upload_bucket_kms_key_arn=upload_bucket_kms_key_arn,
    )

    labeling_job_name = "labeling-job"
    verification_job_name = "verification-job"

    run_ground_truth_job_lambda_execution_role = create_run_ground_truth_job_lambda_execution_role(
        scope=scope,
        ground_truth_output_bucket_kms_key_arn=ground_truth_output_bucket_kms_key.key_arn,
        ground_truth_output_bucket_arn=ground_truth_output_bucket.bucket_arn,
        labeling_job_name=labeling_job_name,
        verification_job_name=verification_job_name,
        ground_truth_role_arn=ground_truth_role.role_arn,
    )

    run_labeling_job_lambda = create_run_labeling_job_lambda(
        scope=scope,
        job_name=job_name,
        id=id,
        run_ground_truth_job_lambda_execution_role=run_ground_truth_job_lambda_execution_role,
        labeling_job_name=labeling_job_name,
        ground_truth_role_arn=ground_truth_role.role_arn,
        ground_truth_output_bucket_name=ground_truth_output_bucket.bucket_name,
        task_type_config=task_type_config,
        labeling_workteam_arn=labeling_workteam_arn,
        labeling_instructions_template_s3_uri=labeling_instructions_template_s3_uri,
        labeling_categories_s3_uri=labeling_categories_s3_uri,
        labeling_task_title=labeling_task_title,
        labeling_task_description=labeling_task_description,
        labeling_task_keywords=labeling_task_keywords,
        labeling_human_task_config=labeling_human_task_config,
        labeling_task_price=labeling_task_price,
    )

    run_verification_job_lambda = create_run_verification_job_lambda(
        scope=scope,
        task_type_config=task_type_config,
        job_name=job_name,
        id=id,
        run_ground_truth_job_lambda_execution_role=run_ground_truth_job_lambda_execution_role,
        verification_job_name=verification_job_name,
        ground_truth_role_arn=ground_truth_role.role_arn,
        ground_truth_output_bucket_name=ground_truth_output_bucket.bucket_name,
        verification_workteam_arn=verification_workteam_arn,
        verification_instructions_template_s3_uri=verification_instructions_template_s3_uri,
        verification_categories_s3_uri=verification_categories_s3_uri,
        verification_task_title=verification_task_title,
        verification_task_description=verification_task_description,
        verification_task_keywords=verification_task_keywords,
        verification_human_task_config=verification_human_task_config,
        verification_task_price=verification_task_price,
    )

    update_feature_store_lambda = create_update_feature_store_lambda(
        scope=scope,
        ground_truth_output_bucket=ground_truth_output_bucket,
        ground_truth_output_bucket_kms_key_arn=ground_truth_output_bucket_kms_key.key_arn,
        feature_group_name=feature_group_name,
        queue=queue,
        task_type_config=task_type_config,
        job_name=job_name,
        id=id,
    )

    return_messages_to_sqs_queue_lambda = create_return_messages_to_sqs_queue_lambda(
        scope=scope,
        queue=queue,
        ground_truth_output_bucket=ground_truth_output_bucket,
        ground_truth_output_bucket_kms_key_arn=ground_truth_output_bucket_kms_key.key_arn,
        job_name=job_name,
        task_media_type=task_type_config.media_type,
        id=id,
    )

    state_machine = create_state_machine(
        scope=scope,
        id=id,
        job_name=job_name,
        poll_sqs_queue_lambda=poll_sqs_queue_lambda,
        run_labeling_job_lambda=run_labeling_job_lambda,
        run_verification_job_lambda=run_verification_job_lambda,
        update_feature_store_lambda=update_feature_store_lambda,
        return_messages_to_sqs_queue_lambda=return_messages_to_sqs_queue_lambda,
        labeling_job_name=labeling_job_name,
        verification_job_name=verification_job_name,
    )

    create_labeling_workflow_schedule(
        scope=scope,
        labeling_workflow_schedule=labeling_workflow_schedule,
        state_machine_arn=state_machine.state_machine_arn,
    )

    return state_machine


def create_ground_truth_output_bucket(
    scope: Stack, job_name: str, id: str, log_bucket: s3.Bucket
) -> Tuple[s3.Bucket, kms.Key]:
    ground_truth_output_bucket_kms_key = kms.Key(
        scope,
        "GroundTruthOutputBucketKMSKey",
        description="Key for encrypting the Ground Truth output bucket",
        enable_key_rotation=True,
    )
    ground_truth_output_bucket_name_suffix = f"{job_name}-ground-truth-output-bucket"
    ground_truth_output_bucket_name = (
        f"{id[: MAX_BUCKET_NAME_LENGTH - len(ground_truth_output_bucket_name_suffix)]}"
        f"{ground_truth_output_bucket_name_suffix}"
    )
    ground_truth_output_bucket = s3.Bucket(
        scope,
        "GroundTruthOutputBucket",
        bucket_name=ground_truth_output_bucket_name,
        enforce_ssl=True,
        encryption_key=ground_truth_output_bucket_kms_key,
        server_access_logs_prefix="ground_truth_output_logs/",
        server_access_logs_bucket=log_bucket,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True,
        cors=[
            s3.CorsRule(
                allowed_headers=[],
                allowed_methods=[s3.HttpMethods.GET],
                allowed_origins=["*"],
                exposed_headers=["Access-Control-Allow-Origin"],
            )
        ],
    )

    return ground_truth_output_bucket, ground_truth_output_bucket_kms_key


def create_poll_sqs_queue_lambda(
    scope: Stack,
    queue: sqs.Queue,
    queue_kms_key_arn: str,
    ground_truth_output_bucket: s3.Bucket,
    ground_truth_output_bucket_kms_key_arn: str,
    job_name: str,
    id: str,
    task_type: str,
    task_media_type: str,
) -> lambda_.Function:
    poll_sqs_queue_lambda_execution_role = iam.Role(
        scope,
        "PollSqsQueueLambdaExecutionRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )
    poll_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=["*"],
        )
    )
    poll_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                queue.queue_arn,
            ],
            actions=[
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
            ],
        )
    )
    poll_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                queue_kms_key_arn,
            ],
            actions=[
                "kms:Decrypt",
            ],
        )
    )
    poll_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket.bucket_arn,
                f"{ground_truth_output_bucket.bucket_arn}/*",
            ],
            actions=[
                "s3:PutObject",
            ],
        )
    )
    poll_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_kms_key_arn,
            ],
            actions=[
                "kms:GenerateDataKey",
            ],
        )
    )

    poll_sqs_queue_lambda_name_suffix = f"{job_name}-poll-sqs-queue-lambda"
    poll_sqs_queue_lambda_name = (
        f"{id[: MAX_LAMBDA_FUNCTION_NAME_LENGTH - len(poll_sqs_queue_lambda_name_suffix)]}"
        f"{poll_sqs_queue_lambda_name_suffix}"
    )
    poll_sqs_queue_lambda = lambda_.Function(
        scope,
        "PollSqsQueueFunction",
        runtime=LAMBDA_RUNTIME,
        code=lambda_.Code.from_asset(LAMBDA_ASSET_FOLDER),
        handler="poll_sqs_queue.handler",
        function_name=poll_sqs_queue_lambda_name,
        memory_size=512,
        role=poll_sqs_queue_lambda_execution_role,
        timeout=Duration.seconds(600),
        environment={
            "SQS_QUEUE_URL": queue.queue_url,
            "OUTPUT_BUCKET": ground_truth_output_bucket.bucket_name,
            "TASK_TYPE": task_type,
            "TASK_MEDIA_TYPE": task_media_type,
        },
    )

    return poll_sqs_queue_lambda


def create_ground_truth_role(
    scope: Stack,
    upload_bucket_arn: str,
    ground_truth_output_bucket_arn: str,
    labeling_instructions_template_s3_uri: str,
    labeling_categories_s3_uri: str,
    task_type_config_verification_attribute_name: Optional[str],
    verification_instructions_template_s3_uri: str,
    verification_categories_s3_uri: str,
    ground_truth_output_bucket_kms_key_arn: str,
    upload_bucket_kms_key_arn: str,
) -> iam.Role:
    ground_truth_role = iam.Role(
        scope,
        "GroundTruthRole",
        assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSageMakerGroundTruthExecution",
            ),
        ],
    )
    ground_truth_role_s3_get_object_resources = [
        upload_bucket_arn,
        f"{upload_bucket_arn}/*",
        ground_truth_output_bucket_arn,
        f"{ground_truth_output_bucket_arn}/*",
        get_s3_arn_from_uri(labeling_categories_s3_uri, partition=scope.partition),
    ]
    if labeling_instructions_template_s3_uri:
        ground_truth_role_s3_get_object_resources.append(
            get_s3_arn_from_uri(labeling_instructions_template_s3_uri, partition=scope.partition)
        )
    if task_type_config_verification_attribute_name:
        ground_truth_role_s3_get_object_resources.extend(
            [
                get_s3_arn_from_uri(verification_instructions_template_s3_uri, partition=scope.partition),
                get_s3_arn_from_uri(verification_categories_s3_uri, partition=scope.partition),
            ]
        )
    ground_truth_role.add_to_policy(
        iam.PolicyStatement(
            resources=ground_truth_role_s3_get_object_resources,
            actions=[
                "s3:GetObject",
            ],
        )
    )
    ground_truth_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_arn,
                f"{ground_truth_output_bucket_arn}/*",
            ],
            actions=[
                "s3:PutObject",
            ],
        )
    )
    ground_truth_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_kms_key_arn,
            ],
            actions=[
                "kms:GenerateDataKey",
                "kms:Decrypt",
            ],
        )
    )
    ground_truth_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                upload_bucket_kms_key_arn,
            ],
            actions=[
                "kms:Decrypt",
            ],
        )
    )
    NagSuppressions.add_resource_suppressions(
        ground_truth_role,
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AWS manged policy used for Ground Truth",
            }
        ],
    )

    return ground_truth_role


def create_run_ground_truth_job_lambda_execution_role(
    scope: Stack,
    ground_truth_output_bucket_kms_key_arn: str,
    ground_truth_output_bucket_arn: str,
    labeling_job_name: str,
    verification_job_name: str,
    ground_truth_role_arn: str,
) -> iam.Role:
    run_ground_truth_job_lambda_execution_role = iam.Role(
        scope,
        "GroundTruthJobLambdaExecutionRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )
    run_ground_truth_job_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=["*"],
        )
    )
    run_ground_truth_job_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_kms_key_arn,
            ],
            actions=["kms:GenerateDataKey", "kms:Decrypt"],
        )
    )
    run_ground_truth_job_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_arn,
                f"{ground_truth_output_bucket_arn}/*",
            ],
            actions=[
                "s3:GetObject",
                "s3:PutObject",
            ],
        )
    )
    run_ground_truth_job_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                f"arn:{scope.partition}:sagemaker:{scope.region}:{scope.account}:labeling-job/{labeling_job_name}-*",
                f"arn:{scope.partition}:sagemaker:{scope.region}:{scope.account}:labeling-job/{verification_job_name}-*",
            ],
            actions=[
                "sagemaker:CreateLabelingJob",
            ],
        )
    )
    run_ground_truth_job_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_role_arn,
            ],
            actions=[
                "iam:PassRole",
            ],
        )
    )

    return run_ground_truth_job_lambda_execution_role


def create_run_labeling_job_lambda(
    scope: Stack,
    job_name: str,
    id: str,
    run_ground_truth_job_lambda_execution_role: iam.Role,
    labeling_job_name: str,
    ground_truth_role_arn: str,
    ground_truth_output_bucket_name: str,
    task_type_config: TaskTypeConfig,
    labeling_workteam_arn: str,
    labeling_instructions_template_s3_uri: str,
    labeling_categories_s3_uri: str,
    labeling_task_title: str,
    labeling_task_description: str,
    labeling_task_keywords: List[str],
    labeling_human_task_config: Dict[str, Any],
    labeling_task_price: Dict[str, Dict[str, int]],
) -> lambda_.Function:
    run_labeling_job_lambda_name_suffix = f"{job_name}-labeling-job-lambda"
    run_labeling_job_lambda_name = (
        f"{id[: MAX_LAMBDA_FUNCTION_NAME_LENGTH - len(run_labeling_job_lambda_name_suffix)]}"
        f"{run_labeling_job_lambda_name_suffix}"
    )
    run_labeling_job_lambda = lambda_.Function(
        scope,
        "LabelingJobFunction",
        runtime=LAMBDA_RUNTIME,
        code=lambda_.Code.from_asset(LAMBDA_ASSET_FOLDER),
        handler="run_labeling_job.handler",
        function_name=run_labeling_job_lambda_name,
        memory_size=512,
        role=run_ground_truth_job_lambda_execution_role,
        timeout=Duration.seconds(15),
        environment={
            "AC_ARN_MAP": json.dumps(AC_ARN_MAP),
            "TASK_TYPE": task_type_config.task_type,
            "SOURCE_KEY": task_type_config.source_key,
            "LABELING_JOB_NAME": labeling_job_name,
            "GROUND_TRUTH_ROLE_ARN": ground_truth_role_arn,
            "OUTPUT_BUCKET": ground_truth_output_bucket_name,
            "FUNCTION_NAME": task_type_config.function_name,
            "WORKTEAM_ARN": labeling_workteam_arn,
            "INSTRUCTIONS_TEMPLATE_S3_URI": labeling_instructions_template_s3_uri,
            "LABEL_CATEGORIES_S3_URI": labeling_categories_s3_uri,
            "TASK_TITLE": labeling_task_title,
            "TASK_DESCRIPTION": labeling_task_description,
            "TASK_KEYWORDS": json.dumps(labeling_task_keywords),
            "HUMAN_TASK_CONFIG": json.dumps(labeling_human_task_config),
            "TASK_PRICE": json.dumps(labeling_task_price),
            "LABELING_ATTRIBUTE_NAME": task_type_config.labeling_attribute_name,
        },
    )

    return run_labeling_job_lambda


def create_run_verification_job_lambda(
    scope: Stack,
    task_type_config: TaskTypeConfig,
    job_name: str,
    id: str,
    run_ground_truth_job_lambda_execution_role: iam.Role,
    verification_job_name: str,
    ground_truth_role_arn: str,
    ground_truth_output_bucket_name: str,
    verification_workteam_arn: str,
    verification_instructions_template_s3_uri: str,
    verification_categories_s3_uri: str,
    verification_task_title: str,
    verification_task_description: str,
    verification_task_keywords: List[str],
    verification_human_task_config: Dict[str, Any],
    verification_task_price: Dict[str, Dict[str, int]],
) -> Optional[lambda_.Function]:
    if task_type_config.verification_attribute_name:
        run_verification_job_lambda_name_suffix = f"{job_name}-verification-job-lambda"
        run_verification_job_lambda_name = (
            f"{id[: MAX_LAMBDA_FUNCTION_NAME_LENGTH - len(run_verification_job_lambda_name_suffix)]}"
            f"{run_verification_job_lambda_name_suffix}"
        )
        run_verification_job_lambda = lambda_.Function(
            scope,
            "VerificationJobFunction",
            runtime=LAMBDA_RUNTIME,
            code=lambda_.Code.from_asset(LAMBDA_ASSET_FOLDER),
            handler="run_verification_job.handler",
            function_name=run_verification_job_lambda_name,
            memory_size=512,
            role=run_ground_truth_job_lambda_execution_role,
            timeout=Duration.seconds(30),
            environment={
                "AC_ARN_MAP": json.dumps(AC_ARN_MAP),
                "SOURCE_KEY": task_type_config.source_key,
                "VERIFICATION_JOB_NAME": verification_job_name,
                "GROUND_TRUTH_ROLE_ARN": ground_truth_role_arn,
                "OUTPUT_BUCKET": ground_truth_output_bucket_name,
                "FUNCTION_NAME": task_type_config.function_name,
                "WORKTEAM_ARN": verification_workteam_arn,
                "INSTRUCTIONS_TEMPLATE_S3_URI": verification_instructions_template_s3_uri,
                "LABEL_CATEGORIES_S3_URI": verification_categories_s3_uri,
                "TASK_TITLE": verification_task_title,
                "TASK_DESCRIPTION": verification_task_description,
                "TASK_KEYWORDS": json.dumps(verification_task_keywords),
                "HUMAN_TASK_CONFIG": json.dumps(verification_human_task_config),
                "TASK_PRICE": json.dumps(verification_task_price),
                "VERIFICATION_ATTRIBUTE_NAME": task_type_config.verification_attribute_name,
                "LABELING_ATTRIBUTE_NAME": task_type_config.labeling_attribute_name,
            },
        )
        return run_verification_job_lambda
    else:
        return None


def create_update_feature_store_lambda(
    scope: Stack,
    ground_truth_output_bucket: s3.Bucket,
    ground_truth_output_bucket_kms_key_arn: str,
    feature_group_name: str,
    queue: sqs.Queue,
    task_type_config: TaskTypeConfig,
    job_name: str,
    id: str,
) -> lambda_.Function:
    update_feature_store_lambda_execution_role = iam.Role(
        scope,
        "UpdateFeatureStoreLambdaExecutionRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )
    update_feature_store_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=["*"],
        )
    )
    update_feature_store_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket.bucket_arn,
                f"{ground_truth_output_bucket.bucket_arn}/*",
            ],
            actions=[
                "s3:GetObject",
                "s3:PutObject",
            ],
        )
    )
    update_feature_store_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_kms_key_arn,
            ],
            actions=[
                "kms:GenerateDataKey",
                "kms:Decrypt",
            ],
        )
    )
    update_feature_store_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                f"arn:{scope.partition}:sagemaker:{scope.region}:{scope.account}:feature-group/{feature_group_name}",
            ],
            actions=[
                "sagemaker:PutRecord",
            ],
        )
    )
    update_feature_store_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                queue.queue_arn,
            ],
            actions=[
                "sqs:DeleteMessage",
            ],
        )
    )

    feature_group_definitions = {
        definition.feature_name: definition.output_key for definition in task_type_config.feature_group_config
    }

    update_feature_store_lambda_name_suffix = f"{job_name}-update-feature-store-lambda"
    update_feature_store_lambda_name = (
        f"{id[: MAX_LAMBDA_FUNCTION_NAME_LENGTH - len(update_feature_store_lambda_name_suffix)]}"
        f"{update_feature_store_lambda_name_suffix}"
    )
    update_feature_store_lambda_environment = {
        "FEATURE_GROUP_NAME": feature_group_name,
        "FEATURE_GROUP_DEFINITIONS": json.dumps(feature_group_definitions),
        "SQS_QUEUE_URL": queue.queue_url,
        "OUTPUT_BUCKET": ground_truth_output_bucket.bucket_name,
        "LABELING_ATTRIBUTE_NAME": task_type_config.labeling_attribute_name,
        "TASK_MEDIA_TYPE": task_type_config.media_type,
        "SOURCE_KEY": task_type_config.source_key,
    }
    if task_type_config.verification_attribute_name:
        update_feature_store_lambda_environment["VERIFICATION_ATTRIBUTE_NAME"] = (
            task_type_config.verification_attribute_name
        )
    update_feature_store_lambda = lambda_.Function(
        scope,
        "UpdateFeatureStoreFunction",
        runtime=LAMBDA_RUNTIME,
        code=lambda_.Code.from_asset(LAMBDA_ASSET_FOLDER),
        handler="update_feature_store.handler",
        function_name=update_feature_store_lambda_name,
        memory_size=512,
        role=update_feature_store_lambda_execution_role,
        timeout=Duration.seconds(900),
        environment=update_feature_store_lambda_environment,
    )

    return update_feature_store_lambda


def create_return_messages_to_sqs_queue_lambda(
    scope: Stack,
    queue: sqs.Queue,
    ground_truth_output_bucket: s3.Bucket,
    ground_truth_output_bucket_kms_key_arn: str,
    job_name: str,
    task_media_type: str,
    id: str,
) -> lambda_.Function:
    return_messages_to_sqs_queue_lambda_execution_role = iam.Role(
        scope,
        "ReturnMessagesToSqsQueueLambdaExecutionRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )
    return_messages_to_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=["*"],
        )
    )
    return_messages_to_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                queue.queue_arn,
            ],
            actions=[
                "sqs:ChangeMessageVisibility",
            ],
        )
    )
    return_messages_to_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket.bucket_arn,
                f"{ground_truth_output_bucket.bucket_arn}/*",
            ],
            actions=[
                "s3:GetObject",
            ],
        )
    )
    return_messages_to_sqs_queue_lambda_execution_role.add_to_policy(
        iam.PolicyStatement(
            resources=[
                ground_truth_output_bucket_kms_key_arn,
            ],
            actions=[
                "kms:Decrypt",
            ],
        )
    )

    return_messages_to_sqs_queue_lambda_name_suffix = f"{job_name}-return-messages-to-sqs-queue-lambda"
    return_messages_to_sqs_queue_lambda_name = (
        f"{id[: MAX_LAMBDA_FUNCTION_NAME_LENGTH - len(return_messages_to_sqs_queue_lambda_name_suffix)]}"
        f"{return_messages_to_sqs_queue_lambda_name_suffix}"
    )
    return_messages_to_sqs_queue_lambda = lambda_.Function(
        scope,
        "ReturnMessagesToSqsQueueFunction",
        runtime=LAMBDA_RUNTIME,
        code=lambda_.Code.from_asset(LAMBDA_ASSET_FOLDER),
        handler="return_messages_to_sqs_queue.handler",
        function_name=return_messages_to_sqs_queue_lambda_name,
        memory_size=512,
        role=return_messages_to_sqs_queue_lambda_execution_role,
        timeout=Duration.seconds(600),
        environment={
            "SQS_QUEUE_URL": queue.queue_url,
            "OUTPUT_BUCKET": ground_truth_output_bucket.bucket_name,
            "TASK_MEDIA_TYPE": task_media_type,
        },
    )

    return return_messages_to_sqs_queue_lambda


def create_state_machine(
    scope: Stack,
    id: str,
    job_name: str,
    poll_sqs_queue_lambda: lambda_.Function,
    run_labeling_job_lambda: lambda_.Function,
    run_verification_job_lambda: Optional[lambda_.Function],
    update_feature_store_lambda: lambda_.Function,
    return_messages_to_sqs_queue_lambda: lambda_.Function,
    labeling_job_name: str,
    verification_job_name: str,
) -> sfn.StateMachine:
    state_machine_log_group = logs.LogGroup(
        scope,
        "StateMachineLogGroup",
        log_group_name=f"/aws/vendedlogs/states/{job_name}",
        retention=logs.RetentionDays.ONE_MONTH,
        removal_policy=RemovalPolicy.DESTROY,
    )

    state_machine_name_suffix = f"-{job_name}-state-machine"
    state_machine_name = (
        f"{id[: MAX_STATE_MACHINE_NAME_LENGTH - len(state_machine_name_suffix)]}{state_machine_name_suffix}"
    )
    state_machine = sfn.StateMachine(
        scope,
        "LabelingStateMachine",
        state_machine_name=state_machine_name,
        definition=get_state_machine_definition(
            scope,
            poll_sqs_queue_lambda=poll_sqs_queue_lambda,
            run_labeling_job_lambda=run_labeling_job_lambda,
            run_verification_job_lambda=run_verification_job_lambda,
            update_feature_store_lambda=update_feature_store_lambda,
            return_messages_to_sqs_queue_lambda=return_messages_to_sqs_queue_lambda,
            labeling_job_name=labeling_job_name,
            verification_job_name=verification_job_name,
        ),
        logs=sfn.LogOptions(destination=state_machine_log_group, level=sfn.LogLevel.ALL),
        tracing_enabled=True,
    )

    return state_machine


def get_state_machine_definition(
    scope: Stack,
    poll_sqs_queue_lambda: lambda_.Function,
    run_labeling_job_lambda: lambda_.Function,
    run_verification_job_lambda: Optional[lambda_.Function],
    update_feature_store_lambda: lambda_.Function,
    return_messages_to_sqs_queue_lambda: lambda_.Function,
    labeling_job_name: str,
    verification_job_name: str,
) -> sfn.Chain:
    success = sfn.Succeed(scope, "Labeling Pipeline execution succeeded")
    fail = sfn.Fail(scope, "Labeling Pipeline execution failed")

    poll_sqs_queue = tasks.LambdaInvoke(
        scope,
        "PollSqsQueue",
        lambda_function=poll_sqs_queue_lambda,
        payload=sfn.TaskInput.from_object(
            {
                "ExecutionId": sfn.JsonPath.string_at("$$.Execution.Id"),
            }
        ),
        result_path="$.Output",
        result_selector={
            "MessagesCount.$": "$.Payload.MessagesCount",
            "RecordSourceToReceiptHandleS3Key.$": "$.Payload.RecordSourceToReceiptHandleS3Key",
        },
    )

    run_labeling_job = tasks.LambdaInvoke(
        scope,
        "RunLabelingJob",
        lambda_function=run_labeling_job_lambda,
        payload=sfn.TaskInput.from_object(
            {
                "ExecutionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                "RecordSourceToReceiptHandleS3Key": sfn.JsonPath.string_at("$.Output.RecordSourceToReceiptHandleS3Key"),
            }
        ),
        result_path="$.Output.RunLabelingJobOutput",
        result_selector={
            "LabelingJobName.$": "$.Payload.LabelingJobName",
        },
    )

    run_verification_job = None
    return_unlabeled_messages_to_sqs_queue = None
    if run_verification_job_lambda:
        run_verification_job = tasks.LambdaInvoke(
            scope,
            "RunVerificationJob",
            lambda_function=run_verification_job_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "ExecutionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "LabelingJobOutputUri": sfn.JsonPath.string_at(
                        "$.DescribeLabelingJobOutput.LabelingJobOutput.OutputDatasetS3Uri"
                    ),
                    "RecordSourceToReceiptHandleS3Key": sfn.JsonPath.string_at(
                        "$.Output.RecordSourceToReceiptHandleS3Key"
                    ),
                }
            ),
            result_path="$.Output",
            result_selector={
                "RunLabelingJobOutput": {
                    "LabelingJobName.$": "$.Payload.LabelingJobName",
                },
                "UnlabeledRecordSourceToReceiptHandleS3Key.$": "$.Payload.UnlabeledRecordSourceToReceiptHandleS3Key",
                "RecordSourceToReceiptHandleS3Key.$": "$.Payload.RecordSourceToReceiptHandleS3Key",
            },
        )

        return_unlabeled_messages_to_sqs_queue = tasks.LambdaInvoke(
            scope,
            "ReturnUnlabeledMessagesToSqsQueue",
            lambda_function=return_messages_to_sqs_queue_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "RecordSourceToReceiptHandleS3Key": sfn.JsonPath.string_at(
                        "$.Output.UnlabeledRecordSourceToReceiptHandleS3Key"
                    ),
                }
            ),
            result_path=sfn.JsonPath.DISCARD,
        )

    update_feature_store = tasks.LambdaInvoke(
        scope,
        "UpdateFeatureStore",
        lambda_function=update_feature_store_lambda,
        payload=sfn.TaskInput.from_object(
            {
                "ExecutionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                "LabelingJobOutputUri": sfn.JsonPath.string_at(
                    "$.DescribeLabelingJobOutput.LabelingJobOutput.OutputDatasetS3Uri"
                ),
                "RecordSourceToReceiptHandleS3Key": sfn.JsonPath.string_at("$.Output.RecordSourceToReceiptHandleS3Key"),
            }
        ),
        result_path="$.Output",
        result_selector={
            "RejectedLabelsRecordSourceToReceiptHandleS3Key.$": (
                "$.Payload.RejectedLabelsRecordSourceToReceiptHandleS3Key"
            ),
        },
    )

    # invoke multiple times as we can't have multiple next steps
    return_messages_to_sqs_queue_on_failure = tasks.LambdaInvoke(
        scope,
        "ReturnMessagesToSqsQueueOnFailure",
        lambda_function=return_messages_to_sqs_queue_lambda,
        payload=sfn.TaskInput.from_object(
            {
                "RecordSourceToReceiptHandleS3Key": sfn.JsonPath.string_at("$.Output.RecordSourceToReceiptHandleS3Key"),
            }
        ),
    )
    return_messages_to_sqs_queue_on_failure.next(fail)

    return_remaining_label_messages_to_sqs_queue = tasks.LambdaInvoke(
        scope,
        "ReturnRemainingLabelMessagesToSqsQueue",
        lambda_function=return_messages_to_sqs_queue_lambda,
        payload=sfn.TaskInput.from_object(
            {
                "RecordSourceToReceiptHandleS3Key": sfn.JsonPath.string_at(
                    "$.Output.RejectedLabelsRecordSourceToReceiptHandleS3Key"
                ),
            }
        ),
    )

    post_labeling_job_step = update_feature_store.next(return_remaining_label_messages_to_sqs_queue.next(success))

    if run_verification_job and return_unlabeled_messages_to_sqs_queue:
        post_labeling_job_step = run_verification_job.next(
            return_unlabeled_messages_to_sqs_queue.next(
                create_labeling_job_waiter(
                    scope,
                    verification_job_name,
                    return_messages_to_sqs_queue_on_failure,
                    post_labeling_job_step,
                )
            )
        )

    definition = poll_sqs_queue.next(
        sfn.Choice(scope, "New messages?")
        .when(
            sfn.Condition.number_equals("$.Output.MessagesCount", 0),
            success,
        )
        .otherwise(
            run_labeling_job.next(
                create_labeling_job_waiter(
                    scope,
                    labeling_job_name,
                    return_messages_to_sqs_queue_on_failure,
                    post_labeling_job_step,
                )
            )
        )
    )

    return definition


def create_labeling_job_waiter(
    scope: Stack,
    labeling_job_name: str,
    fail: sfn.IChainable,
    next: sfn.IChainable,
) -> sfn.Chain:
    get_labeling_job_status = tasks.CallAwsService(
        scope,
        f"Get {labeling_job_name} status",
        service="sagemaker",
        action="describeLabelingJob",
        parameters={"LabelingJobName": sfn.JsonPath.string_at("$.Output.RunLabelingJobOutput.LabelingJobName")},
        iam_resources=[
            f"arn:{scope.partition}:sagemaker:{scope.region}:{scope.account}:labeling-job/{labeling_job_name}-*",
        ],
        result_path="$.DescribeLabelingJobOutput",
    )

    wait_x = sfn.Wait(
        scope,
        f"Waiting for - {labeling_job_name} - completion",
        time=sfn.WaitTime.duration(Duration.seconds(30)),
    )

    return wait_x.next(get_labeling_job_status).next(
        sfn.Choice(scope, f"{labeling_job_name} Complete?")
        .when(
            sfn.Condition.string_equals("$.DescribeLabelingJobOutput.LabelingJobStatus", "Failed"),
            fail,
        )
        .when(
            sfn.Condition.string_equals("$.DescribeLabelingJobOutput.LabelingJobStatus", "Stopped"),
            fail,
        )
        .when(
            sfn.Condition.and_(
                sfn.Condition.string_equals("$.DescribeLabelingJobOutput.LabelingJobStatus", "Completed"),
                sfn.Condition.number_equals("$.DescribeLabelingJobOutput.LabelCounters.TotalLabeled", 0),
            ),
            fail,
        )
        .when(
            sfn.Condition.and_(
                sfn.Condition.string_equals("$.DescribeLabelingJobOutput.LabelingJobStatus", "Completed"),
                sfn.Condition.number_greater_than("$.DescribeLabelingJobOutput.LabelCounters.TotalLabeled", 0),
            ),
            next,
        )
        .otherwise(wait_x)
    )


def create_labeling_workflow_schedule(scope: Stack, labeling_workflow_schedule: str, state_machine_arn: str) -> None:
    if labeling_workflow_schedule:
        scheduler_role = iam.Role(
            scope,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
        scheduler_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    state_machine_arn,
                ],
                actions=[
                    "states:StartExecution",
                ],
            )
        )
        scheduler.CfnSchedule(
            scope,
            "LabelingStateMachineSchedule",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(mode="OFF"),
            schedule_expression=labeling_workflow_schedule,
            target=scheduler.CfnSchedule.TargetProperty(
                arn=state_machine_arn,
                role_arn=scheduler_role.role_arn,
            ),
        )


def get_s3_arn_from_uri(uri: str, partition: str) -> str:
    if not uri:
        return ""
    bucket_name = uri.split("/")[2]
    object_key = "/".join(uri.split("/")[3:])
    return f"arn:{partition}:s3:::{bucket_name}/{object_key}"
