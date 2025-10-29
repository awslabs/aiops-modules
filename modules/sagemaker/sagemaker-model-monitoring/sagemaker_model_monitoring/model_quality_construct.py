from typing import Any, List, Optional

from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct

from sagemaker_model_monitoring.utils import generate_unique_id


class ModelQualityConstruct(Construct):
    """
    CDK construct to define a SageMaker model quality job definition.

    It defines both the model quality job, corresponding schedule, and configuration.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        monitor_image_uri: str,
        endpoint_name: str,
        model_bucket_name: str,
        model_quality_baseline_s3_uri: str,
        model_quality_output_s3_uri: str,
        model_quality_ground_truth_s3_uri: str,
        kms_key_id: str,
        model_monitor_role_arn: str,
        security_group_id: str,
        subnet_ids: List[str],
        instance_count: int,
        instance_type: str,
        instance_volume_size_in_gb: int,
        max_runtime_in_seconds: int,
        problem_type: str,
        inference_attribute: Optional[str],
        probability_attribute: Optional[str],
        probability_threshold_attribute: Optional[int],
        schedule_expression: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CloudFormation doesn't seem to properly wait for the job definition name to be properly populated if we allow
        # it to autogenerate it. Generate one which will hopefully not conflict.
        unique_id = generate_unique_id(
            monitor_image_uri,
            endpoint_name,
            model_bucket_name,
            model_quality_baseline_s3_uri,
            model_quality_output_s3_uri,
            model_quality_ground_truth_s3_uri,
            kms_key_id,
            model_monitor_role_arn,
            security_group_id,
            subnet_ids,
            instance_count,
            instance_type,
            instance_volume_size_in_gb,
            max_runtime_in_seconds,
            problem_type,
            inference_attribute,
            probability_attribute,
            probability_threshold_attribute,
            schedule_expression,
        )
        job_definition_name = f"model-quality-{unique_id}"

        model_quality_job_definition = sagemaker.CfnModelQualityJobDefinition(
            self,
            "ModelQualityJobDefinition",
            job_resources=sagemaker.CfnModelQualityJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnModelQualityJobDefinition.ClusterConfigProperty(
                    instance_count=instance_count,
                    instance_type=instance_type,
                    volume_size_in_gb=instance_volume_size_in_gb,
                    volume_kms_key_id=kms_key_id,
                )
            ),
            model_quality_app_specification=sagemaker.CfnModelQualityJobDefinition.ModelQualityAppSpecificationProperty(
                image_uri=monitor_image_uri,
                problem_type=problem_type,
            ),
            model_quality_job_input=sagemaker.CfnModelQualityJobDefinition.ModelQualityJobInputProperty(
                ground_truth_s3_input=sagemaker.CfnModelQualityJobDefinition.MonitoringGroundTruthS3InputProperty(
                    s3_uri=model_quality_ground_truth_s3_uri,
                ),
                endpoint_input=sagemaker.CfnModelQualityJobDefinition.EndpointInputProperty(
                    endpoint_name=endpoint_name,
                    local_path="/opt/ml/processing/input_data",
                    inference_attribute=inference_attribute if inference_attribute else None,
                    probability_attribute=probability_attribute if probability_attribute else None,
                    probability_threshold_attribute=probability_threshold_attribute if probability_threshold_attribute else None,
                ),
            ),
            model_quality_job_output_config=sagemaker.CfnModelQualityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelQualityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelQualityJobDefinition.S3OutputProperty(
                            local_path="/opt/ml/processing/output",
                            s3_uri=model_quality_output_s3_uri,
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=kms_key_id if kms_key_id else None,
            ),
            job_definition_name=job_definition_name,
            role_arn=model_monitor_role_arn,
            model_quality_baseline_config=sagemaker.CfnModelQualityJobDefinition.ModelQualityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelQualityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"{model_quality_baseline_s3_uri}/constraints.json"
                )
            ),
            stopping_condition=sagemaker.CfnModelQualityJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=max_runtime_in_seconds
            ),
            network_config=sagemaker.CfnModelQualityJobDefinition.NetworkConfigProperty(
                enable_inter_container_traffic_encryption=False,
                enable_network_isolation=False,
                vpc_config=sagemaker.CfnModelQualityJobDefinition.VpcConfigProperty(
                    security_group_ids=[security_group_id], subnets=subnet_ids
                )
                if security_group_id and subnet_ids
                else None,
            ),
        )

        model_quality_monitor_schedule = sagemaker.CfnMonitoringSchedule(
            self,
            "ModelQualityMonitoringSchedule",
            monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
                monitoring_job_definition_name=model_quality_job_definition.job_definition_name,
                monitoring_type="ModelQuality",
                schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                    schedule_expression=schedule_expression,
                ),
            ),
            monitoring_schedule_name=f"{job_definition_name}-schedule",
        )
        model_quality_monitor_schedule.add_dependency(model_quality_job_definition)
