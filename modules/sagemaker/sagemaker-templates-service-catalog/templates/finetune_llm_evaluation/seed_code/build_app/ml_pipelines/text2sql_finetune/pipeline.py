"""Example workflow pipeline script for Text-to-SQL pipeline using Hugging Face and CodeLlama.

                                               . - ModelStep and Register Model
                                              .
    Process Data -> Train  -> Evaluate -> Condition .
                                              .
                                               . - (stop)

Implements a get_pipeline(**kwargs) method.
"""

import logging
from typing import Any, Optional

import boto3
import sagemaker
import sagemaker.session
from sagemaker.huggingface import (
    HuggingFace,
    HuggingFaceModel,
    HuggingFaceProcessor,
    get_huggingface_llm_image_uri,
)
from sagemaker.inputs import TrainingInput
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.parameters import (
    ParameterFloat,
    ParameterInteger,
    ParameterString,
)
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

# from sagemaker.workflow.steps import CacheConfig # Enable to debug specific steps if previous steps were succesful


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

SCRIPTS_DIR_PATH = "source_scripts"


def get_sagemaker_client(region: str) -> Any:
    """Gets the sagemaker client.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        `sagemaker.session.Session instance
    """
    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")
    return sagemaker_client


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
    return sagemaker.session.Session(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        sagemaker_runtime_client=runtime_client,
        default_bucket=default_bucket,
    )


def get_pipeline_session(region: str, default_bucket: Optional[str]) -> PipelineSession:
    """Gets the pipeline session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        PipelineSession instance
    """

    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")

    return PipelineSession(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        default_bucket=default_bucket,
    )


def get_pipeline_custom_tags(new_tags: Any, region: str, sagemaker_project_name: Optional[str] = None) -> Any:
    try:
        sm_client = get_sagemaker_client(region)
        response = sm_client.describe_project(ProjectName=sagemaker_project_name)
        sagemaker_project_arn = response["ProjectArn"]
        response = sm_client.list_tags(ResourceArn=sagemaker_project_arn)
        project_tags = response["Tags"]
        for project_tag in project_tags:
            new_tags.append(project_tag)
    except Exception as e:
        logger.error(f"Error getting project tags: {e}")
    return new_tags


def get_pipeline(
    region: str,
    sagemaker_project_name: Optional[str] = None,
    role: Optional[str] = None,
    default_bucket: Optional[str] = None,
    bucket_kms_id: Optional[str] = None,
    model_package_group_name: str = "Text2SQLGenerationPackageGroup",
    pipeline_name: str = "Text2SQLSQLGenerationPipeline",
    base_job_prefix: str = "Text2sql",
    processing_instance_count: int = 1,
    processing_instance_type: str = "ml.g4dn.xlarge",  # small gpu instance for data preprocessing
    training_instance_type: str = "ml.g5.12xlarge",  # "ml.g5.24xlarge", # larger instance type for training if needed
    evaluation_instance_type: str = "ml.g4dn.12xlarge",
    transformers_version: str = "4.28.1",
    pytorch_version: str = "2.0.0",
    py_version: str = "py310",
) -> Pipeline:
    """Gets a SageMaker ML Pipeline instance to fine-tune LLMs with HuggingFace scripts.

    Args:

        region: AWS region to create and run the pipeline.
        sagemaker_project_name: sagemaker project name
        role: IAM role to create and run steps and pipeline.
        default_bucket: the bucket to use for storing the artifacts
        bucket_kms_id: bucket kms id
        model_package_group_name: model package group name
        pipeline_name: sagemaker pipeline name
        base_job_prefix: base job prefix
        processing_instance_count: number of processing instances to use
        training_instance_type: training instance type
        transformers_version: hugging face transformers package version
        pytorch_version: PyTorch version to use
        py_version: Python version to use


    Returns:
        an instance of a pipeline
    """
    sagemaker_session = get_session(region, default_bucket)
    if role is None:
        role = sagemaker.session.get_execution_role(sagemaker_session)

    pipeline_session = get_pipeline_session(region, default_bucket)

    logger.info(
        f"sagemaker_project_name : {sagemaker_project_name}, "
        f"bucket_kms_id : {bucket_kms_id}, default_bucket : {default_bucket}, role : {role}"
    )

    # parameters for pipeline execution
    processing_instance_count = ParameterInteger(name="ProcessingInstanceCount", default_value=1)

    model_approval_status = ParameterString(name="ModelApprovalStatus", default_value="PendingManualApproval")

    # condition step for evaluating model quality and branching execution
    acc_score_threshold = ParameterFloat(name="AccuracyScoreThreshold", default_value=0.0)  # Auto approve for test

    hf_model_id = ParameterString(name="HuggingFaceModel", default_value="codellama/CodeLlama-7b-hf")

    hf_dataset_name = ParameterString(name="HuggingFaceDataset", default_value="philikai/Spider-SQL-LLAMA2_train")

    # This parameter is used to test the entire pipeline and is useful for development and debugging.
    # If set to True, a small data sample will be selected to speed up pipeline execution.
    dry_run = ParameterString(name="DryRun", default_value="True")

    # cache_config = CacheConfig(enable_caching=True, expire_after="P1D")
    # # Enable to debug specific steps if previous steps were succesful

    ########################################## PREPROCESSING STEP #################################################

    hf_data_processor = HuggingFaceProcessor(
        instance_type=processing_instance_type,
        instance_count=processing_instance_count,
        transformers_version=transformers_version,
        pytorch_version=pytorch_version,
        py_version=py_version,
        base_job_name=f"{base_job_prefix}/preprocess-dataset",
        sagemaker_session=pipeline_session,
        role=role,
        output_kms_key=bucket_kms_id,
    )

    step_args = hf_data_processor.run(
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
            ProcessingOutput(output_name="test", source="/opt/ml/processing/test"),
        ],
        code="preprocess.py",
        source_dir=SCRIPTS_DIR_PATH,
        arguments=[
            "--dataset_name",
            hf_dataset_name,
            "--dry_run",
            dry_run,
        ],
    )

    step_process = ProcessingStep(
        name="LoadPreprocessSplitDataset",
        step_args=step_args,
        # cache_config=cache_config, # Enable to debug specific steps if previous steps were succesful
    )

    ########################################## TRAINING STEP #######################################################

    hyperparameters = {
        "model_id": hf_model_id,  # pre-trained model
        "epochs": 2,  # number of training epochs --> 1 is for fast testing.
        # Can be exposed as pipeline parameter for example.
        "per_device_train_batch_size": 4,  # batch size for training
        "lr": 1e-4,  # learning rate used during training
        "merge_weights": True,  # wether to merge LoRA into the model (needs more memory)
    }

    huggingface_estimator = HuggingFace(
        entry_point="train.py",  # train script
        source_dir=SCRIPTS_DIR_PATH,  # directory which includes all the files needed for training
        instance_type=training_instance_type,  # instances type used for the training job
        instance_count=1,  # the number of instances used for training
        base_job_name=f"{base_job_prefix}/training",  # the name of the training job
        role=role,  # Iam role used in training job to access AWS ressources, e.g. S3
        volume_size=300,  # the size of the EBS volume in GB
        transformers_version=transformers_version,  # the transformers version used in the training job
        pytorch_version=pytorch_version,  # the pytorch_version version used in the training job
        py_version=py_version,  # the python version used in the training job
        hyperparameters=hyperparameters,  # the hyperparameters passed to the training job
        sagemaker_session=pipeline_session,
        environment={"HUGGINGFACE_HUB_CACHE": "/tmp/.cache"},  # set env variable to cache models in /tmp
        keepAlivePeriod=600,
        output_kms_key=bucket_kms_id,
    )

    step_args = huggingface_estimator.fit(
        inputs={
            "training": TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri,
            )
        },
    )

    step_train = TrainingStep(
        name="FinetuneLLMSQLModel",
        step_args=step_args,
        # cache_config=cache_config, # Enable to debug specific steps if previous steps were succesful
    )

    ############ Evaluation Step ##############

    hf_evaluator = HuggingFaceProcessor(
        role=role,
        instance_count=processing_instance_count,
        instance_type=evaluation_instance_type,
        transformers_version=transformers_version,
        pytorch_version=pytorch_version,
        py_version=py_version,
        base_job_name=f"{base_job_prefix}/evaluation",
        sagemaker_session=pipeline_session,
        output_kms_key=bucket_kms_id,
    )

    # The evaluate.py defines several parameters as input args.
    # We are only passing the --dry-run parameter here as an example.
    # If you want to be able to change the other parameters at runtime,
    # please implement them as SageMaker pipeline paramets analougously to the
    # --dry-run parameter.
    step_args = hf_evaluator.run(
        code="evaluate.py",
        source_dir=SCRIPTS_DIR_PATH,
        arguments=[
            "--dry_run",
            dry_run,
        ],
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source=step_process.properties.ProcessingOutputConfig.Outputs["test"].S3Output.S3Uri,
                destination="/opt/ml/processing/test",
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/evaluation",
            ),
        ],
    )

    evaluation_report = PropertyFile(
        name="LLMEvaluationReport",
        output_name="evaluation",
        path="evaluation.json",
    )

    step_eval = ProcessingStep(
        name="EvaluateSQLModel",
        step_args=step_args,
        property_files=[evaluation_report],
        # cache_config=cache_config, # Enable to debug specific steps if previous steps were succesful
    )

    # ########## MODEL CREATION & REGISTRATION STEP #####

    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri="{}/evaluation.json".format(
                step_eval.arguments["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"]
            ),
            content_type="application/json",
        )
    )

    # Inference endpoint works with the tgi images which can be retrieved with
    # the get_huggingface_llm_image_uri() method
    llm_image = get_huggingface_llm_image_uri("huggingface", version="1.0.3")

    env = {
        "HF_MODEL_ID": "/opt/ml/model",
    }

    huggingface_model = HuggingFaceModel(
        name="LLMModel",
        image_uri=llm_image,
        env=env,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=pipeline_session,
        role=role,
        model_kms_key=bucket_kms_id,
    )

    step_args = huggingface_model.register(
        content_types=["application/json"],
        response_types=["application/json"],
        inference_instances=["ml.g4dn.xlarge", "ml.g4dn.8xlarge", "ml.g5.12xlarge"],
        transform_instances=["ml.g4dn.xlarge", "ml.g4dn.8xlarge", "ml.g5.12xlarge"],
        model_package_group_name=model_package_group_name,
        approval_status=model_approval_status,
        model_metrics=model_metrics,
    )

    step_register = ModelStep(
        name="TextToSQLLLM",
        step_args=step_args,
    )

    ########################################## CONDITION STEP #######################################################

    cond_gte = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=step_eval.name,
            property_file=evaluation_report,
            json_path="metrics.accuracy.value",
        ),
        right=acc_score_threshold,
    )

    step_cond = ConditionStep(
        name="CheckAccuracyScore",
        conditions=[cond_gte],
        if_steps=[step_register],
        else_steps=[],
    )

    # Create pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            processing_instance_type,
            processing_instance_count,
            training_instance_type,
            hf_model_id,
            hf_dataset_name,
            model_approval_status,
            acc_score_threshold,
            dry_run,
        ],
        steps=[step_process, step_train, step_eval, step_cond],
        sagemaker_session=pipeline_session,
    )
    return pipeline
