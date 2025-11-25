import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_sagemaker_modules():
    """Mock sagemaker modules for these tests only."""
    # Set environment variable
    os.environ["SAGEMAKER_ROLE_ARN"] = "arn:aws:iam::123456789012:role/test-role"
    
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


def test_check_baselining_job_completed(mock_sagemaker_modules, mock_env, mock_sagemaker_client):
    """Test check_baselining_job with completed job."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules
    event = {"job_name": "test-job"}

    mock_sagemaker_client.describe_processing_job.return_value = {"ProcessingJobStatus": "Completed"}

    result = check_baselining_job(event)

    assert result["statusCode"] == 200
    assert result["status"] == "COMPLETED"
    assert result["job_name"] == "test-job"


def test_check_baselining_job_in_progress(mock_sagemaker_modules, mock_env, mock_sagemaker_client):
    """Test check_baselining_job with in-progress job."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules
    event = {"job_name": "test-job"}

    mock_sagemaker_client.describe_processing_job.return_value = {"ProcessingJobStatus": "InProgress"}

    result = check_baselining_job(event)

    assert result["statusCode"] == 200
    assert result["status"] == "IN_PROGRESS"
    assert result["job_name"] == "test-job"


def test_check_baselining_job_missing_job_name(mock_sagemaker_modules, mock_env):
    """Test check_baselining_job with missing job_name."""
    check_baselining_job, lambda_handler = mock_sagemaker_modules
    event = {}

    result = check_baselining_job(event)

    assert result["statusCode"] == 400
    assert "error" in result
    assert "Missing required parameter" in result["error"]
