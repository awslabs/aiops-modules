import json
import logging
import os
from typing import Any, Dict, List

import boto3
from _utils import IMAGE, TEXT, upload_json_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")

SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
TASK_TYPE = os.environ["TASK_TYPE"]
TASK_MEDIA_TYPE = os.environ["TASK_MEDIA_TYPE"]

MAX_BATCH_SIZE = 10
MAX_LONG_POLLING_DURATION = 20

MAX_NUMBER_OF_LABELING_ITEMS = 100000
MAX_NUMBER_OF_LABELING_ITEMS_SEMANTIC_SEGMENTATION = 20000


def handler(event: Dict[str, Any], context: object) -> Dict[str, str]:
    item_limit = (
        MAX_NUMBER_OF_LABELING_ITEMS_SEMANTIC_SEGMENTATION
        if TASK_TYPE == "semantic_segmentation"
        else MAX_NUMBER_OF_LABELING_ITEMS
    )
    logger.info(f"Item limit set: {item_limit}")

    record_source_to_receipt_handle = poll_sqs_queue(
        sqs_queue_url=SQS_QUEUE_URL,
        item_limit=item_limit,
        messages_per_batch=MAX_BATCH_SIZE,
        wait_time_seconds=MAX_LONG_POLLING_DURATION,
        task_media_type=TASK_MEDIA_TYPE,
    )

    execution_id = event["ExecutionId"].rsplit(":", 1)[-1]
    record_source_to_receipt_handle_s3_key = upload_json_to_s3(
        json_data=record_source_to_receipt_handle,
        bucket=OUTPUT_BUCKET,
        prefix=f"runs/{execution_id}",
        filename="record_source_to_receipt_handle.json",
    )
    logger.info("Uploaded record source to receipt handles to S3")

    return {
        "MessagesCount": str(len(record_source_to_receipt_handle)),
        "RecordSourceToReceiptHandleS3Key": record_source_to_receipt_handle_s3_key,
    }


def poll_sqs_queue(
    sqs_queue_url: str,
    item_limit: int,
    messages_per_batch: int,
    wait_time_seconds: int,
    task_media_type: str,
) -> Dict[str, str]:
    receipt_handles_of_duplicates: List[str] = []
    record_source_to_receipt_handle: Dict[str, str] = {}

    while True:
        if len(record_source_to_receipt_handle) >= item_limit:
            break
        if len(record_source_to_receipt_handle) + messages_per_batch > item_limit:
            messages_per_batch = item_limit - len(record_source_to_receipt_handle)
        response = sqs.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=messages_per_batch,
            WaitTimeSeconds=wait_time_seconds,
        )

        if not response.get("Messages"):
            break

        for message in response["Messages"]:
            try:
                if task_media_type == IMAGE:
                    body = json.loads(message["Body"])
                    s3_event = body["Records"][0]["s3"]
                    bucket_name = s3_event["bucket"]["name"]
                    object_key = s3_event["object"]["key"]
                    record_source = f"s3://{bucket_name}/{object_key}"
                elif task_media_type == TEXT:
                    record_source = message["Body"]
                else:
                    raise ValueError(f"Unsupported task media type: {task_media_type}")

                if record_source in record_source_to_receipt_handle:
                    receipt_handles_of_duplicates.append(message["ReceiptHandle"])
                else:
                    record_source_to_receipt_handle[record_source] = message["ReceiptHandle"]

            except (KeyError, json.JSONDecodeError, IndexError) as e:
                logger.error(f"Error processing message: {str(e)}")

    if receipt_handles_of_duplicates:
        delete_duplicate_record_source_messages(
            sqs_queue_url=sqs_queue_url,
            messages_per_batch=messages_per_batch,
            receipt_handles_of_duplicates=receipt_handles_of_duplicates,
        )

    logger.info(f"Total messages received: {len(record_source_to_receipt_handle)}")

    return record_source_to_receipt_handle


def delete_duplicate_record_source_messages(
    sqs_queue_url: str,
    messages_per_batch: int,
    receipt_handles_of_duplicates: List[str],
) -> None:
    logger.info(f"Deleting {len(receipt_handles_of_duplicates)} duplicate messages from the queue.")

    receipt_handles_batches = [
        receipt_handles_of_duplicates[i : i + messages_per_batch]
        for i in range(0, len(receipt_handles_of_duplicates), messages_per_batch)
    ]
    for batch in receipt_handles_batches:
        try:
            sqs.delete_message_batch(
                QueueUrl=sqs_queue_url,
                Entries=[{"Id": str(i), "ReceiptHandle": receipt_handle} for i, receipt_handle in enumerate(batch)],
            )
        except Exception as e:
            logger.error(f"Error deleting messages: {str(e)}")
