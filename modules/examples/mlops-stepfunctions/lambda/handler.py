import json
import logging
import os
import time

import boto3  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]

# Configure the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):  # type: ignore[no-untyped-def]
    logger.info(f"event: {event}")
    s3 = boto3.client("s3")

    bucket_name = event["config"]["bucket"]
    prefix = event["config"]["prefix"]
    response = s3.get_object(Bucket=bucket_name, Key=prefix)

    yaml_data = response["Body"].read().decode("utf-8")
    configuration = yaml.safe_load(yaml_data)
    execution_name = f'{configuration["job_prefix"]}-{configuration["model_id"]}-{int(time.time())}'
    stateMachineArn = os.environ["STATE_MACHINE_ARN"]
    sfn = boto3.client("stepfunctions")
    input_data = json.dumps(configuration)
    input_data = input_data.replace("SFN_EXECUTION_ID", execution_name)
    response = sfn.start_execution(stateMachineArn=stateMachineArn, name=execution_name, input=input_data)
    logger.info(f"sfn response: {response}")

    return {"statusCode": 200, "body": json.dumps("Success")}
