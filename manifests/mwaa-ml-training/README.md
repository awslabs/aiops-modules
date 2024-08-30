The module at 
```
manifests/mwaa-ml-training/deployment.yaml
```
deploys MWAA (Managed Workflows for Apache Airflow) and an example Machine Learning training DAG and the necessary resources for running Airflow DAGs. It includes an Amazon S3 bucket for storing DAG files and other assets, as well as an AWS Identity and Access Management (IAM) role with the required permissions for the DAGs to access AWS services.

## Architecture
The stack creates the following resources:

Amazon S3 Bucket : A versioned S3 bucket for storing DAG files, data, and other assets required by the DAGs. The bucket is encrypted using AWS Key Management Service (KMS) and has public access blocked for security.

IAM Role : An IAM role with permissions to access the S3 bucket and any other required AWS services (e.g., Amazon SageMaker, CloudWatch Logs). The role is assumed by the Amazon MWAA execution role, allowing the DAGs to access AWS resources securely.

SageMaker Execution Role : An IAM role with the 
AmazonSageMakerFullAccess
 managed policy attached, which is used by Amazon SageMaker for executing machine learning tasks.

The IAM roles created by the stack can optionally have a permissions boundary applied for additional security.

![MWAA Module Architecture](docs/aiops_mwaa_module.png "MWAA Module Architecture")

## Deployment
The stack is deployed as part of the overall Airflow deployment process. For deployment instructions, please refer to the [DEPLOYMENT.MD](DEPLOYMENT.md) file.

## Usage
After deploying the stack, the DAGs can access the S3 bucket and other AWS resources using the IAM role created by the stack. The DAG files can be uploaded to the S3 bucket, and the DAGs can be scheduled and executed using Amazon MWAA.

## Example DAG
Here's an example of how a DAG might use the resources created by the stack

```
from airflow import DAG
from airflow.providers.amazon.aws.operators.sagemaker import (
    SageMakerTrainingOperator,
    SageMakerModelOperator,
    SageMakerTransformOperator,
)
from airflow.utils.dates import days_ago

dag = DAG(
    dag_id="sagemaker_ml_pipeline",
    start_date=days_ago(1),
    schedule_interval=None,
)

# Training step
training = SageMakerTrainingOperator(
    task_id="train_model",
    estimator_type="xgboost",
    instance_count=1,
    instance_type="ml.m5.xlarge",
    output_path="{{ var.value.sagemaker_model_path }}",
    sagemaker_role_arn="{{ var.value.sagemaker_role_arn }}",
    base_job_name="xgboost-training",
    dag=dag,
)

# Model creation step
model = SageMakerModelOperator(
    task_id="create_model",
    model_data="{{ var.value.sagemaker_model_path }}/output/model.tar.gz",
    execution_role_arn="{{ var.value.sagemaker_role_arn }}",
    model_name="xgboost-model",
    dag=dag,
)

# Batch transform step
transform = SageMakerTransformOperator(
    task_id="batch_transform",
    model_name="xgboost-model",
    instance_count=1,
    instance_type="ml.m5.xlarge",
    output_path="{{ var.value.sagemaker_transform_path }}",
    transform_input="s3://{{ var.value.mlops_assets_bucket }}/data/test_data",
    sagemaker_role_arn="{{ var.value.sagemaker_role_arn }}",
    dag=dag,
)

training >> model >> transform
```
