import json
import logging
import os
from typing import Any, Dict, List, Tuple

import boto3
from _utils import (
    create_labeling_job,
    download_json_dict_from_s3,
    get_s3_string_object_from_uri,
    upload_json_to_s3,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
SOURCE_KEY = os.environ["SOURCE_KEY"]
VERIFICATION_JOB_NAME = os.environ["VERIFICATION_JOB_NAME"]
HUMAN_TASK_CONFIG = json.loads(os.environ["HUMAN_TASK_CONFIG"])
AWS_REGION = os.environ["AWS_REGION"]
AC_ARN_MAP = json.loads(os.environ["AC_ARN_MAP"])
FUNCTION_NAME = os.environ["FUNCTION_NAME"]
TASK_TITLE = os.environ["TASK_TITLE"]
TASK_DESCRIPTION = os.environ["TASK_DESCRIPTION"]
TASK_KEYWORDS = json.loads(os.environ["TASK_KEYWORDS"])
WORKTEAM_ARN = os.environ["WORKTEAM_ARN"]
TASK_PRICE = json.loads(os.environ["TASK_PRICE"])
INSTRUCTIONS_TEMPLATE_S3_URI = os.environ["INSTRUCTIONS_TEMPLATE_S3_URI"]
GROUND_TRUTH_ROLE_ARN = os.environ["GROUND_TRUTH_ROLE_ARN"]
LABEL_CATEGORIES_S3_URI = os.environ["LABEL_CATEGORIES_S3_URI"]
VERIFICATION_ATTRIBUTE_NAME = os.environ["VERIFICATION_ATTRIBUTE_NAME"]
LABELING_ATTRIBUTE_NAME = os.environ["LABELING_ATTRIBUTE_NAME"]


def handler(event: Dict[str, Any], context: object) -> Dict[str, str]:
    record_source_to_receipt_handle_s3_key = event["RecordSourceToReceiptHandleS3Key"]
    record_source_to_receipt_handle = download_json_dict_from_s3(
        s3_key=record_source_to_receipt_handle_s3_key,
        bucket=OUTPUT_BUCKET,
    )
    logger.info("Downloaded record source to receipt handles from S3")

    labeling_job_output_uri = event["LabelingJobOutputUri"]
    labeling_job_output = get_s3_string_object_from_uri(s3_uri=labeling_job_output_uri)
    logger.info("Downloaded labeling job output from S3")

    (
        labeled_records,
        unlabeled_record_source_to_receipt_handle,
        record_source_to_receipt_handle,
    ) = parse_labeling_job_output(
        labeling_job_output=labeling_job_output,
        record_source_to_receipt_handle=record_source_to_receipt_handle,
    )

    execution_id = event["ExecutionId"].rsplit(":", 1)[-1]
    manifest_uri = create_and_upload_manifest(
        labeled_records=labeled_records,
        bucket=OUTPUT_BUCKET,
        prefix=f"runs/{execution_id}",
    )

    output_uri = f"s3://{OUTPUT_BUCKET}/runs/{execution_id}/"
    job_name = f"{VERIFICATION_JOB_NAME}-{execution_id}"
    prehuman_arn = f"arn:aws:lambda:{AWS_REGION}:{AC_ARN_MAP[AWS_REGION]}:function:PRE-Verification{FUNCTION_NAME}"
    acs_arn = f"arn:aws:lambda:{AWS_REGION}:{AC_ARN_MAP[AWS_REGION]}:function:ACS-Verification{FUNCTION_NAME}"
    create_labeling_job(
        human_task_config=HUMAN_TASK_CONFIG,
        prehuman_arn=prehuman_arn,
        acs_arn=acs_arn,
        task_title=TASK_TITLE,
        task_description=TASK_DESCRIPTION,
        task_keywords=TASK_KEYWORDS,
        workteam_arn=WORKTEAM_ARN,
        task_price=TASK_PRICE,
        instructions_template_s3_uri=INSTRUCTIONS_TEMPLATE_S3_URI,
        manifest_uri=manifest_uri,
        output_uri=output_uri,
        job_name=job_name,
        ground_truth_role_arn=GROUND_TRUTH_ROLE_ARN,
        label_attribute_name=VERIFICATION_ATTRIBUTE_NAME,
        label_categories_s3_uri=LABEL_CATEGORIES_S3_URI,
    )
    logger.info("Created verification labeling job")

    unlabeled_record_source_to_receipt_handle_s3_key = upload_json_to_s3(
        json_data=unlabeled_record_source_to_receipt_handle,
        bucket=OUTPUT_BUCKET,
        prefix=f"runs/{execution_id}",
        filename="unlabeled_record_source_to_receipt_handle.json",
    )
    logger.info("Uploaded unlabeled record source to receipt handles to S3")

    record_source_to_receipt_handle_s3_key = upload_json_to_s3(
        json_data=record_source_to_receipt_handle,
        bucket=OUTPUT_BUCKET,
        prefix=f"runs/{execution_id}",
        filename="record_source_to_receipt_handle.json",
    )
    logger.info("Uploaded record source to receipt handles to S3")

    return {
        "LabelingJobName": job_name,
        "UnlabeledRecordSourceToReceiptHandleS3Key": unlabeled_record_source_to_receipt_handle_s3_key,
        "RecordSourceToReceiptHandleS3Key": record_source_to_receipt_handle_s3_key,
    }


def parse_labeling_job_output(
    labeling_job_output: str,
    record_source_to_receipt_handle: Dict[str, str],
) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    logger.info("Parsing labeling job output")

    unlabeled_record_source_to_receipt_handle = {}
    labeled_records = []
    for line in labeling_job_output.splitlines():
        item = json.loads(line)
        if "failure-reason" in item[f"{LABELING_ATTRIBUTE_NAME}-metadata"]:
            record_source = item[SOURCE_KEY]
            receipt_handle = record_source_to_receipt_handle.pop(record_source)
            unlabeled_record_source_to_receipt_handle[record_source] = receipt_handle
        else:
            labeled_records.append(line)

    logger.info(
        f"Parsed labeling job output. {len(labeled_records)} labeled records, "
        f"{len(unlabeled_record_source_to_receipt_handle)} unlabeled records."
    )
    return (
        labeled_records,
        unlabeled_record_source_to_receipt_handle,
        record_source_to_receipt_handle,
    )


def create_and_upload_manifest(
    labeled_records: List[str],
    bucket: str,
    prefix: str,
) -> str:
    logger.info("Creating manifest")

    manifest_name = "verification.manifest"
    tmp_file = f"/tmp/{manifest_name}"
    with open(tmp_file, "w") as f:
        for line in labeled_records:
            f.write(f"{line}\n")
    s3.upload_file(Filename=tmp_file, Bucket=bucket, Key=f"{prefix}/{manifest_name}")
    logger.info("Uploaded manifest to S3")

    return f"s3://{bucket}/{prefix}/{manifest_name}"
