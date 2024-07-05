from typing import Any, List, Optional

from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct


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
        model_quality_checkstep_output_prefix: str,
        model_quality_output_prefix: str,
        ground_truth_prefix: str,
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
                    s3_uri=f"s3://{model_bucket_name}/{ground_truth_prefix}"
                ),
                endpoint_input=sagemaker.CfnModelQualityJobDefinition.EndpointInputProperty(
                    endpoint_name=endpoint_name,
                    local_path="/opt/ml/processing/input/model_quality_input",
                    inference_attribute=inference_attribute,
                    probability_attribute=probability_attribute,
                    probability_threshold_attribute=probability_threshold_attribute,
                ),
            ),
            model_quality_job_output_config=sagemaker.CfnModelQualityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelQualityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelQualityJobDefinition.S3OutputProperty(
                            local_path="/opt/ml/processing/output/model_quality_output",
                            s3_uri=f"s3://{model_bucket_name}/{model_quality_output_prefix}",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=kms_key_id,
            ),
            job_definition_name=f"{endpoint_name}-model-quality-def",
            role_arn=model_monitor_role_arn,
            model_quality_baseline_config=sagemaker.CfnModelQualityJobDefinition.ModelQualityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelQualityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"s3://{model_bucket_name}/{model_quality_checkstep_output_prefix}/constraints.json"
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
                ),
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
            monitoring_schedule_name=f"{endpoint_name}-model-quality",
        )
        model_quality_monitor_schedule.add_dependency(model_quality_job_definition)
