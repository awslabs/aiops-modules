"""
Airflow dag with Sagemaker Processing and Training Job
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from datetime import datetime

import boto3
from airflow import DAG
from airflow.operators.python import PythonOperator
from config import MLOPS_DATA_BUCKET, SAGEMAKER_EXECUTION_ROLE, DAG_EXECUTION_ROLE
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.inputs import TrainingInput
from sagemaker.session import Session
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.sklearn.processing import SKLearnProcessor

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2020, 1, 1),
}
dag = DAG("SciKitLearn_MLOps", default_args=default_args, schedule_interval=None)

pre_processing_input = (
    f"s3://sagemaker-sample-data-{os.environ['AWS_REGION']}/processing/census"
)
test_data_s3_path = f"s3://{MLOPS_DATA_BUCKET}/processing/test"
train_data_s3_path = f"s3://{MLOPS_DATA_BUCKET}/processing/train"
model_path = f"s3://{MLOPS_DATA_BUCKET}/train/models/"
eval_output_s3_path = f"s3://{MLOPS_DATA_BUCKET}/eval/output"


def get_assume_role_session(role_arn):
    sts = boto3.client("sts")
    response = sts.assume_role(RoleArn=role_arn, RoleSessionName="AssumeRoleSession1")
    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )


def pre_processing():
    sess = Session(
        boto_session=get_assume_role_session(DAG_EXECUTION_ROLE),
        default_bucket=MLOPS_DATA_BUCKET,
    )

    sklearn_processor = SKLearnProcessor(
        framework_version="0.20.0",
        role=SAGEMAKER_EXECUTION_ROLE,
        instance_type="ml.m5.xlarge",
        instance_count=1,
        sagemaker_session=sess,
    )

    processing_input = ProcessingInput(
        source=pre_processing_input,
        destination="/opt/ml/processing/input",
        input_name="input",
    )
    processing_train_output = ProcessingOutput(
        source="/opt/ml/processing/train",
        destination=train_data_s3_path,
        output_name="train",
    )
    processing_test_output = ProcessingOutput(
        source="/opt/ml/processing/test",
        destination=test_data_s3_path,
        output_name="test",
    )

    return sklearn_processor.run(
        code=os.path.join(os.path.dirname(__file__), "preprocessing.py"),
        inputs=[processing_input],
        outputs=[
            processing_train_output,
            processing_test_output,
        ],
        arguments=["--train-test-split-ratio", "0.2"],
        wait=True,
    )


def training():
    sess = Session(
        boto_session=get_assume_role_session(DAG_EXECUTION_ROLE),
        default_bucket=MLOPS_DATA_BUCKET,
    )
    sklearn = SKLearn(
        entry_point=os.path.join(os.path.dirname(__file__), "train.py"),
        framework_version="0.20.0",
        instance_type="ml.m5.xlarge",
        role=SAGEMAKER_EXECUTION_ROLE,
        output_path=model_path,
        sagemaker_session=sess,
    )
    training_input = TrainingInput(
        s3_data=train_data_s3_path,
    )
    sklearn.fit(inputs=training_input, wait=True)
    training_job_description = sklearn.jobs[-1].describe()
    model_data_s3_uri = "{}{}/{}".format(
        training_job_description["OutputDataConfig"]["S3OutputPath"],
        training_job_description["TrainingJobName"],
        "output/model.tar.gz",
    )
    return model_data_s3_uri


def evaluation(model_path):
    sess = Session(
        boto_session=get_assume_role_session(DAG_EXECUTION_ROLE),
        default_bucket=MLOPS_DATA_BUCKET,
    )

    sklearn_processor = SKLearnProcessor(
        framework_version="0.20.0",
        role=SAGEMAKER_EXECUTION_ROLE,
        instance_type="ml.m5.xlarge",
        instance_count=1,
        sagemaker_session=sess,
    )
    sklearn_processor.run(
        code=os.path.join(os.path.dirname(__file__), "evaluation.py"),
        inputs=[
            ProcessingInput(source=model_path, destination="/opt/ml/processing/model"),
            ProcessingInput(
                source=test_data_s3_path, destination="/opt/ml/processing/test"
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                destination=eval_output_s3_path,
                source="/opt/ml/processing/evaluation",
            )
        ],
    )


pre_processing_step = PythonOperator(
    task_id="pre_processing",
    python_callable=pre_processing,
    dag=dag,
)

training_step = PythonOperator(
    task_id="training",
    python_callable=training,
    dag=dag,
)

evaluation_step = PythonOperator(
    task_id="evaluation",
    python_callable=evaluation,
    dag=dag,
    op_args=["{{ task_instance.xcom_pull('training') }}"],
)

pre_processing_step >> training_step >> evaluation_step
