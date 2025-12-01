# mypy: disable-error-code="attr-defined,no-untyped-call,assignment,call-arg,no-any-return,union-attr"
import json
import logging
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

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger(__name__)

SAGEMAKER_ROLE_ARN = os.environ["SAGEMAKER_ROLE_ARN"]

sagemaker = boto3.client("sagemaker")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SageMaker Model Monitor baselining jobs."""
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        action = event.get("action", "start")
        logger.info(f"Action: {action}")

        if action == "start":
            return start_baselining_job(event)
        elif action == "check":
            return check_baselining_job(event)

        return {"statusCode": 200}
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        return {"statusCode": 400, "error": f"Missing required parameter: {e}"}
    except Exception as e:
        logger.exception(f"Internal error: {str(e)}")
        return {"statusCode": 500, "error": f"Internal error: {str(e)}"}


def start_data_quality_baseline(training_data_uri: str, baseline_output_uri: str, event: Dict[str, Any]) -> str:
    """Start data quality baseline job."""
    params = DataQualityParams(**event.get("data_quality_params", {}))
    logger.info(f"Data quality baseline params: {params.model_dump_json()}")

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
    job_name = monitor.latest_baselining_job.job_name
    logger.info(f"Started data quality baseline job: {job_name}")
    return job_name


def start_model_quality_baseline(training_data_uri: str, baseline_output_uri: str, event: Dict[str, Any]) -> str:
    """Start model quality baseline job."""
    params = ModelQualityParams(**event.get("model_quality_params", {}))
    logger.info(f"Model quality baseline params: {params.model_dump_json()}")

    monitor = ModelQualityMonitor(
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
        problem_type=params.problem_type,
        inference_attribute=params.inference_attribute,
        probability_attribute=params.probability_attribute,
        ground_truth_attribute=params.ground_truth_attribute,
        wait=False,
        logs=False,
    )
    job_name = monitor.latest_baselining_job.job_name
    logger.info(f"Started model quality baseline job: {job_name}")
    return job_name


def start_model_bias_baseline(
    training_data_uri: str, baseline_output_uri: str, endpoint_name: str, event: Dict[str, Any]
) -> str:
    """Start model bias baseline job."""
    params = ModelBiasParams(**event.get("model_bias_params", {}))
    logger.info(f"Model bias baseline params: {params.model_dump_json()}")

    monitor = ModelBiasMonitor(role=SAGEMAKER_ROLE_ARN, max_runtime_in_seconds=params.max_runtime_seconds)

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
    model_predicted_label_config = ModelPredictedLabelConfig(probability_threshold=params.probability_threshold)
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
    job_name = monitor.latest_baselining_job.job_name
    logger.info(f"Started model bias baseline job: {job_name}")
    return job_name


def start_model_explainability_baseline(
    training_data_uri: str, baseline_output_uri: str, endpoint_name: str, event: Dict[str, Any]
) -> str:
    """Start model explainability baseline job."""
    params = ModelExplainabilityParams(**event.get("model_explainability_params", {}))
    logger.info(f"Model explainability baseline params: {params.model_dump_json()}")

    monitor = ModelExplainabilityMonitor(role=SAGEMAKER_ROLE_ARN, max_runtime_in_seconds=params.max_runtime_seconds)

    model_explainability_data_config = DataConfig(
        s3_data_input_path=training_data_uri,
        s3_output_path=baseline_output_uri,
        label=params.label_header,
        headers=params.get_headers(),
        dataset_type=params.dataset_type,
    )
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
    job_name = monitor.latest_baselining_job.job_name
    logger.info(f"Started model explainability baseline job: {job_name}")
    return job_name


def start_baselining_job(event: Dict[str, Any]) -> Dict[str, Any]:
    """Start a baselining processing job."""
    try:
        monitor_type = event["monitor_type"]
        endpoint_name = event["endpoint_name"]
        training_data_uri = event["training_data_uri"]
        baseline_output_uri = event["baseline_output_uri"]

        logger.info(
            f"Starting baselining job - Monitor type: {monitor_type}, Endpoint: {endpoint_name}, "
            f"Training URI: {training_data_uri}, Output URI: {baseline_output_uri}"
        )
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        return {"statusCode": 400, "error": f"Missing required parameter: {e}"}

    try:
        job_name = None
        if monitor_type == "data_quality":
            job_name = start_data_quality_baseline(training_data_uri, baseline_output_uri, event)
        elif monitor_type == "model_quality":
            job_name = start_model_quality_baseline(training_data_uri, baseline_output_uri, event)
        elif monitor_type == "model_bias":
            job_name = start_model_bias_baseline(training_data_uri, baseline_output_uri, endpoint_name, event)
        elif monitor_type == "model_explainability":
            job_name = start_model_explainability_baseline(training_data_uri, baseline_output_uri, endpoint_name, event)
        else:
            logger.error(f"Unsupported monitor_type: {monitor_type}")
            return {"statusCode": 400, "error": f"Unsupported monitor_type: {monitor_type}"}

        logger.info(f"Successfully started baselining job: {job_name}")
        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}
    except Exception as e:
        logger.exception(f"Failed to start baseline job: {str(e)}")
        return {"statusCode": 500, "error": f"Failed to start baseline job: {str(e)}"}


def check_baselining_job(event: Dict[str, Any]) -> Dict[str, Any]:
    """Check the status of a baselining processing job."""
    try:
        job_name = event["job_name"]
        logger.info(f"Checking status for job: {job_name}")

        response = sagemaker.describe_processing_job(ProcessingJobName=job_name)
        status = response["ProcessingJobStatus"]
        logger.info(f"Job {job_name} status: {status}")

        # Map SageMaker processing job statuses to simplified states
        if status == "Completed":
            logger.info(f"Job {job_name} completed successfully")
            return {"statusCode": 200, "job_name": job_name, "status": "COMPLETED"}
        elif status in ["Failed", "Stopped", "Stopping"]:
            failure_reason = response.get("FailureReason", "Unknown failure reason")
            logger.error(f"Job {job_name} failed: {failure_reason}")
            return {
                "statusCode": 200,
                "job_name": job_name,
                "status": "FAILED",
                "failure_reason": failure_reason,
            }
        else:  # InProgress
            logger.info(f"Job {job_name} still in progress")
            return {"statusCode": 200, "job_name": job_name, "status": "IN_PROGRESS"}
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        return {"statusCode": 400, "error": f"Missing required parameter: {e}"}
    except sagemaker.exceptions.ResourceNotFound:
        logger.error(f"Processing job not found: {event.get('job_name', 'unknown')}")
        return {"statusCode": 404, "error": f"Processing job not found: {event.get('job_name', 'unknown')}"}
    except Exception as e:
        logger.exception(f"Failed to check job status: {str(e)}")
        return {"statusCode": 500, "error": f"Failed to check job status: {str(e)}"}
