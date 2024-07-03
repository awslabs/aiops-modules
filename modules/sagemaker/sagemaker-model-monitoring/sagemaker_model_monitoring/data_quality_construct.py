from time import time
from typing import Any, List

from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct


class DataQualityConstruct(Construct):
    """
    CDK construct to define a SageMaker data quality job definition.

    It defines both the data quality job, corresponding schedule, and configuration.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        monitor_image_uri: str,
        endpoint_name: str,
        model_bucket_name: str,
        data_quality_checkstep_output_prefix: str,
        data_quality_output_prefix: str,
        kms_key_id: str,
        model_monitor_role_arn: str,
        security_group_id: str,
        subnet_ids: List[str],
        instance_count: int,
        instance_type: str,
        instance_volume_size_in_gb: int,
        max_runtime_in_seconds: int,
        schedule_expression: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CloudFormation doesn't seem to properly wait for the job definition name to be properly populated if we allow
        # it to autogenerate it. Generate one which will hopefully not conflict.
        job_definition_name = f"{endpoint_name}-data-quality-{int(time())}"

        data_quality_job_definition = sagemaker.CfnDataQualityJobDefinition(
            self,
            "DataQualityJobDefinition",
            data_quality_app_specification=sagemaker.CfnDataQualityJobDefinition.DataQualityAppSpecificationProperty(
                image_uri=monitor_image_uri,
            ),
            data_quality_job_input=sagemaker.CfnDataQualityJobDefinition.DataQualityJobInputProperty(
                endpoint_input=sagemaker.CfnDataQualityJobDefinition.EndpointInputProperty(
                    endpoint_name=endpoint_name,
                    local_path="/opt/ml/processing/input/data_quality_input",
                )
            ),
            data_quality_job_output_config=sagemaker.CfnDataQualityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnDataQualityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnDataQualityJobDefinition.S3OutputProperty(
                            local_path="/opt/ml/processing/output/data_quality_output",
                            s3_uri=f"s3://{model_bucket_name}/{data_quality_output_prefix}",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=kms_key_id,
            ),
            job_resources=sagemaker.CfnDataQualityJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnDataQualityJobDefinition.ClusterConfigProperty(
                    instance_count=instance_count,
                    instance_type=instance_type,
                    volume_size_in_gb=instance_volume_size_in_gb,
                    volume_kms_key_id=kms_key_id,
                )
            ),
            job_definition_name=job_definition_name,
            role_arn=model_monitor_role_arn,
            data_quality_baseline_config=sagemaker.CfnDataQualityJobDefinition.DataQualityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnDataQualityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"s3://{model_bucket_name}/{data_quality_checkstep_output_prefix}/constraints.json"
                ),
                statistics_resource=sagemaker.CfnDataQualityJobDefinition.StatisticsResourceProperty(
                    s3_uri=f"s3://{model_bucket_name}/{data_quality_checkstep_output_prefix}/statistics.json"
                ),
            ),
            stopping_condition=sagemaker.CfnDataQualityJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=max_runtime_in_seconds
            ),
            network_config=sagemaker.CfnDataQualityJobDefinition.NetworkConfigProperty(
                enable_inter_container_traffic_encryption=False,
                enable_network_isolation=False,
                vpc_config=sagemaker.CfnDataQualityJobDefinition.VpcConfigProperty(
                    security_group_ids=[security_group_id], subnets=subnet_ids
                ),
            ),
        )

        data_quality_monitor_schedule = sagemaker.CfnMonitoringSchedule(
            self,
            "DataQualityMonitoringSchedule",
            monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
                monitoring_job_definition_name=data_quality_job_definition.job_definition_name,
                monitoring_type="DataQuality",
                schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                    schedule_expression=schedule_expression,
                ),
            ),
            monitoring_schedule_name=f"{job_definition_name}-schedule",
        )
        data_quality_monitor_schedule.add_dependency(data_quality_job_definition)
