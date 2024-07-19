import boto3
import json
import os
from datetime import datetime
import logging
from collections import namedtuple

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource("s3")
s3_client = boto3.client("s3")
sagemaker_client = boto3.client("sagemaker")
region = boto3.session.Session().region_name

# map of lambda function Id, you can see the current list here:
# https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_AnnotationConsolidationConfig.html#SageMaker-Type-AnnotationConsolidationConfig-AnnotationConsolidationLambdaArn
AC_ARN_MAP = {
    "us-west-2": "081040173940",
    "us-east-1": "432418664414",
    "us-east-2": "266458841044",
    "eu-west-1": "568282634449",
    "eu-west-2": "487402164563",
    "eu-central-1": "203001061592",
    "ap-southeast-1": "377565633583",
    "ap-southeast-2": "454466003867",
    "ap-south-1": "565803892007",
    "ap-northeast-1": "477331159723",
    "ap-northeast-2": "845288260483",
    "ca-central-1": "918755190332",
}
TASK_DESCRIPTION = "Verify that scratches are correctly labeled"
TASK_KEYWORDS = ["Images", "object detection", "label verification", "bounding boxes"]
TASK_TITLE = "Label verification - Bounding boxes: Review the existing labels on the objects and choose the appropriate option."
TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
PUBLIC_WORKTEAM_ARN = (
    f"arn:aws:sagemaker:{region}:394669845002:workteam/public-crowd/default"
)

LabelingjobConfig = namedtuple(
    "LabelingjobConfig",
    "input_manifest use_private_workteam execution_id role workteam_arn instructions_template_s3_uri label_categories_uri output_uri",
)


def handler(event, context):
    logger.info(f"# event={json.dumps(event)} , Environment {os.environ}")
    config = get_step_config(event)
    logger.info(f"StepConfig: {config}")

    # create labeling job
    labeling_job_config = create_labeling_job_config(config)

    logger.info(labeling_job_config)
    response = sagemaker_client.create_labeling_job(**labeling_job_config)
    logger.info(f"Kicked off labeling job {response}")
    return {"LabelingJobName": labeling_job_config["LabelingJobName"]}


def get_step_config(event) -> LabelingjobConfig:
    # file containing list of missing labels
    input_manifest = event["input_manifest"]
    # bucket/path where the job should write temp assets to
    bucket = os.environ.get("BUCKET")
    bucket_prefix = os.environ.get("PREFIX")
    # the exectuion role used to kick off the labeling job
    role = os.environ.get("ROLE")
    # whether to use a private workteam
    use_private_workteam = os.environ.get("USE_PRIVATE_WORKTEAM")
    # execution id
    execution_id = event["executionId"].rsplit(":", 1)[-1]
    # setting workteam arn as public as default
    workteam_arn = (
        f"arn:aws:sagemaker:{region}:394669845002:workteam/public-crowd/default"
    )

    if use_private_workteam.lower() == "True".lower():
        if "PRIVATE_WORKTEAM_ARN" in os.environ:
            workteam_arn = os.environ.get("PRIVATE_WORKTEAM_ARN")
        else:
            raise Exception(
                "USE_PRIVATE_WORKTEAM set to True, make sure to also specify parameter 'PRIVATE_WORKTEAM_ARN'"
            )

    instructions_template_s3_uri = (
        f"s3://{bucket}/{bucket_prefix}/groundtruth/verification_job/template.liquid"
    )
    label_categories_uri = (
        f"s3://{bucket}/{bucket_prefix}/groundtruth/verification_job/data.json"
    )
    output_uri = f"s3://{bucket}/{bucket_prefix}/runs/{execution_id}/"

    return LabelingjobConfig(
        input_manifest,
        use_private_workteam,
        execution_id,
        role,
        workteam_arn,
        instructions_template_s3_uri,
        label_categories_uri,
        output_uri,
    )


def create_labeling_job_config(config: LabelingjobConfig):
    prehuman_arn = "arn:aws:lambda:{}:{}:function:PRE-VerificationBoundingBox".format(
        region, AC_ARN_MAP[region]
    )
    acs_arn = "arn:aws:lambda:{}:{}:function:ACS-VerificationBoundingBox".format(
        region, AC_ARN_MAP[region]
    )
    job_name = f"quality-inspection-verification-job-{config.execution_id[:6]}"

    human_task_config = {
        "AnnotationConsolidationConfig": {
            "AnnotationConsolidationLambdaArn": acs_arn,
        },
        "PreHumanTaskLambdaArn": prehuman_arn,
        # 200 images will be sent at a time to the workteam.
        "MaxConcurrentTaskCount": 1000,
        # We will obtain and consolidate 5 human annotations for each image.
        "NumberOfHumanWorkersPerDataObject": 1,
        # Your workteam has 6 hours to complete all pending tasks.
        "TaskAvailabilityLifetimeInSeconds": 43200,
        "TaskDescription": TASK_DESCRIPTION,
        "TaskKeywords": TASK_KEYWORDS,
        # Each image must be labeled within 5 minutes.
        "TaskTimeLimitInSeconds": 300,
        "TaskTitle": TASK_TITLE,
        "WorkteamArn": config.workteam_arn,
        "UiConfig": {"UiTemplateS3Uri": config.instructions_template_s3_uri},
    }
    if config.use_private_workteam.lower() == "False".lower():
        logger.info("Setting task price")
        human_task_config["PublicWorkforceTaskPrice"] = {
            "AmountInUsd": {
                "Dollars": 0,
                "Cents": 3,
                "TenthFractionsOfACent": 6,
            }
        }
    ground_truth_request = {
        "InputConfig": {
            "DataSource": {"S3DataSource": {"ManifestS3Uri": config.input_manifest}},
            "DataAttributes": {
                "ContentClassifiers": [
                    "FreeOfPersonallyIdentifiableInformation",
                    "FreeOfAdultContent",
                ]
            },
        },
        "OutputConfig": {"S3OutputPath": config.output_uri},
        "HumanTaskConfig": human_task_config,
        "LabelingJobName": job_name,
        "RoleArn": config.role,
        "LabelAttributeName": "verified",
        "LabelCategoryConfigS3Uri": config.label_categories_uri,
    }

    return ground_truth_request
