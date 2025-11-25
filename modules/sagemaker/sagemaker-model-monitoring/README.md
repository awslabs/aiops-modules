# SageMaker Model Monitoring

## Description

This module creates SageMaker Model Monitoring jobs and monitoring schedules for (optionally) 
data quality, model quality, model bias, and model explainability. It requires a deployed model 
endpoint with data capture enabled.

Available monitoring types:

* Data Quality
* Model Quality
* Model Bias
* Model Explainability

### Baseline Generation

The module includes an optional automated baseline generation feature that creates baseline statistics and constraints for your monitoring jobs. When you provide training data, the module will:

1. Deploy a Step Functions state machine that orchestrates baseline generation
2. Run SageMaker Processing jobs to analyze your training data
3. Generate baseline statistics and constraints files
4. Store the baseline artifacts in your specified S3 location
5. Schedule automatic baseline regeneration (default: daily at 2 AM UTC)

The baseline generation uses a Lambda function deployed as a Docker container image to handle the SageMaker SDK dependencies efficiently.

Note that updating parameters will require replacing resources. Deployments may be delayed until any
running monitoring jobs complete (and the resources can be destroyed).

### Architecture

![SageMaker Model Monitoring Module Architecture](docs/_static/sagemaker-model-monitoring-module-architecture.png "SageMaker Model Monitoring Module Architecture")

1. **SageMaker Endpoint** - The deployed model endpoint being monitored
    - **WARNING**: Data capture must be enabled for monitoring to function
    - Captures inference requests and responses to S3

2. **Baseline Generation (Optional)** - Automated baseline creation workflow
    - **EventBridge Rule**: Triggers baseline generation on a schedule (default: daily at 2 AM UTC)
    - **Step Functions State Machine**: Orchestrates the baseline generation process
    - **Lambda Function (Docker)**: Invokes SageMaker Processing jobs for baseline calculation
    - **SageMaker Processing Jobs**: Analyze training data to generate baseline statistics and constraints
    - **S3 Baseline Output**: Stores generated baseline artifacts (constraints.json, statistics.json)

3. **Ground Truth Data (Optional)** - Required for model quality and bias monitoring
    - Actual "correct" labels created manually or by a workflow
    - Example: actual customer churn for churn prediction models
    - Stored in S3 and merged with captured inference data

4. **Monitoring Jobs and Schedules** - Continuous monitoring execution
    - **Monitoring Schedules**: Cron-based execution (minimum 1 hour interval)
    - **SageMaker Monitoring Jobs**: Compare captured data against baselines
    - Supports data quality, model quality, model bias, and model explainability monitoring

5. **Monitoring Outputs** - Results and alerts
    - **Violations Report**: Detailed violations file emitted to S3
    - **CloudWatch Metrics**: Some monitoring types emit metrics (e.g., data quality drift)
    - **CloudWatch Alarms**: Can be configured based on emitted metrics for automated alerting

### Input Parameters

#### Required

- `endpoint_name`: The name of the endpoint used to run the monitoring job. NOTE: The endpoint must have data capture enabled. Data capture location must be in the bucket provided by `model_bucket_arn` parameter below.
- `model_bucket_arn`: S3 bucket ARN for model, data capture, and monitoring artifacts. Used to provide IAM permissions for monitoring jobs. NOTE: All following S3 URIs must be under this bucket.

One or more of:

- `enable_data_quality_monitor`: True to enable the data quality monitoring job.
- `enable_model_quality_monitor`: True to enable the model quality monitoring job.
- `enable_model_bias_monitor`: True to enable the model bias monitoring job.
- `enable_model_explainability_monitor`: True to enable the model explainability monitoring job.

#### Optional

- `security_group_id`: The VPC security group IDs, should provide access to the given `subnet_ids`.
- `subnet_ids`: The ID of the subnets in the VPC to which you want to connect your training job or model.
- `kms_key_id`: The KMS key used to encrypted storage and output.
- `sagemaker_project_id`: SageMaker project id
- `sagemaker_project_name`: SageMaker project name
- `tags`: Dictionary of tags to apply to resources

#### Baseline Generation Parameters (Optional)

These parameters control the automated baseline generation feature:

- `baseline_training_data_s3_uri`: S3 URI for the training data used to generate baselines (e.g., `s3://bucket/path/to/training-data.csv`)
- `baseline_output_data_s3_uri`: S3 URI where baseline statistics and constraints will be stored (e.g., `s3://bucket/path/to/baseline-output/`)
- `baseline_instance_count`: Number of ML compute instances for baseline generation (default: 1)
- `baseline_instance_type`: ML compute instance type for baseline generation (default: "ml.m5.xlarge")
- `baseline_volume_size_gb`: Size of ML storage volume in GB for baseline generation (default: 20)
- `baseline_max_runtime_seconds`: Maximum runtime in seconds for baseline generation jobs (default: 3600)

**Note**: If `baseline_training_data_s3_uri` and `baseline_output_data_s3_uri` are provided, the module will automatically create a Step Functions state machine to generate and update baselines for all enabled monitoring types.

### Per-job Parameters

#### Data Quality Monitoring Job Parameters

- `data_quality_baseline_s3_uri`: S3 URI for baseline data quality statistics
- `data_quality_output_s3_uri`: S3 URI for data quality monitoring output
- `data_quality_instance_count`: Number of ML compute instances (default: 1)
- `data_quality_instance_type`: ML compute instance type (default: "ml.m5.large")
- `data_quality_instance_volume_size_in_gb`: Size of ML storage volume in GB (default: 20)
- `data_quality_max_runtime_in_seconds`: Maximum runtime in seconds (default: 3600)
- `data_quality_schedule_expression`: Cron expression for monitoring schedule (default: "cron(0 * ? * * *)")

#### Model Quality Monitoring Job Parameters

- `model_quality_baseline_s3_uri`: S3 URI for baseline model quality statistics
- `model_quality_output_s3_uri`: S3 URI for model quality monitoring output
- `model_quality_ground_truth_s3_uri`: S3 URI for ground truth data
- `model_quality_instance_count`: Number of ML compute instances (default: 1)
- `model_quality_instance_type`: ML compute instance type (default: "ml.m5.large")
- `model_quality_instance_volume_size_in_gb`: Size of ML storage volume in GB (default: 20)
- `model_quality_max_runtime_in_seconds`: Maximum runtime in seconds (default: 1800)
- `model_quality_problem_type`: Machine learning problem type (default: "Regression")
- `model_quality_inference_attribute`: Attribute representing the ground truth label
- `model_quality_probability_attribute`: Attribute representing class probability
- `model_quality_probability_threshold_attribute`: Threshold for class probability evaluation
- `model_quality_schedule_expression`: Cron expression for monitoring schedule (default: "cron(0 * ? * * *)")

#### Model Bias Monitoring Job Parameters

- `model_bias_baseline_s3_uri`: S3 URI for baseline model bias statistics
- `model_bias_output_s3_uri`: S3 URI for model bias monitoring output
- `model_bias_ground_truth_s3_uri`: S3 URI for ground truth data
- `model_bias_instance_count`: Number of ML compute instances (default: 1)
- `model_bias_instance_type`: ML compute instance type (default: "ml.m5.large")
- `model_bias_instance_volume_size_in_gb`: Size of ML storage volume in GB (default: 20)
- `model_bias_max_runtime_in_seconds`: Maximum runtime in seconds (default: 1800)
- `model_bias_features_attribute`: Attributes of input data that are input features
- `model_bias_inference_attribute`: Attribute representing the ground truth label
- `model_bias_probability_attribute`: Attribute representing class probability
- `model_bias_probability_threshold_attribute`: Threshold for class probability evaluation
- `model_bias_schedule_expression`: Cron expression for monitoring schedule (default: "cron(0 * ? * * *)")

#### Model Explainability Monitoring Job Parameters

- `model_explainability_baseline_s3_uri`: S3 URI for baseline model explainability statistics
- `model_explainability_output_s3_uri`: S3 URI for model explainability monitoring output
- `model_explainability_instance_count`: Number of ML compute instances (default: 1)
- `model_explainability_instance_type`: ML compute instance type (default: "ml.m5.large")
- `model_explainability_instance_volume_size_in_gb`: Size of ML storage volume in GB (default: 20)
- `model_explainability_max_runtime_in_seconds`: Maximum runtime in seconds (default: 1800)
- `model_explainability_features_attribute`: Attributes of input data that are input features
- `model_explainability_inference_attribute`: Attribute representing the ground truth label
- `model_explainability_probability_attribute`: Attribute representing class probability
- `model_explainability_schedule_expression`: Cron expression for monitoring schedule (default: "cron(0 * ? * * *)")

### Sample manifest declaration

#### Basic Monitoring (without baseline generation)

```yaml
name: monitoring
path: modules/sagemaker/sagemaker-model-monitoring
parameters:
  - name: sagemaker_project_id
    value: SF-DEMO-xgb-churn-pred-model-monitor-2025-10-23-19-11-16
  - name: sagemaker_project_name
    value: SF-DEMO-xgb-churn-pred-model-monitor-2025-10-23-19-11-16
  - name: model_bucket_arn
    value: arn:aws:s3:::sagemaker-us-east-2-<REDACTED>
  - name: endpoint_name
    value: DEMO-xgb-churn-pred-model-monitor-2025-10-23-19-11-16
  - name: enable_data_quality_monitor
    value: true
  - name: data_quality_schedule_expression
    value: cron(0 * ? * * *)
  - name: data_quality_baseline_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/SF-DEMO-xgb-churn-pred-model-monitor/baseline
  - name: data_quality_output_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/SF-DEMO-xgb-churn-pred-model-monitor/output
```

#### With Automated Baseline Generation

```yaml
name: monitoring
path: modules/sagemaker/sagemaker-model-monitoring
parameters:
  - name: sagemaker_project_id
    value: SF-DEMO-xgb-churn-pred-model-monitor-2025-10-23-19-11-16
  - name: sagemaker_project_name
    value: SF-DEMO-xgb-churn-pred-model-monitor-2025-10-23-19-11-16
  - name: model_bucket_arn
    value: arn:aws:s3:::sagemaker-us-east-2-<REDACTED>
  - name: endpoint_name
    value: DEMO-xgb-churn-pred-model-monitor-2025-10-23-19-11-16
  # Baseline generation parameters
  - name: baseline_training_data_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/training-data/train.csv
  - name: baseline_output_data_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/baselines/
  - name: baseline_instance_type
    value: ml.m5.xlarge
  - name: baseline_max_runtime_seconds
    value: 3600
  # Enable monitoring types
  - name: enable_data_quality_monitor
    value: true
  - name: enable_model_quality_monitor
    value: true
  # Data quality monitoring
  - name: data_quality_schedule_expression
    value: cron(0 * ? * * *)
  - name: data_quality_baseline_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/baselines/data-quality/
  - name: data_quality_output_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/monitoring-output/data-quality/
  # Model quality monitoring
  - name: model_quality_schedule_expression
    value: cron(0 * ? * * *)
  - name: model_quality_baseline_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/baselines/model-quality/
  - name: model_quality_output_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/monitoring-output/model-quality/
  - name: model_quality_ground_truth_s3_uri
    value: s3://sagemaker-us-east-2-<REDACTED>/ground-truth/
  - name: model_quality_problem_type
    value: BinaryClassification
```

### Sample Baseline Generation Events

#### Step Functions Event Examples

The baseline generation Step Functions state machine accepts events with the following structure. You can manually trigger the state machine with these event payloads:

**Data Quality Baseline:**
```json
{
  "monitor_type": "data_quality",
  "endpoint_name": "my-endpoint",
  "training_data_uri": "s3://my-bucket/training-data/train.csv",
  "baseline_output_uri": "s3://my-bucket/baselines/data-quality/",
  "data_quality_params": {
    "instance_count": 1,
    "instance_type": "ml.m5.xlarge",
    "volume_size_gb": 30,
    "max_runtime_seconds": 3600
  }
}
```

**Model Quality Baseline:**
```json
{
  "monitor_type": "model_quality",
  "endpoint_name": "my-endpoint",
  "training_data_uri": "s3://my-bucket/training-data/train.csv",
  "baseline_output_uri": "s3://my-bucket/baselines/model-quality/",
  "model_quality_params": {
    "instance_count": 1,
    "instance_type": "ml.m5.xlarge",
    "volume_size_gb": 30,
    "max_runtime_seconds": 1800,
    "problem_type": "BinaryClassification",
    "inference_attribute": "prediction",
    "probability_attribute": "probability",
    "ground_truth_attribute": "label"
  }
}
```

**Model Bias Baseline:**
```json
{
  "monitor_type": "model_bias",
  "endpoint_name": "my-endpoint",
  "training_data_uri": "s3://my-bucket/training-data/train.csv",
  "baseline_output_uri": "s3://my-bucket/baselines/model-bias/",
  "model_bias_params": {
    "instance_count": 1,
    "instance_type": "ml.m5.xlarge",
    "volume_size_gb": 30,
    "max_runtime_seconds": 1800,
    "label_header": "label",
    "headers": "feature1,feature2,feature3,label",
    "dataset_type": "text/csv",
    "label_values": "0,1",
    "facet_name": "feature1",
    "facet_values": "100,200",
    "probability_threshold": 0.8,
    "model_name": "my-model"
  }
}
```

**Model Explainability Baseline:**
```json
{
  "monitor_type": "model_explainability",
  "endpoint_name": "my-endpoint",
  "training_data_uri": "s3://my-bucket/training-data/train.csv",
  "baseline_output_uri": "s3://my-bucket/baselines/model-explainability/",
  "model_explainability_params": {
    "instance_count": 1,
    "instance_type": "ml.m5.xlarge",
    "volume_size_gb": 30,
    "max_runtime_seconds": 1800,
    "label_header": "label",
    "headers": "feature1,feature2,feature3,label",
    "dataset_type": "text/csv",
    "model_name": "my-model",
    "num_samples": 100,
    "agg_method": "mean_abs",
    "save_local_shap_values": false,
    "shap_baseline": [[0.0]]
  }
}
```

**Note**: All parameter fields within the `*_params` objects are optional and will use the defaults shown above if not provided.
