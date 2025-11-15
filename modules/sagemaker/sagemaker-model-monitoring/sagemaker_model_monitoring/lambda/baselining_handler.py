import os
from typing import Any, Dict

import boto3
import pandas as pd
from sagemaker.model_monitor import DefaultModelMonitor, ModelQualityMonitor, ModelBiasMonitor, ModelExplainabilityMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat
from sagemaker.clarify import DataConfig, BiasConfig, ModelConfig, ModelPredictedLabelConfig, SHAPConfig

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

    if monitor_type == "data_quality":
        job_name = f"{endpoint_name}-data-quality-baseline"
        
        monitor = DefaultModelMonitor(
            role=os.environ["SAGEMAKER_ROLE_ARN"],
            instance_count=int(os.environ.get("BASELINE_INSTANCE_COUNT", "1")),
            instance_type=os.environ.get("BASELINE_INSTANCE_TYPE", "ml.m5.xlarge"),
            volume_size_in_gb=int(os.environ.get("BASELINE_VOLUME_SIZE_GB", "20")),
            max_runtime_in_seconds=int(os.environ.get("BASELINE_MAX_RUNTIME_SECONDS", "3600")),
        )

        monitor.suggest_baseline(
            baseline_dataset=os.environ["TRAINING_DATA_URI"],
            dataset_format=DatasetFormat.csv(header=True),
            output_s3_uri=os.environ["BASELINE_OUTPUT_URI"],
            wait=False,
            logs=False,
        )

        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}

    elif monitor_type == "model_quality":
        job_name = f"{endpoint_name}-model-quality-baseline"
        
        monitor = ModelQualityMonitor(
            role=os.environ["SAGEMAKER_ROLE_ARN"],
            instance_count=int(os.environ.get("BASELINE_INSTANCE_COUNT", "1")),
            instance_type=os.environ.get("BASELINE_INSTANCE_TYPE", "ml.m5.xlarge"),
            volume_size_in_gb=int(os.environ.get("BASELINE_VOLUME_SIZE_GB", "20")),
            max_runtime_in_seconds=int(os.environ.get("BASELINE_MAX_RUNTIME_SECONDS", "1800")),
        )

        monitor.suggest_baseline(
            job_name=job_name,
            baseline_dataset=os.environ["TRAINING_DATA_URI"],
            dataset_format=DatasetFormat.csv(header=True),
            output_s3_uri=os.environ["BASELINE_OUTPUT_URI"],
            problem_type=os.environ.get("MODEL_QUALITY_PROBLEM_TYPE", "BinaryClassification"),
            inference_attribute=os.environ.get("MODEL_QUALITY_INFERENCE_ATTRIBUTE", "prediction"),
            probability_attribute=os.environ.get("MODEL_QUALITY_PROBABILITY_ATTRIBUTE", "probability"),
            ground_truth_attribute=os.environ.get("MODEL_QUALITY_GROUND_TRUTH_ATTRIBUTE", "label"),
            wait=False,
            logs=False,
        )

        return {"statusCode": 200, "job_name": job_name, "status": "STARTED"}

    elif monitor_type == "model_bias":
        job_name = f"{endpoint_name}-model-bias-baseline"
        
        monitor = ModelBiasMonitor(
            role=os.environ["SAGEMAKER_ROLE_ARN"],
            max_runtime_in_seconds=int(os.environ.get("BASELINE_MAX_RUNTIME_SECONDS", "1800")),
        )

        model_bias_data_config = DataConfig(
            s3_data_input_path=os.environ["TRAINING_DATA_URI"],
            s3_output_path=os.environ["BASELINE_OUTPUT_URI"],
            label=os.environ.get("MODEL_BIAS_LABEL_HEADER", "label"),
            headers=os.environ.get("MODEL_BIAS_HEADERS", "").split(",") if os.environ.get("MODEL_BIAS_HEADERS") else None,
            dataset_type=os.environ.get("MODEL_BIAS_DATASET_TYPE", "text/csv"),
        )

        model_bias_config = BiasConfig(
            label_values_or_threshold=[int(x) for x in os.environ.get("MODEL_BIAS_LABEL_VALUES", "1").split(",")],
            facet_name=os.environ.get("MODEL_BIAS_FACET_NAME", "Account Length"),
            facet_values_or_threshold=[int(x) for x in os.environ.get("MODEL_BIAS_FACET_VALUES", "100").split(",")],
        )

        model_predicted_label_config = ModelPredictedLabelConfig(
            probability_threshold=float(os.environ.get("MODEL_BIAS_PROBABILITY_THRESHOLD", "0.8")),
        )

        model_config = ModelConfig(
            model_name=os.environ.get("MODEL_BIAS_MODEL_NAME", endpoint_name),
            instance_count=int(os.environ.get("BASELINE_INSTANCE_COUNT", "1")),
            instance_type=os.environ.get("BASELINE_INSTANCE_TYPE", "ml.m5.xlarge"),
            content_type=os.environ.get("MODEL_BIAS_DATASET_TYPE", "text/csv"),
            accept_type=os.environ.get("MODEL_BIAS_DATASET_TYPE", "text/csv"),
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
        
        monitor = ModelExplainabilityMonitor(
            role=os.environ["SAGEMAKER_ROLE_ARN"],
            max_runtime_in_seconds=int(os.environ.get("BASELINE_MAX_RUNTIME_SECONDS", "1800")),
        )

        model_explainability_data_config = DataConfig(
            s3_data_input_path=os.environ["TRAINING_DATA_URI"],
            s3_output_path=os.environ["BASELINE_OUTPUT_URI"],
            label=os.environ.get("MODEL_EXPLAINABILITY_LABEL_HEADER", "label"),
            headers=os.environ.get("MODEL_EXPLAINABILITY_HEADERS", "").split(",") if os.environ.get("MODEL_EXPLAINABILITY_HEADERS") else None,
            dataset_type=os.environ.get("MODEL_EXPLAINABILITY_DATASET_TYPE", "text/csv"),
        )

        # Use mean value of test dataset as SHAP baseline
        test_dataframe = pd.read_csv(os.environ["TRAINING_DATA_URI"], header=None)
        shap_baseline = [list(test_dataframe.mean())]

        shap_config = SHAPConfig(
            baseline=shap_baseline,
            num_samples=100,
            agg_method="mean_abs",
            save_local_shap_values=False,
        )

        model_config = ModelConfig(
            model_name=os.environ.get("MODEL_EXPLAINABILITY_MODEL_NAME", endpoint_name),
            instance_count=int(os.environ.get("BASELINE_INSTANCE_COUNT", "1")),
            instance_type=os.environ.get("BASELINE_INSTANCE_TYPE", "ml.m5.xlarge"),
            content_type=os.environ.get("MODEL_EXPLAINABILITY_DATASET_TYPE", "text/csv"),
            accept_type=os.environ.get("MODEL_EXPLAINABILITY_DATASET_TYPE", "text/csv"),
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
