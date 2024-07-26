import json
import boto3
import os

bedrock = boto3.client(service_name="bedrock")
bedrock_runtime = boto3.client(service_name="bedrock-runtime")

role_arn = os.environ.get("role_arn")
kms_key_id = os.environ.get("kms_key_id")
base_model_id = os.environ.get("base_model_id")
vpc_subnets = json.loads(os.environ.get("vpc_subnets"))
vpc_sec_group = os.environ.get("vpc_sec_group")


def lambda_handler(event, context):
    file_key = event["detail"]["object"]["key"]
    job_name = (
        file_key.replace(".", "-")
        .replace(",", "-")
        .replace("_", "-")
        .replace("/", "-")[:62]
    )
    output_location = event["detail"]["bucket"]["name"]
    output_loc = "s3://" + output_location + "/" + job_name.split("/")[0] + "-output"
    model_name = (
        "model-"
        + file_key.replace(".", "-")
        .replace(",", "-")
        .replace("_", "-")
        .replace("/", "-")[:62]
    )
    training_input = "s3://" + event["detail"]["bucket"]["name"] + "/" + file_key

    bedrock.create_model_customization_job(
        customizationType="FINE_TUNING",
        customModelKmsKeyId=kms_key_id,
        jobName=job_name,
        customModelName=model_name,
        roleArn=role_arn,
        baseModelIdentifier=base_model_id,
        hyperParameters={
            "epochCount": "1",
            "batchSize": "1",
            "learningRate": "0.00005",
        },
        trainingDataConfig={"s3Uri": training_input},
        outputDataConfig={"s3Uri": output_loc},
        vpcConfig={
            "securityGroupIds": [vpc_sec_group],
            "subnets": vpc_subnets,
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Model finetuning started successfully, job name: {job_name}"
        ),
    }
