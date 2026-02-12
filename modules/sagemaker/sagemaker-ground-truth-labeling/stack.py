# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from typing import Any, Dict, List, Tuple, Union

import aws_cdk.aws_lambda as lambda_
import constructs
from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_sagemaker import CfnFeatureGroup
from cdk_nag import NagPackSuppression, NagSuppressions

from constants import (
    LAMBDA_RUNTIME,
    MAX_BUCKET_NAME_LENGTH,
    MAX_FEATURE_GROUP_NAME_LENGTH,
    MAX_SQS_QUEUE_NAME_LENGTH,
)
from labeling_step_function.labeling_state_machine import setup_and_create_state_machine
from task_type_config import IMAGE, TEXT, TaskTypeConfig, get_task_type_config


class DeployGroundTruthLabelingStack(Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        job_name: str,
        task_type: str,
        sqs_queue_retention_period: int,
        sqs_queue_visibility_timeout: int,
        sqs_queue_max_receive_count: int,
        sqs_dlq_retention_period: int,
        sqs_dlq_visibility_timeout: int,
        sqs_dlq_alarm_threshold: int,
        labeling_workteam_arn: str,
        labeling_instructions_template_s3_uri: str,
        labeling_categories_s3_uri: str,
        labeling_task_title: str,
        labeling_task_description: str,
        labeling_task_keywords: List[str],
        labeling_human_task_config: Dict[str, Union[str, int]],
        labeling_task_price: Dict[str, Any],
        verification_workteam_arn: str,
        verification_instructions_template_s3_uri: str,
        verification_categories_s3_uri: str,
        verification_task_title: str,
        verification_task_description: str,
        verification_task_keywords: List[str],
        verification_human_task_config: Dict[str, Any],
        verification_task_price: Dict[str, Dict[str, int]],
        labeling_workflow_schedule: str,
        permissions_boundary_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Apply permissions boundary to all roles in this stack if provided
        if permissions_boundary_name:
            permissions_boundary_policy = iam.ManagedPolicy.from_managed_policy_name(
                self, "PermBoundary", permissions_boundary_name
            )
            iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)

        log_bucket = self.create_log_bucket(job_name=job_name, id=id)

        self.upload_bucket, upload_bucket_kms_key = self.create_upload_bucket(
            job_name=job_name,
            id=id,
            log_bucket=log_bucket,
        )

        self.upload_dlq = self.create_upload_dlq(
            job_name=job_name,
            id=id,
            sqs_dlq_retention_period=sqs_dlq_retention_period,
            sqs_dlq_visibility_timeout=sqs_dlq_visibility_timeout,
            sqs_dlq_alarm_threshold=sqs_dlq_alarm_threshold,
        )

        self.upload_queue, upload_queue_kms_key = self.create_upload_queue(
            job_name=job_name,
            id=id,
            sqs_queue_retention_period=sqs_queue_retention_period,
            sqs_queue_visibility_timeout=sqs_queue_visibility_timeout,
            sqs_queue_max_receive_count=sqs_queue_max_receive_count,
            upload_dlq=self.upload_dlq,
        )

        task_type_config = get_task_type_config(task_type)

        self.create_s3_upload_notification(
            task_type_config_media_type=task_type_config.media_type,
            upload_bucket=self.upload_bucket,
            upload_bucket_kms_key_arn=upload_bucket_kms_key.key_arn,
            upload_queue=self.upload_queue,
            upload_queue_kms_key_arn=upload_queue_kms_key.key_arn,
        )

        feature_group_bucket, feature_group_bucket_kms_key = self.create_feature_group_bucket(
            job_name=job_name,
            id=id,
            log_bucket=log_bucket,
        )

        feature_group_name_suffix = f"-{job_name}-sagemaker-feature-group"
        feature_group_name = (
            f"{id[: MAX_FEATURE_GROUP_NAME_LENGTH - len(feature_group_name_suffix)]}{feature_group_name_suffix}"
        )

        feature_group_role = self.create_feature_group_role(
            feature_group_bucket_arn=feature_group_bucket.bucket_arn,
            feature_group_bucket_kms_key_arn=feature_group_bucket_kms_key.key_arn,
            feature_group_name=feature_group_name,
        )

        feature_group_bucket_kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt", "kms:GenerateDataKey"],
                principals=[feature_group_role],
                resources=["*"],
            )
        )

        self.feature_group = self.create_feature_group(
            task_type_config=task_type_config,
            feature_group_name=feature_group_name,
            feature_group_bucket_name=feature_group_bucket.bucket_name,
            feature_group_bucket_kms_key_arn=feature_group_bucket_kms_key.key_arn,
            feature_group_role=feature_group_role,
        )

        self.labeling_state_machine = setup_and_create_state_machine(
            scope=self,
            id=id,
            job_name=job_name,
            queue=self.upload_queue,
            queue_kms_key_arn=upload_queue_kms_key.key_arn,
            upload_bucket_arn=self.upload_bucket.bucket_arn,
            upload_bucket_kms_key_arn=upload_bucket_kms_key.key_arn,
            log_bucket=log_bucket,
            task_type=task_type,
            feature_group_name=self.feature_group.feature_group_name,
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
        )

        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AWS managed policy is used by CDK-managed Lambda for S3 notifications",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                    ],
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="CDK-managed Lambda for S3 notifications requires these permissions",
                ),
            ],
        )

    def create_log_bucket(
        self,
        job_name: str,
        id: str,
    ) -> s3.Bucket:
        log_bucket_kms_key = kms.Key(
            self,
            "Log Bucket KMS Key",
            description="key used for encryption of data in Amazon S3",
            enable_key_rotation=True,
        )

        # limit bucket name length to 63 chars as that is the limit in S3
        log_bucket_name_suffix = f"-{job_name}-bucket-logs"
        log_bucket_name = f"{id[: MAX_BUCKET_NAME_LENGTH - len(log_bucket_name_suffix)]}{log_bucket_name_suffix}"
        log_bucket = s3.Bucket(
            self,
            "LogBucket",
            bucket_name=log_bucket_name,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption_key=log_bucket_kms_key,
        )

        return log_bucket

    def create_upload_bucket(self, job_name: str, id: str, log_bucket: s3.Bucket) -> Tuple[s3.Bucket, kms.Key]:
        upload_bucket_kms_key = kms.Key(
            self,
            "Upload Bucket KMS Key",
            description="key used for encryption of data in Amazon S3",
            enable_key_rotation=True,
        )

        upload_bucket_name_suffix = f"-{job_name}-upload-bucket"
        upload_bucket_name = (
            f"{id[: MAX_BUCKET_NAME_LENGTH - len(upload_bucket_name_suffix)]}{upload_bucket_name_suffix}"
        )
        upload_bucket = s3.Bucket(
            self,
            "UploadBucket",
            bucket_name=upload_bucket_name,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption_key=upload_bucket_kms_key,
            server_access_logs_prefix="upload_bucket_logs/",
            server_access_logs_bucket=log_bucket,
            cors=[
                s3.CorsRule(
                    allowed_headers=[],
                    allowed_methods=[s3.HttpMethods.GET],
                    allowed_origins=["*"],
                    exposed_headers=["Access-Control-Allow-Origin"],
                )
            ],
        )

        return upload_bucket, upload_bucket_kms_key

    def create_upload_dlq(
        self,
        job_name: str,
        id: str,
        sqs_dlq_retention_period: int,
        sqs_dlq_visibility_timeout: int,
        sqs_dlq_alarm_threshold: int,
    ) -> sqs.Queue:
        upload_dlq_kms_key = kms.Key(
            self,
            "Upload DLQ KMS Key",
            description="key used for encryption of data in Amazon SQS",
            enable_key_rotation=True,
        )

        upload_dlq_name_suffix = f"-{job_name}-upload-dlq"
        upload_dlq_name = f"{id[: MAX_SQS_QUEUE_NAME_LENGTH - len(upload_dlq_name_suffix)]}{upload_dlq_name_suffix}"
        upload_dlq = sqs.Queue(
            self,
            "UploadDLQ",
            queue_name=upload_dlq_name,
            retention_period=Duration.minutes(sqs_dlq_retention_period),
            visibility_timeout=Duration.minutes(sqs_dlq_visibility_timeout),
            enforce_ssl=True,
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=upload_dlq_kms_key,
        )

        if sqs_dlq_alarm_threshold != 0:
            cloudwatch.Alarm(
                self,
                "DlqMessageCountAlarm",
                alarm_name=f"{id}-{job_name}-dlq-message-count-alarm",
                metric=upload_dlq.metric_approximate_number_of_messages_visible(),
                threshold=sqs_dlq_alarm_threshold,
                evaluation_periods=1,
                alarm_description="Alarm when more than 1 message is in the DLQ",
            )

        return upload_dlq

    def create_upload_queue(
        self,
        job_name: str,
        id: str,
        sqs_queue_max_receive_count: int,
        sqs_queue_retention_period: int,
        sqs_queue_visibility_timeout: int,
        upload_dlq: sqs.Queue,
    ) -> Tuple[sqs.Queue, kms.Key]:
        upload_queue_kms_key = kms.Key(
            self,
            "Upload Queue KMS Key",
            description="key used for encryption of data in Amazon SQS",
            enable_key_rotation=True,
        )

        upload_queue_name_suffix = f"-{job_name}-upload-queue"
        upload_queue_name = (
            f"{id[: MAX_SQS_QUEUE_NAME_LENGTH - len(upload_queue_name_suffix)]}{upload_queue_name_suffix}"
        )
        upload_queue = sqs.Queue(
            self,
            "UploadQueue",
            queue_name=upload_queue_name,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=sqs_queue_max_receive_count, queue=upload_dlq),
            retention_period=Duration.minutes(sqs_queue_retention_period),
            visibility_timeout=Duration.minutes(sqs_queue_visibility_timeout),
            enforce_ssl=True,
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=upload_queue_kms_key,
        )

        return upload_queue, upload_queue_kms_key

    def create_s3_upload_notification(
        self,
        task_type_config_media_type: str,
        upload_bucket: s3.Bucket,
        upload_bucket_kms_key_arn: str,
        upload_queue: sqs.Queue,
        upload_queue_kms_key_arn: str,
    ) -> None:
        if task_type_config_media_type == IMAGE:
            upload_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, s3n.SqsDestination(upload_queue))
        elif task_type_config_media_type == TEXT:
            txt_file_s3_to_sqs_relay_lambda_role = iam.Role(
                self,
                "TxtFileS3ToSqsRelayLambdaRole",
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            )
            txt_file_s3_to_sqs_relay_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=["*"],
                )
            )
            txt_file_s3_to_sqs_relay_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["s3:GetObject"],
                    resources=[
                        upload_bucket.bucket_arn,
                        f"{upload_bucket.bucket_arn}/*",
                    ],
                )
            )
            txt_file_s3_to_sqs_relay_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["kms:Decrypt"],
                    resources=[upload_bucket_kms_key_arn],
                )
            )
            txt_file_s3_to_sqs_relay_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["sqs:SendMessage"],
                    resources=[upload_queue.queue_arn],
                )
            )
            txt_file_s3_to_sqs_relay_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["kms:GenerateDataKey"],
                    resources=[upload_queue_kms_key_arn],
                )
            )
            txt_file_s3_to_sqs_relay_lambda = lambda_.Function(
                self,
                "TxtFileS3ToSqsRelayLambda",
                runtime=LAMBDA_RUNTIME,
                code=lambda_.Code.from_asset("lambda"),
                handler="txt_file_s3_to_sqs_relay.handler",
                memory_size=128,
                role=txt_file_s3_to_sqs_relay_lambda_role,
                timeout=Duration.seconds(5),
                environment={
                    "SQS_QUEUE_URL": upload_queue.queue_url,
                },
            )
            upload_bucket.add_event_notification(
                s3.EventType.OBJECT_CREATED,
                s3n.LambdaDestination(txt_file_s3_to_sqs_relay_lambda),
            )
        else:
            raise ValueError(f"Unsupported media type: {task_type_config_media_type}")

    def create_feature_group_bucket(self, job_name: str, id: str, log_bucket: s3.Bucket) -> Tuple[s3.Bucket, kms.Key]:
        feature_group_bucket_kms_key = kms.Key(
            self,
            "FeatureStoreBucket KMS Key",
            description="key used for encryption of data in Amazon S3",
            enable_key_rotation=True,
        )

        feature_group_bucket_name_suffix = f"-{job_name}-feature-store-bucket"
        feature_group_bucket_name = (
            f"{id[: MAX_BUCKET_NAME_LENGTH - len(feature_group_bucket_name_suffix)]}{feature_group_bucket_name_suffix}"
        )
        feature_group_bucket = s3.Bucket(
            self,
            "FeatureStoreBucket",
            bucket_name=feature_group_bucket_name,
            enforce_ssl=True,
            encryption_key=feature_group_bucket_kms_key,
            server_access_logs_prefix="feature_store_bucket_logs/",
            server_access_logs_bucket=log_bucket,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        return feature_group_bucket, feature_group_bucket_kms_key

    def create_feature_group_role(
        self,
        feature_group_bucket_arn: str,
        feature_group_bucket_kms_key_arn: str,
        feature_group_name: str,
    ) -> iam.Role:
        feature_group_role = iam.Role(
            self,
            "FeatureGroupRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        )
        feature_group_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                    "s3:GetBucketAcl",
                    "s3:PutObjectAcl",
                ],
                resources=[
                    feature_group_bucket_arn,
                    f"{feature_group_bucket_arn}/*",
                ],
            )
        )
        feature_group_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt", "kms:GenerateDataKey"],
                resources=[feature_group_bucket_kms_key_arn],
            )
        )
        feature_group_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sagemaker:PutRecord"],
                resources=[
                    f"arn:{self.partition}:sagemaker:{self.region}:{self.account}:feature-group/{feature_group_name}",
                ],
            ),
        )

        return feature_group_role

    def create_feature_group(
        self,
        task_type_config: TaskTypeConfig,
        feature_group_name: str,
        feature_group_bucket_name: str,
        feature_group_bucket_kms_key_arn: str,
        feature_group_role: iam.Role,
    ) -> CfnFeatureGroup:
        source_key = task_type_config.source_key.replace("-", "_")
        feature_definitions = [
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name=source_key,
                feature_type="String",
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="event_time",
                feature_type="Fractional",
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(feature_name="labeling_job", feature_type="String"),
        ]
        if task_type_config.verification_attribute_name:
            feature_definitions.append(
                CfnFeatureGroup.FeatureDefinitionProperty(
                    feature_name="status",
                    feature_type="String",
                )
            )
        for feature_definition in task_type_config.feature_group_config:
            feature_definitions.append(
                CfnFeatureGroup.FeatureDefinitionProperty(
                    feature_name=feature_definition.feature_name,
                    feature_type=feature_definition.feature_type,
                )
            )

        sagemaker_feature_group = CfnFeatureGroup(
            self,
            "SagemakerFeatureGroup",
            feature_group_name=feature_group_name,
            event_time_feature_name="event_time",
            record_identifier_feature_name=source_key,
            feature_definitions=feature_definitions,
            offline_store_config={
                "S3StorageConfig": {
                    "S3Uri": f"s3://{feature_group_bucket_name}/feature-store/",
                    "KmsKeyId": feature_group_bucket_kms_key_arn,
                }
            },
            role_arn=feature_group_role.role_arn,
        )
        sagemaker_feature_group.node.add_dependency(feature_group_role)

        return sagemaker_feature_group
