import logging
import os
from typing import Any, Dict

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def handler(event: Dict[str, Any], context: object) -> None:
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        if not key.endswith(".txt"):
            logger.info(f"Skipping non-txt file {key}")
            continue

        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response["Body"].read().decode("utf-8")

            sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=file_content)
            logger.info("Sent file contents to SQS queue")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
