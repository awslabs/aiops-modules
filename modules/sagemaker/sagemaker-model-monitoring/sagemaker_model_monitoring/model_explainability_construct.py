from typing import Any, List, Optional

from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct


class ModelExplainabilityConstruct(Construct):
    """
    CDK construct to define a SageMaker model explainability job definition.

    It defines both the model explainability job, corresponding schedule, and configuration.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        clarify_image_uri: str,
        endpoint_name: str,
        model_bucket_name: str,
        model_explainability_checkstep_output_prefix: str,
        model_explainability_checkstep_analysis_config_prefix: Optional[str],
        model_explainability_output_prefix: str,
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
        schedule_expression: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # To match the defaults in SageMaker.
        if model_explainability_checkstep_analysis_config_prefix is None:
            model_explainability_checkstep_analysis_config_prefix = model_explainability_checkstep_output_prefix

        model_explainability_job_definition = sagemaker.CfnModelExplainabilityJobDefinition(
            self,
            "ModelExplainabilityJobDefinition",
            job_resources=sagemaker.CfnModelExplainabilityJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnModelExplainabilityJobDefinition.ClusterConfigProperty(
                    instance_count=instance_count,
                    instance_type=instance_type,
                    volume_size_in_gb=instance_volume_size_in_gb,
                    volume_kms_key_id=kms_key_id,
                )
            ),
            model_explainability_app_specification=sagemaker.CfnModelExplainabilityJobDefinition.ModelExplainabilityAppSpecificationProperty(
                config_uri=f"s3://{model_bucket_name}/{model_explainability_checkstep_analysis_config_prefix}/analysis_config.json",
                image_uri=clarify_image_uri,
            ),
            model_explainability_job_input=sagemaker.CfnModelExplainabilityJobDefinition.ModelExplainabilityJobInputProperty(
                endpoint_input=sagemaker.CfnModelExplainabilityJobDefinition.EndpointInputProperty(
                    endpoint_name=endpoint_name,
                    local_path="/opt/ml/processing/input/model_explainability_input",
                    features_attribute=features_attribute,
                    inference_attribute=inference_attribute,
                    probability_attribute=probability_attribute,
                )
            ),
            model_explainability_job_output_config=sagemaker.CfnModelExplainabilityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelExplainabilityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelExplainabilityJobDefinition.S3OutputProperty(
                            local_path="/opt/ml/processing/output/model_explainability_output",
                            s3_uri=f"s3://{model_bucket_name}/{model_explainability_output_prefix}",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=kms_key_id,
            ),
            job_definition_name=f"{endpoint_name}-model-explain-def",
            role_arn=model_monitor_role_arn,
            model_explainability_baseline_config=sagemaker.CfnModelExplainabilityJobDefinition.ModelExplainabilityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelExplainabilityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"s3://{model_bucket_name}/{model_explainability_checkstep_output_prefix}/analysis.json"
                )
            ),
            stopping_condition=sagemaker.CfnModelExplainabilityJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=max_runtime_in_seconds
            ),
            network_config=sagemaker.CfnModelExplainabilityJobDefinition.NetworkConfigProperty(
                enable_inter_container_traffic_encryption=False,
                enable_network_isolation=False,
                vpc_config=sagemaker.CfnModelExplainabilityJobDefinition.VpcConfigProperty(
                    security_group_ids=[security_group_id], subnets=subnet_ids
                ),
            ),
        )

        model_explainability_monitor_schedule = sagemaker.CfnMonitoringSchedule(
            self,
            "ModelExplainabilityMonitoringSchedule",
            monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
                monitoring_job_definition_name=model_explainability_job_definition.job_definition_name,
                monitoring_type="ModelExplainability",
                schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                    schedule_expression=schedule_expression,
                ),
            ),
            monitoring_schedule_name=f"{endpoint_name}-model-explainability",
        )
        model_explainability_monitor_schedule.add_depends_on(model_explainability_job_definition)
