import datetime
import json
import logging
import os
from collections import namedtuple
from urllib.parse import urlparse
import time
import boto3
import pandas as pd
import sagemaker
from botocore.exceptions import ClientError
from sagemaker.feature_store.feature_group import FeatureGroup

APPROVED_LABELS_QUERY = """
SELECT *
FROM
    (SELECT *, row_number()
        OVER (PARTITION BY source_ref
    ORDER BY event_time desc, Api_Invocation_Time DESC, write_time DESC) AS row_number
    FROM "{table}")
WHERE row_number = 1 AND status = 'APPROVED' AND NOT is_deleted 
"""
FEATURE_S3URI = "source_ref"
EVENT_TIME_FEATURE_NAME = "event_time"
VERIFICATION_APPROVED_CLASS = 0

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# initialize clients
s3 = boto3.resource("s3")
s3_client = boto3.client("s3")
sagemaker_session = sagemaker.Session()
sagemaker_client = boto3.client("sagemaker")
sagemaker_featurestore_runtime_client = boto3.client("sagemaker-featurestore-runtime")

# initialize config from env variables
LambdaConfig = namedtuple(
    "LambdaConfig",
    [
        "role",
        "verification_job_output",
        "feature_group_name",
        "feature_name_s3uri",
        "feature_store_s3uri",
        "query_results_s3uri",
    ],
)


def initialize_lambda_config(event):
    role = os.environ["ROLE"]
    feature_group_name = (
        os.environ["FEATURE_GROUP_NAME"]
        if "FEATURE_GROUP_NAME" in os.environ
        else "tag-quality-inspection"
    )
    feature_name_s3uri = (
        os.environ["FEATURE_NAME_S3URI"]
        if "FEATURE_NAME_S3URI" in os.environ
        else "source_ref"
    )
    feature_store_s3uri = os.environ["FEATURE_STORE_S3URI"]
    verification_job_output = event["verification_job_output"]
    query_results_s3uri = os.environ["QUERY_RESULTS_S3URI"]
    return LambdaConfig(
        role,
        verification_job_output,
        feature_group_name,
        feature_name_s3uri,
        feature_store_s3uri,
        query_results_s3uri,
    )


def handler(event, context):
    logger.info(f"check-missing-labels called with event {event} ")
    config = initialize_lambda_config(event)
    logging.info(f"Loaded config: {config}")
    df = load_manifest_to_dataframe(config.verification_job_output)

    feature_group = FeatureGroup(
        name=config.feature_group_name, sagemaker_session=sagemaker_session
    )

    if not feature_group_exists(config.feature_group_name):
        feature_group.load_feature_definitions(data_frame=df)
        feature_group.create(
            s3_uri=config.feature_store_s3uri,
            record_identifier_name="source_ref",
            event_time_feature_name=EVENT_TIME_FEATURE_NAME,
            role_arn=config.role,
            enable_online_store=False,
            description="Stores bounding box dataset for quality inspection",
        )
        wait_for_feature_group_creation(feature_group)

    print(f"Ingesting {len(df)} labels into data lake")
    records = transform_df_to_records(df)

    for record in records:
        print(f"ingesting Record {record}")
        sagemaker_featurestore_runtime_client.put_record(
            FeatureGroupName=config.feature_group_name, Record=record
        )
    logging.info("Updated feature store with new labels")


def transform_df_to_records(df: pd.DataFrame):
    return [
        [
            {"ValueAsString": str(row[column]), "FeatureName": column}
            for column in df.columns
        ]
        for _, row in df.iterrows()
    ]


def load_manifest_to_dataframe(s3_uri):
    parsed_url = urlparse(s3_uri, allow_fragments=False)
    s3_object = s3.Object(parsed_url.netloc, parsed_url.path[1:])
    file_content = s3_object.get()["Body"].read().decode("utf-8")

    source_ref = []
    image_height = []
    image_width = []
    image_depth = []
    annotations = []
    creation_date = []
    labeling_job = []
    status = []

    for line in file_content.splitlines():
        item = json.loads(line)

        source_ref.append(item["source-ref"])
        image_width.append(item["category"]["image_size"][0]["width"])
        image_height.append(item["category"]["image_size"][0]["height"])
        image_depth.append(item["category"]["image_size"][0]["depth"])
        annotations.append(item["category"]["annotations"])
        time = datetime.datetime.strptime(
            item["category-metadata"]["creation-date"], "%Y-%m-%dT%H:%M:%S.%f"
        ).timestamp()
        # strftime("%Y-%m-%dT%H:%M:%S%f"))
        creation_date.append(int(round(time)))
        labeling_job.append(item["category-metadata"]["job-name"])

        item_status = (
            "APPROVED"
            if item["verified"] == VERIFICATION_APPROVED_CLASS
            else "REJECTED"
        )
        status.append(item_status)

    data_frame = pd.DataFrame(
        {
            "source_ref": source_ref,
            "image_width": image_width,
            "image_height": image_height,
            "image_depth": image_depth,
            "annotations": annotations,
            EVENT_TIME_FEATURE_NAME: creation_date,
            "labeling_job": labeling_job,
            "status": status,
        }
    )

    # cast all object dtypes to string for auto type recognition of feature store
    for label in data_frame.columns:
        if data_frame.dtypes[label] == object:
            print(data_frame[label])
            data_frame[label] = data_frame[label].astype("str").astype("string")
    # make sure time value is recognized with correct data type
    data_frame[EVENT_TIME_FEATURE_NAME] = data_frame[EVENT_TIME_FEATURE_NAME].astype(
        "float64"
    )
    logging.info(f"labels by status: {data_frame['status'].value_counts()}")
    return data_frame


def feature_group_exists(feature_group_name):
    try:
        sagemaker_client.describe_feature_group(FeatureGroupName=feature_group_name)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFound":
            logging.info(f"No feature group found with name {feature_group_name}")
            return False
    return True


def wait_for_feature_group_creation(feature_group):
    """
    Print when the feature group has been successfully created
    Parameters:
        feature_group: FeatureGroup
    Returns:
        None
    """
    status = feature_group.describe().get("FeatureGroupStatus")
    while status == "Creating":
        print("Waiting for Feature Group to be Created")
        time.sleep(5)
        status = feature_group.describe().get("FeatureGroupStatus")
    print(f"FeatureGroup {feature_group.name} successfully created.")
