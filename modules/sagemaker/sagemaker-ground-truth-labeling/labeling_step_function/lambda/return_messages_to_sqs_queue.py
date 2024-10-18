import logging
import os
from typing import Any, Dict, List

import boto3
from _utils import IMAGE, TEXT, download_json_dict_from_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")

QUEUE_URL = os.environ["SQS_QUEUE_URL"]
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
TASK_MEDIA_TYPE = os.environ["TASK_MEDIA_TYPE"]

BATCH_SIZE_LIMIT = 10


def handler(event: Dict[str, Any], context: object) -> None:
    record_source_to_receipt_handle_s3_key = event["RecordSourceToReceiptHandleS3Key"]
    record_source_to_receipt_handle = download_json_dict_from_s3(
        s3_key=record_source_to_receipt_handle_s3_key, bucket=OUTPUT_BUCKET
    )
    logger.info(
        f"Downloaded record source to receipt handles from S3, "
        f"{len(record_source_to_receipt_handle)} messages to return to SQS queue"
    )

    batches = split_dict_into_batches(data=record_source_to_receipt_handle, batch_size=BATCH_SIZE_LIMIT)

    logger.info("Starting to return messages to SQS queue")

    for batch in batches:
        change_visibility_batch(queue_url=QUEUE_URL, batch=batch, task_media_type=TASK_MEDIA_TYPE)

    logger.info("Finished returning messages to SQS queue")


def split_dict_into_batches(data: Dict[str, str], batch_size: int) -> List[Dict[str, str]]:
    items = list(data.items())
    return [dict(items[i : i + batch_size]) for i in range(0, len(items), batch_size)]


def change_visibility_batch(queue_url: str, batch: Dict[str, str], task_media_type: str) -> None:
    entries = []
    for i, (record_source, receipt_handle) in enumerate(batch.items()):
        if task_media_type == IMAGE:
            filename = record_source.split("/")[-1]
            # id request can only contain alphanumeric, hyphen and underscores
            id = filename.replace(".", "_")
        elif task_media_type == TEXT:
            id = str(i)
        else:
            raise ValueError(f"Unsupported task media type: {task_media_type}")

        entries.append(
            {
                "Id": id,
                "ReceiptHandle": receipt_handle,
                "VisibilityTimeout": 0,
            }
        )

    response = sqs.change_message_visibility_batch(QueueUrl=queue_url, Entries=entries)

    if "Failed" in response:
        for failed in response["Failed"]:
            logger.error(f"Failed to return message: {failed['Id']}")
