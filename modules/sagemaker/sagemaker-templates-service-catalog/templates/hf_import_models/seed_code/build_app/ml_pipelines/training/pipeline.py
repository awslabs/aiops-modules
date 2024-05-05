import json
import logging
import os
from typing import Any, Optional

import boto3
import sagemaker
import sagemaker.session
from botocore.exceptions import ClientError
from sagemaker.huggingface import HuggingFaceModel, get_huggingface_llm_image_uri
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.step_collections import RegisterModel

logger = logging.getLogger(__name__)
ACCESS_TOKEN_SECRET = os.environ["HUGGING_FACE_ACCESS_TOKEN_SECRET"]  # read token from secret using boto3
SECRET_REGION = os.environ["AWS_REGION"]


def get_acess_token_from_secret(secretid: str, secret_region: str) -> Any:
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=secret_region)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secretid)
    except ClientError as e:
        raise e

    # Get the secret value
    secret_value = get_secret_value_response["SecretString"]
    return secret_value


ACCESS_TOKEN = get_acess_token_from_secret(ACCESS_TOKEN_SECRET, SECRET_REGION)


def get_session(region: str, default_bucket: Optional[str]) -> sagemaker.session.Session:
    """Gets the sagemaker session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        `sagemaker.session.Session instance
    """

    boto_session = boto3.Session(region_name=region)

    sagemaker_client = boto_session.client("sagemaker")
    runtime_client = boto_session.client("sagemaker-runtime")
    session = sagemaker.session.Session(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        sagemaker_runtime_client=runtime_client,
        default_bucket=default_bucket,
    )

    return session


def get_pipeline(
    region: str,
    hugging_face_model_id: str,
    role: Optional[str] = None,
    default_bucket: Optional[str] = None,
    model_package_group_name: str = "AbalonePackageGroup",
    pipeline_name: str = "AbalonePipeline",
    project_id: str = "SageMakerProjectId",
) -> Any:
    sagemaker_session = get_session(region, default_bucket)
    if role is None:
        role = sagemaker.session.get_execution_role(sagemaker_session)

    # parameters for pipeline execution
    model_approval_status = ParameterString(name="ModelApprovalStatus", default_value="PendingManualApproval")

    inference_image_uri = get_huggingface_llm_image_uri("huggingface", version="0.9.3")
    llm_model = HuggingFaceModel(
        role=role,
        image_uri=inference_image_uri,
        env={
            "HF_MODEL_ID": hugging_face_model_id,  # model_id from hf.co/models
            "SM_NUM_GPUS": json.dumps(1),  # Number of GPU used per replica
            "MAX_INPUT_LENGTH": json.dumps(2048),  # Max length of input text
            "MAX_TOTAL_TOKENS": json.dumps(4096),  # Max length of the generation (including input text)
            "MAX_BATCH_TOTAL_TOKENS": json.dumps(
                8192
            ),  # Limits the number of tokens that can be processed in parallel during the generation
            "HUGGING_FACE_HUB_TOKEN": ACCESS_TOKEN,
            # ,'HF_MODEL_QUANTIZE': "bitsandbytes",           # comment in to quantize
        },
    )

    step_register = RegisterModel(
        name="RegisterModel",
        model=llm_model,
        # estimator=xgb_train,
        # image_uri=inference_image_uri,
        # model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.g5.2xlarge", "ml.g5.12xlarge"],
        # transform_instances=["ml.g5.12xlarge", "ml.p4d.24xlarge"],
        model_package_group_name=model_package_group_name,
        approval_status=model_approval_status,
    )

    # pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            model_approval_status,
        ],
        steps=[step_register],
        sagemaker_session=sagemaker_session,
    )
    return pipeline
