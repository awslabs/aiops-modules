from __future__ import print_function

import logging
from collections import namedtuple
from io import StringIO
from urllib.parse import urlparse

import boto3
import pandas as pd
import sagemaker
from crhelper import CfnResource

logger = logging.getLogger(__name__)

helper = CfnResource(
    json_logging=False,
    log_level="DEBUG",
    boto_level="CRITICAL",
    sleep_on_delete=120,
    ssl_verify=None,
)

LambdaConfig = namedtuple("LambdaConfig", ["feature_group_name", "labels_uri"])

try:
    # initialize clients
    s3 = boto3.resource("s3")
    s3_client = boto3.client("s3")
    sagemaker_session = sagemaker.Session()
    sagemaker_client = boto3.client("sagemaker")
    sagemaker_featurestore_runtime_client = boto3.client(
        "sagemaker-featurestore-runtime"
    )
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info(f"check-missing-labels called with event {event}")
    lambda_config = initialize_lambda_config(event)
    logger.info(f"Finished with lambda config {lambda_config}")

    # lead labels from s3
    labels_csv = read_file_from_s3(lambda_config.labels_uri)
    # replace with correct path to images
    bucket, _ = parse_s3_uri(lambda_config.labels_uri)
    labels_csv = labels_csv.replace("${bucket}", bucket)
    df = pd.read_csv(StringIO(labels_csv))
    # transform to feature store records
    records = transform_df_to_records(df)

    # ingest to feature store
    for record in records:
        print(f"ingesting Record {record}")
        sagemaker_featurestore_runtime_client.put_record(
            FeatureGroupName=lambda_config.feature_group_name, Record=record
        )
    return f"Successfully uploaded {len(records)} to feature group {lambda_config.feature_group_name}"


@helper.delete
def delete(event, context):
    logger.info("Deletion of labels not required")


def initialize_lambda_config(event: dict):
    feature_group_name = (
        event["ResourceProperties"]["feature_group_name"]
        if "feature_group_name" in event["ResourceProperties"]
        else "tag-quality-inspection"
    )
    labels_uri = ""

    if "labels_uri" in event["ResourceProperties"]:
        labels_uri = event["ResourceProperties"]["labels_uri"]
    else:
        raise Exception("No labels_uri specified in lambda event")
    return LambdaConfig(feature_group_name, labels_uri)


def transform_df_to_records(df: pd.DataFrame):
    return [
        [
            {"ValueAsString": str(row[column]), "FeatureName": column}
            for column in df.columns
        ]
        for _, row in df.iterrows()
    ]


def read_file_from_s3(file: str):
    bucket, key = parse_s3_uri(file)
    logger.info(f"Reading file {file} from bucket {bucket} with key {key}")
    obj = s3.Object(bucket, key)
    return obj.get()["Body"].read().decode("utf-8")


def parse_s3_uri(s3_url):
    bucket = urlparse(s3_url, allow_fragments=False).netloc
    key = urlparse(s3_url, allow_fragments=False).path[1:]
    return bucket, key


def handler(event, context):
    helper(event, context)
