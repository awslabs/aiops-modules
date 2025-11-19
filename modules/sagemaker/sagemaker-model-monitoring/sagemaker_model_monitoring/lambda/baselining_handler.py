import os
from typing import Any, Dict

import boto3
from models import DataQualityParams, ModelBiasParams, ModelExplainabilityParams, ModelQualityParams
from sagemaker.clarify import BiasConfig, DataConfig, ModelConfig, ModelPredictedLabelConfig, SHAPConfig
from sagemaker.model_monitor import (
    DefaultModelMonitor,
    ModelBiasMonitor,
    ModelExplainabilityMonitor,
    ModelQualityMonitor,
)
from sagemaker.model_monitor.dataset_format import DatasetFormat

SAGEMAKER_ROLE_ARN = os.environ["SAGEMAKER_ROLE_ARN"]

sagemaker = boto3.client("sagemaker")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SageMaker Model Monitor baselining jobs."""

    action = event.get("action", "start")

    if action == "start":
        return start_baselining_job(event)
    elif action == "check":
        return check_baselining_job(event)

    return {"statusCode": 200}


def start_baselining_job(event: Dict[str, Any]) -> Dict[str, Any]:
    """Start a baselining processing job."""

    monitor_type = event["monitor_type"]
    endpoint_name = event["endpoint_name"]
    training_data_uri = event["training_data_uri"]
    baseline_output_uri = event["baseline_output_uri"]

    if monitor_type == "data_quality":
        job_name = f"{endpoint_name}-data-quality-baseline"
        params = DataQualityParams(**event.get("data_quality_params", {}))

        monitor = DefaultModelMonitor(
            role=SAGEMAKER_ROLE_ARN,
            instance_count=params.instance_count,
            instance_type=params.instance_type,
            volume_size_in_gb=params.volume_size_gb,
            max_runtime_in_seconds=params.max_runtime_seconds,
        )

        monitor.suggest_baseline(
            baseline_dataset=training_data_uri,
            dataset_format=DatasetFormat.csv(header=True),
            output_s3_uri=baseline_output_uri,
            wait=False,
            logs=False,
        )

        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}

    elif monitor_type == "model_quality":
        job_name = f"{endpoint_name}-model-quality-baseline"
        params = ModelQualityParams(**event.get("model_quality_params", {}))

        monitor = ModelQualityMonitor(
            role=SAGEMAKER_ROLE_ARN,
            instance_count=params.instance_count,
            instance_type=params.instance_type,
            volume_size_in_gb=params.volume_size_gb,
            max_runtime_in_seconds=params.max_runtime_seconds,
        )

        monitor.suggest_baseline(
            job_name=job_name,
            baseline_dataset=training_data_uri,
            dataset_format=DatasetFormat.csv(header=True),
            output_s3_uri=baseline_output_uri,
            problem_type=params.problem_type,
            inference_attribute=params.inference_attribute,
            probability_attribute=params.probability_attribute,
            ground_truth_attribute=params.ground_truth_attribute,
            wait=False,
            logs=False,
        )

        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}

    elif monitor_type == "model_bias":
        job_name = f"{endpoint_name}-model-bias-baseline"
        params = ModelBiasParams(**event.get("model_bias_params", {}))

        monitor = ModelBiasMonitor(
            role=SAGEMAKER_ROLE_ARN,
            max_runtime_in_seconds=params.max_runtime_seconds,
        )

        model_bias_data_config = DataConfig(
            s3_data_input_path=training_data_uri,
            s3_output_path=baseline_output_uri,
            label=params.label_header,
            headers=params.get_headers(),
            dataset_type=params.dataset_type,
        )

        model_bias_config = BiasConfig(
            label_values_or_threshold=params.get_label_values(),
            facet_name=params.facet_name,
            facet_values_or_threshold=params.get_facet_values(),
        )

        model_predicted_label_config = ModelPredictedLabelConfig(
            probability_threshold=params.probability_threshold,
        )

        model_config = ModelConfig(
            model_name=params.model_name or endpoint_name,
            instance_count=params.instance_count,
            instance_type=params.instance_type,
            content_type=params.dataset_type,
            accept_type=params.dataset_type,
        )

        monitor.suggest_baseline(
            model_config=model_config,
            data_config=model_bias_data_config,
            bias_config=model_bias_config,
            model_predicted_label_config=model_predicted_label_config,
            wait=False,
            logs=False,
        )

        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}

    elif monitor_type == "model_explainability":
        job_name = f"{endpoint_name}-model-explainability-baseline"
        params = ModelExplainabilityParams(**event.get("model_explainability_params", {}))

        monitor = ModelExplainabilityMonitor(
            role=SAGEMAKER_ROLE_ARN,
            max_runtime_in_seconds=params.max_runtime_seconds,
        )

        model_explainability_data_config = DataConfig(
            s3_data_input_path=training_data_uri,
            s3_output_path=baseline_output_uri,
            label=params.label_header,
            headers=params.get_headers(),
            dataset_type=params.dataset_type,
        )

        # Use configurable SHAP baseline
        shap_config = SHAPConfig(
            baseline=params.shap_baseline,
            num_samples=params.num_samples,
            agg_method=params.agg_method,
            save_local_shap_values=params.save_local_shap_values,
        )

        model_config = ModelConfig(
            model_name=params.model_name or endpoint_name,
            instance_count=params.instance_count,
            instance_type=params.instance_type,
            content_type=params.dataset_type,
            accept_type=params.dataset_type,
        )

        monitor.suggest_baseline(
            data_config=model_explainability_data_config,
            model_config=model_config,
            explainability_config=shap_config,
        )

        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}

    return {"statusCode": 400, "error": f"Unsupported monitor_type: {monitor_type}"}


def check_baselining_job(event: Dict[str, Any]) -> Dict[str, Any]:
    """Check the status of a baselining processing job."""

    job_name = event["job_name"]

    response = sagemaker.describe_processing_job(ProcessingJobName=job_name)
    status = response["ProcessingJobStatus"]

    return {"statusCode": 200, "job_name": job_name, "status": "COMPLETED" if status == "Completed" else "IN_PROGRESS"}
