from typing import Any, List, Optional

import constructs
from aws_cdk import Stack, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sagemaker as sagemaker
from cdk_nag import NagSuppressions
from sagemaker import image_uris

from sagemaker_model_monitoring.data_quality_construct import DataQualityConstruct


class SageMakerModelMonitoringStack(Stack):
    """
    CDK stack which provisions SageMaker Model Monitoring.

    This stack is deployed to all the deployment environments of the project.

    It creates the data quality monitor job construct and the associated IAM roles and policies.
    """

    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        sagemaker_project_id: Optional[str],
        sagemaker_project_name: Optional[str],
        endpoint_name: str,
        security_group_id: str,
        subnet_ids: List[str],
        model_package_arn: str,
        model_bucket_arn: str,
        kms_key_id: str,
        # Data quality monitoring options.
        data_quality_checkstep_output_prefix: str,
        data_quality_output_prefix: str,
        data_quality_instance_count: int,
        data_quality_instance_type: str,
        data_quality_instance_volume_size_in_gb: int,
        data_quality_max_runtime_in_seconds: int,
        data_quality_schedule_expression: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        if sagemaker_project_id:
            Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        if sagemaker_project_name:
            Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)

        # TODO Add back cross-region support as a separate S3 replica module?
        # sagemaker requires model package and inference image uri to be in the same region as model and endpoint
        sagemaker.CfnModel.ContainerDefinitionProperty(model_package_name=model_package_arn)

        monitor_image_uri = image_uris.retrieve(framework="model-monitor", region=self.region)

        model_monitor_policy = iam.ManagedPolicy(
            self,
            "Model Monitor Policy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "s3:PutObject",
                            "s3:GetObject",
                            "s3:ListBucket",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[
                            model_bucket_arn,
                            f"{model_bucket_arn}/*",
                        ],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "kms:CreateGrant",
                            "kms:Encrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[
                            f"arn:{self.partition}:kms:{self.region}:{self.account}:key/*",
                        ],
                    ),
                ]
            ),
        )

        # TODO Reduce the use of wildcards by limiting to the provided KMS key ID & needed bucket prefixes.
        NagSuppressions.add_resource_suppressions(
            model_monitor_policy,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "The IAM policy needs access to the S3 bucket and associated KMS keys",
                },
            ],
        )

        model_monitor_role = iam.Role(
            self,
            "Model Monitor Role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                model_monitor_policy,
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
        )

        # TODO Avoid AmazonSageMakerFullAccess by limiting to the needed operations.
        NagSuppressions.add_resource_suppressions(
            model_monitor_role,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "The IAM policy needs access to many SageMaker and EC2 operations.",
                },
            ],
        )

        model_bucket_name = model_bucket_arn.split(":")[-1]

        DataQualityConstruct(
            self,
            "Data Quality Construct",
            monitor_image_uri=monitor_image_uri,
            endpoint_name=endpoint_name,
            model_bucket_name=model_bucket_name,
            data_quality_checkstep_output_prefix=data_quality_checkstep_output_prefix,
            data_quality_output_prefix=data_quality_output_prefix,
            kms_key_id=kms_key_id,
            model_monitor_role_arn=model_monitor_role.role_arn,
            security_group_id=security_group_id,
            subnet_ids=subnet_ids,
            instance_count=data_quality_instance_count,
            instance_type=data_quality_instance_type,
            instance_volume_size_in_gb=data_quality_instance_volume_size_in_gb,
            max_runtime_in_seconds=data_quality_max_runtime_in_seconds,
            schedule_expression=data_quality_schedule_expression,
        )
