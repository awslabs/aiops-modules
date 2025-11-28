import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_sagemaker_modules():
    """Mock sagemaker modules for these tests only."""
    # Set environment variables
    os.environ["SAGEMAKER_ROLE_ARN"] = "arn:aws:iam::123456789012:role/test-role"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # Store original modules
    original_modules = {}
    sagemaker_module_names = [
        "sagemaker",
        "sagemaker.clarify",
        "sagemaker.model_monitor",
        "sagemaker.model_monitor.dataset_format",
    ]

    for module_name in sagemaker_module_names:
        if module_name in sys.modules:
            original_modules[module_name] = sys.modules[module_name]

    # Mock the sagemaker modules
    sys.modules["sagemaker"] = MagicMock()
    sys.modules["sagemaker.clarify"] = MagicMock()
    sys.modules["sagemaker.model_monitor"] = MagicMock()
    sys.modules["sagemaker.model_monitor.dataset_format"] = MagicMock()

    # Add lambda path
    lambda_path = "sagemaker_model_monitoring/lambda"
    if lambda_path not in sys.path:
        sys.path.insert(0, lambda_path)

    # Import after mocking
    from baselining_handler import check_baselining_job, lambda_handler

    yield check_baselining_job, lambda_handler

    # Restore original modules
    for module_name in sagemaker_module_names:
        if module_name in original_modules:
            sys.modules[module_name] = original_modules[module_name]
        else:
            sys.modules.pop(module_name, None)

    # Remove lambda path
    if lambda_path in sys.path:
        sys.path.remove(lambda_path)

    # Clean up imported handler module
    if "baselining_handler" in sys.modules:
        del sys.modules["baselining_handler"]


@pytest.fixture
def mock_env():
    """Environment variables are already set in mock_sagemaker_modules."""
    pass


@pytest.fixture
def mock_sagemaker_client():
    """Mock boto3 SageMaker client."""
    with patch("baselining_handler.sagemaker") as mock_client:
        yield mock_client


def test_lambda_handler_check_action(mock_sagemaker_modules, mock_env, mock_sagemaker_client):
    """Test lambda_handler with check action."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules
    event = {"action": "check", "job_name": "test-job"}

    mock_sagemaker_client.describe_processing_job.return_value = {"ProcessingJobStatus": "Completed"}

    result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    assert result["status"] == "COMPLETED"
    assert result["job_name"] == "test-job"


@pytest.mark.parametrize(
    "processing_job_status,expected_status",
    [
        ("Completed", "COMPLETED"),
        ("Failed", "FAILED"),
        ("InProgress", "IN_PROGRESS"),
        ("Stopping", "FAILED"),
        ("Stopped", "FAILED"),
    ],
)
def test_check_baselining_job_status(
    mock_sagemaker_modules, mock_env, mock_sagemaker_client, processing_job_status, expected_status
):
    """Test check_baselining_job with various job statuses."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules
    event = {"job_name": "test-job"}

    mock_sagemaker_client.describe_processing_job.return_value = {"ProcessingJobStatus": processing_job_status}

    result = check_baselining_job(event)

    assert result["statusCode"] == 200
    assert result["status"] == expected_status
    assert result["job_name"] == "test-job"


def test_check_baselining_job_missing_job_name(mock_sagemaker_modules, mock_env):
    """Test check_baselining_job with missing job_name."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules
    event = {}

    result = check_baselining_job(event)

    assert result["statusCode"] == 400
    assert "error" in result
    assert "Missing required parameter" in result["error"]


@pytest.mark.parametrize(
    "monitor_type,monitor_class_path,expected_job_name",
    [
        ("data_quality", "baselining_handler.DefaultModelMonitor", "data-quality-job-123"),
        ("model_quality", "baselining_handler.ModelQualityMonitor", "model-quality-job-456"),
        ("model_bias", "baselining_handler.ModelBiasMonitor", "model-bias-job-789"),
        ("model_explainability", "baselining_handler.ModelExplainabilityMonitor", "model-explainability-job-012"),
    ],
)
def test_start_baselining_job_types(
    mock_sagemaker_modules, mock_env, monitor_type, monitor_class_path, expected_job_name
):
    """Test starting different types of baselining jobs."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules

    event = {
        "action": "start",
        "monitor_type": monitor_type,
        "endpoint_name": "test-endpoint",
        "training_data_uri": "s3://bucket/training-data",
        "baseline_output_uri": "s3://bucket/baseline-output",
    }

    with patch(monitor_class_path) as mock_monitor_class:
        mock_monitor_instance = MagicMock()
        mock_monitor_class.return_value = mock_monitor_instance

        # Mock the baselining job
        mock_baselining_job = MagicMock()
        mock_baselining_job.job_name = expected_job_name
        mock_monitor_instance.latest_baselining_job = mock_baselining_job

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        assert result["status"] == "STARTED"
        assert result["job_name"] == expected_job_name

        # Verify the monitor was instantiated
        mock_monitor_class.assert_called_once()

        # Verify suggest_baseline was called
        mock_monitor_instance.suggest_baseline.assert_called_once()
