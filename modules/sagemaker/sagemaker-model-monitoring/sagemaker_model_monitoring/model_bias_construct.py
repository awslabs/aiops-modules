from typing import Any, List, Optional

from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct


class ModelBiasConstruct(Construct):
    """
    CDK construct to define a SageMaker model bias job definition.

    It defines both the model bias job, corresponding schedule, and configuration.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        clarify_image_uri: str,
        endpoint_name: str,
        model_bucket_name: str,
        model_bias_checkstep_output_prefix: str,
        model_bias_checkstep_analysis_config_prefix: Optional[str],
        model_bias_output_prefix: str,
        ground_truth_prefix: str,
        kms_key_id: str,
        model_monitor_role_arn: str,
        security_group_id: str,
        subnet_ids: List[str],
        instance_count: int,
        instance_type: str,
        instance_volume_size_in_gb: int,
        max_runtime_in_seconds: int,
        features_attribute: Optional[str],
        inference_attribute: Optional[str],
        probability_attribute: Optional[str],
        probability_threshold_attribute: Optional[int],
        schedule_expression: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # To match the defaults in SageMaker.
        if model_bias_checkstep_analysis_config_prefix is None:
            model_bias_checkstep_analysis_config_prefix = model_bias_checkstep_output_prefix

        model_bias_job_definition = sagemaker.CfnModelBiasJobDefinition(
            self,
            "ModelBiasJobDefinition",
            job_resources=sagemaker.CfnModelBiasJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnModelBiasJobDefinition.ClusterConfigProperty(
                    instance_count=instance_count,
                    instance_type=instance_type,
                    volume_size_in_gb=instance_volume_size_in_gb,
                    volume_kms_key_id=kms_key_id,
                )
            ),
            model_bias_app_specification=sagemaker.CfnModelBiasJobDefinition.ModelBiasAppSpecificationProperty(
                config_uri=f"s3://{model_bucket_name}/{model_bias_checkstep_analysis_config_prefix}/analysis_config.json",
                image_uri=clarify_image_uri,
            ),
            model_bias_job_input=sagemaker.CfnModelBiasJobDefinition.ModelBiasJobInputProperty(
                ground_truth_s3_input=sagemaker.CfnModelBiasJobDefinition.MonitoringGroundTruthS3InputProperty(
                    s3_uri=f"s3://{model_bucket_name}/{ground_truth_prefix}"
                ),
                endpoint_input=sagemaker.CfnModelBiasJobDefinition.EndpointInputProperty(
                    endpoint_name=endpoint_name,
                    local_path="/opt/ml/processing/input/model_bias_input",
                    features_attribute=features_attribute,
                    inference_attribute=inference_attribute,
                    probability_attribute=probability_attribute,
                    probability_threshold_attribute=probability_threshold_attribute,
                ),
            ),
            model_bias_job_output_config=sagemaker.CfnModelBiasJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelBiasJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelBiasJobDefinition.S3OutputProperty(
                            local_path="/opt/ml/processing/output/model_bias_output",
                            s3_uri=f"s3://{model_bucket_name}/{model_bias_output_prefix}",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=kms_key_id,
            ),
            job_definition_name=f"{endpoint_name}-model-bias-def",
            role_arn=model_monitor_role_arn,
            model_bias_baseline_config=sagemaker.CfnModelBiasJobDefinition.ModelBiasBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelBiasJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"s3://{model_bucket_name}/{model_bias_checkstep_output_prefix}/analysis.json"
                )
            ),
            stopping_condition=sagemaker.CfnModelBiasJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=max_runtime_in_seconds
            ),
            network_config=sagemaker.CfnModelBiasJobDefinition.NetworkConfigProperty(
                enable_inter_container_traffic_encryption=False,
                enable_network_isolation=False,
                vpc_config=sagemaker.CfnModelBiasJobDefinition.VpcConfigProperty(
                    security_group_ids=[security_group_id], subnets=subnet_ids
                ),
            ),
        )

        model_bias_monitor_schedule = sagemaker.CfnMonitoringSchedule(
            self,
            "ModelBiasMonitoringSchedule",
            monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
                monitoring_job_definition_name=model_bias_job_definition.job_definition_name,
                monitoring_type="ModelBias",
                schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                    schedule_expression=schedule_expression,
                ),
            ),
            monitoring_schedule_name=f"{endpoint_name}-model-bias",
        )
        model_bias_monitor_schedule.add_dependency(model_bias_job_definition)
