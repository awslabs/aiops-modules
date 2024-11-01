import concurrent.futures
import datetime
import json
import logging
import operator
import os
from functools import reduce
from typing import Any, Dict, List, Union

import boto3
from _utils import (
    IMAGE,
    TEXT,
    download_json_dict_from_s3,
    get_s3_string_object_from_uri,
    upload_json_to_s3,
)
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
TASK_MEDIA_TYPE = os.environ["TASK_MEDIA_TYPE"]
SOURCE_KEY = os.environ["SOURCE_KEY"]
FEATURE_GROUP_NAME = os.environ["FEATURE_GROUP_NAME"]
FEATURE_GROUP_DEFINITIONS = json.loads(os.environ["FEATURE_GROUP_DEFINITIONS"])
QUEUE_URL = os.environ["SQS_QUEUE_URL"]
LABELING_ATTRIBUTE_NAME = os.environ["LABELING_ATTRIBUTE_NAME"]
VERIFICATION_ATTRIBUTE_NAME = os.getenv("VERIFICATION_ATTRIBUTE_NAME", None)
VERIFICATION_STEP = VERIFICATION_ATTRIBUTE_NAME is not None

VERIFICATION_APPROVED_CLASS = 0
APPROVED_STATUS = "APPROVED"
REJECTED_STATUS = "REJECTED"

MAX_SQS_BATCH_SIZE = 10
THREAD_POOL_SIZE = 5
CONCURRENT_PROCESSING_BATCH_SIZE = 1000

boto3_config = Config(max_pool_connections=THREAD_POOL_SIZE)
sqs = boto3.client("sqs", config=boto3_config)
sagemaker_featurestore = boto3.client("sagemaker-featurestore-runtime", config=boto3_config)


def handler(event: Dict[str, Any], context: object) -> Dict[str, str]:
    labeling_job_output_uri = event["LabelingJobOutputUri"]
    labeling_job_output = get_s3_string_object_from_uri(s3_uri=labeling_job_output_uri)
    logger.info("Downloaded labeling job output from S3")

    record_source_to_receipt_handle_s3_key = event["RecordSourceToReceiptHandleS3Key"]
    record_source_to_receipt_handle = download_json_dict_from_s3(
        s3_key=record_source_to_receipt_handle_s3_key, bucket=OUTPUT_BUCKET
    )
    logger.info("Downloaded record source to receipt handles from S3")

    rejected_labels_record_source_to_receipt_handle = process_labeling_job_output(
        feature_group_name=FEATURE_GROUP_NAME,
        queue_url=QUEUE_URL,
        labeling_job_output=labeling_job_output,
        record_source_to_receipt_handle=record_source_to_receipt_handle,
        feature_group_definitions=FEATURE_GROUP_DEFINITIONS,
        task_media_type=TASK_MEDIA_TYPE,
    )

    execution_id = event["ExecutionId"].rsplit(":", 1)[-1]
    rejected_labels_record_source_to_receipt_handle_s3_key = upload_json_to_s3(
        json_data=rejected_labels_record_source_to_receipt_handle,
        bucket=OUTPUT_BUCKET,
        prefix=f"runs/{execution_id}",
        filename="rejected_labels_record_source_to_receipt_handle.json",
    )
    logger.info("Uploaded rejected labels record source to receipt handles to S3")

    return {"RejectedLabelsRecordSourceToReceiptHandleS3Key": rejected_labels_record_source_to_receipt_handle_s3_key}


def process_labeling_job_output(
    feature_group_name: str,
    queue_url: str,
    labeling_job_output: str,
    record_source_to_receipt_handle: Dict[str, str],
    feature_group_definitions: Dict[str, List[Union[str, int]]],
    task_media_type: str,
) -> Dict[str, str]:
    logger.info("Processing labeling job output")

    delete_entries = []
    feature_store_records = {}
    for i, line in enumerate(labeling_job_output.splitlines()):
        labeling_result = json.loads(line)
        record = transform_labeling_result_to_record(
            labeling_result=labeling_result,
            feature_group_definitions=feature_group_definitions,
        )

        if record:
            record_source = labeling_result[SOURCE_KEY]
            if record_source in record_source_to_receipt_handle:
                receipt_handle = record_source_to_receipt_handle.pop(record_source)
                if task_media_type == IMAGE:
                    filename = record_source.split("/")[-1]
                    # id request can only contain alphanumeric, hyphen and underscores
                    id = filename.replace(".", "_")
                elif task_media_type == TEXT:
                    id = str(i)
                else:
                    raise ValueError(f"Unsupported task media type: {task_media_type}")
                delete_entries.append({"Id": id, "ReceiptHandle": receipt_handle})
                feature_store_records[id] = record

                # multi thread deletes in batches to prevent all records being held in memory at the same time
                if len(delete_entries) == CONCURRENT_PROCESSING_BATCH_SIZE:
                    multi_threaded_batch_delete_message_from_sqs_and_save_to_feature_store(
                        queue_url=queue_url,
                        feature_group_name=feature_group_name,
                        delete_entries=delete_entries,
                        feature_store_records=feature_store_records,
                    )
                    delete_entries = []
                    feature_store_records = {}

    # Delete any remaining messages after for loop
    if delete_entries:
        multi_threaded_batch_delete_message_from_sqs_and_save_to_feature_store(
            queue_url=queue_url,
            feature_group_name=feature_group_name,
            delete_entries=delete_entries,
            feature_store_records=feature_store_records,
        )

    logger.info(f"Processed labeling job output, {len(record_source_to_receipt_handle)} remaining messages")

    return record_source_to_receipt_handle


def transform_labeling_result_to_record(
    labeling_result: Dict[str, Any],
    feature_group_definitions: Dict[str, List[Union[str, int]]],
) -> List[Dict[str, str]]:
    labeling_result_location = VERIFICATION_ATTRIBUTE_NAME if VERIFICATION_STEP else LABELING_ATTRIBUTE_NAME
    if "failure-reason" in labeling_result[f"{labeling_result_location}-metadata"]:
        return []

    creation_date = datetime.datetime.strptime(
        labeling_result[f"{LABELING_ATTRIBUTE_NAME}-metadata"]["creation-date"],
        "%Y-%m-%dT%H:%M:%S.%f",
    ).timestamp()

    record = [
        create_record_feature(SOURCE_KEY.replace("-", "_"), str(labeling_result[SOURCE_KEY])),
        create_record_feature("event_time", str(int(round(creation_date)))),
        create_record_feature(
            "labeling_job",
            str(labeling_result[f"{LABELING_ATTRIBUTE_NAME}-metadata"]["job-name"]),
        ),
    ]

    if VERIFICATION_STEP:
        status = (
            APPROVED_STATUS
            if labeling_result[f"{VERIFICATION_ATTRIBUTE_NAME}"] == VERIFICATION_APPROVED_CLASS
            else REJECTED_STATUS
        )

        if status == REJECTED_STATUS:
            return []
        else:
            record.append(create_record_feature("status", status))

    for feature_name, output_key in feature_group_definitions.items():
        # access nested value using key list
        feature_value = reduce(operator.getitem, output_key, labeling_result)  # type: ignore
        record.append(create_record_feature(feature_name, str(feature_value)))
    return record


def create_record_feature(feature_name: str, feature_value: str) -> Dict[str, str]:
    return {"FeatureName": feature_name, "ValueAsString": feature_value}


def multi_threaded_batch_delete_message_from_sqs_and_save_to_feature_store(
    queue_url: str,
    feature_group_name: str,
    delete_entries: List[Dict[str, str]],
    feature_store_records: Dict[str, List[Dict[str, str]]],
) -> None:
    logger.info(f"Batch deleting {len(delete_entries)} messages from SQS and saving to feature store")

    delete_entries_split = [
        delete_entries[i : i + MAX_SQS_BATCH_SIZE] for i in range(0, len(delete_entries), MAX_SQS_BATCH_SIZE)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
        futures = []
        for delete_entries_for_batch in delete_entries_split:
            feature_store_records_for_batch = {
                entry["Id"]: feature_store_records[entry["Id"]] for entry in delete_entries_for_batch
            }
            future = executor.submit(
                batch_delete_message_from_sqs_and_save_to_feature_store,
                queue_url=queue_url,
                feature_group_name=feature_group_name,
                delete_entries=delete_entries_for_batch,
                feature_store_records=feature_store_records_for_batch,
                executor=executor,
            )
            futures.append(future)

        concurrent.futures.wait(futures)


def batch_delete_message_from_sqs_and_save_to_feature_store(
    queue_url: str,
    feature_group_name: str,
    delete_entries: List[Dict[str, str]],
    feature_store_records: Dict[str, List[Dict[str, str]]],
    executor: concurrent.futures.ThreadPoolExecutor,
) -> None:
    try:
        response = sqs.delete_message_batch(QueueUrl=queue_url, Entries=delete_entries)

        if "Successful" in response:
            for success in response["Successful"]:
                source_key = success["Id"]
                executor.submit(
                    put_record_to_feature_store,
                    feature_group_name=feature_group_name,
                    record=feature_store_records[source_key],
                )
        if "Failed" in response:
            for failed in response["Failed"]:
                logger.error(f"Failed to delete message {failed['Id']} from SQS")

    except Exception as e:
        logger.error(f"Error occurred while deleting messages from SQS: {e}")


def put_record_to_feature_store(feature_group_name: str, record: List[Dict[str, str]]) -> None:
    try:
        sagemaker_featurestore.put_record(FeatureGroupName=feature_group_name, Record=record)
    except Exception as e:
        logger.error(f"Error occurred while putting record to feature store: {e}")
