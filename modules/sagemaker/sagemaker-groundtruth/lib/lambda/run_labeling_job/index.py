import boto3
import json
import os
from urllib.parse import urlparse
from datetime import datetime
import logging
from collections import namedtuple

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource("s3")
s3_client = boto3.client("s3")
sagemaker_client = boto3.client("sagemaker")
region = boto3.session.Session().region_name
SFN = boto3.client("stepfunctions")

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
TASK_DESCRIPTION = "Dear Annotator, please draw a box around each scratch. Thank you!"
TASK_KEYWORDS = ["image", "object", "detection"]
TASK_TITLE = "Please draw a box around each scratch"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


LabelingjobConfig = namedtuple(
    "LabelingjobConfig",
    "missing_labels max_labels_per_labeling_job use_private_workteam execution_id role workteam_arn instructions_template_s3_uri label_categories_uri output_uri",
)


def handler(event, context):
    logger.info(f"# event={json.dumps(event)} , Environment {os.environ}")
    config = get_step_config(event)
    logger.info(f"StepConfig: {config}")
    missing_labels = config.missing_labels
    # Enforcing max number of labels to ensure we can manually inspect labels easily
    if len(missing_labels) > config.max_labels_per_labeling_job:
        missing_labels = missing_labels[0 : config.max_labels_per_labeling_job]

    # generate and upload manifest
    manifest_uri = create_and_upload_manifest(
        images=missing_labels,
        manifest_name=f"{config.execution_id}.manifest",
        labeling_job_s3_uri=config.output_uri,
    )
    # create labeling job
    labeling_job_config = create_labeling_job_config(config, manifest_uri)

    logger.info(labeling_job_config)
    response = sagemaker_client.create_labeling_job(**labeling_job_config)
    logger.info(f"Kicked off labeling job {response}")
    return {
        "LabelingJobName": f"quality-inspection-labeling-job-{config.execution_id[:6]}"
    }


def get_step_config(event) -> LabelingjobConfig:
    # file containing list of missing labels
    missing_labels = event["request"]["Payload"]["missing_labels"]

    max_labels_per_labeling_job = int(os.environ.get("MAX_LABELS"))
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

    if use_private_workteam.lower() == "true":
        if "PRIVATE_WORKTEAM_ARN" in os.environ:
            workteam_arn = os.environ.get("PRIVATE_WORKTEAM_ARN")
        else:
            raise Exception(
                "USE_PRIVATE_WORKTEAM set to True, make sure to also specify parameter 'PRIVATE_WORKTEAM_ARN'"
            )

    instructions_template_s3_uri = (
        f"s3://{bucket}/{bucket_prefix}/groundtruth/labeling_job/instructions.template"
    )
    label_categories_uri = (
        f"s3://{bucket}/{bucket_prefix}/groundtruth/labeling_job/class_labels.json"
    )
    output_uri = f"s3://{bucket}/{bucket_prefix}/runs/{execution_id}/"

    return LabelingjobConfig(
        missing_labels,
        max_labels_per_labeling_job,
        use_private_workteam,
        execution_id,
        role,
        workteam_arn,
        instructions_template_s3_uri,
        label_categories_uri,
        output_uri,
    )


def create_and_upload_manifest(
    images=None, manifest_name="input.manifest", labeling_job_s3_uri=""
):
    parsed_url = urlparse(labeling_job_s3_uri, allow_fragments=False)
    bucket = parsed_url.netloc
    prefix = parsed_url.path[1:]
    tmp_file = f"/tmp/{manifest_name}"
    with open(tmp_file, "w") as f:
        for file in images:
            line = f'{{"source-ref": "{file}"}}\n'
            f.write(line)

    logger.info(f"Uploading manifest-file to s3://{bucket}/{prefix}/{manifest_name}")
    s3.meta.client.upload_file(
        Filename=tmp_file, Bucket=bucket, Key=f"{prefix}/{manifest_name}"
    )
    return f"s3://{bucket}/{prefix}/{manifest_name}"


def create_labeling_job_config(config: LabelingjobConfig, manifest_uri):
    region = boto3.session.Session().region_name
    prehuman_arn = "arn:aws:lambda:{}:{}:function:PRE-BoundingBox".format(
        region, AC_ARN_MAP[region]
    )
    acs_arn = "arn:aws:lambda:{}:{}:function:ACS-BoundingBox".format(
        region, AC_ARN_MAP[region]
    )
    job_name = f"quality-inspection-labeling-job-{config.execution_id[:6]}"

    human_task_config = {
        "AnnotationConsolidationConfig": {
            "AnnotationConsolidationLambdaArn": acs_arn,
        },
        "PreHumanTaskLambdaArn": prehuman_arn,
        # 200 images will be sent at a time to the workteam.
        "MaxConcurrentTaskCount": 200,
        # We will obtain and consolidate 1 human annotations for each image.
        "NumberOfHumanWorkersPerDataObject": 1,
        # Your workteam has 1 hour to complete all pending tasks.
        "TaskAvailabilityLifetimeInSeconds": 3600,
        "TaskDescription": TASK_DESCRIPTION,
        "TaskKeywords": TASK_KEYWORDS,
        # Each image must be labeled within 3 minutes.
        "TaskTimeLimitInSeconds": 180,
        "TaskTitle": TASK_TITLE,
        "WorkteamArn": config.workteam_arn,
        "UiConfig": {"UiTemplateS3Uri": config.instructions_template_s3_uri},
    }
    if config.use_private_workteam.lower() != "true":
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
            "DataSource": {"S3DataSource": {"ManifestS3Uri": manifest_uri}},
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
        "LabelAttributeName": "category",
        "LabelCategoryConfigS3Uri": config.label_categories_uri,
    }

    return ground_truth_request
