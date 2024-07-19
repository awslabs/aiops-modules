from collections import namedtuple
from botocore.exceptions import ClientError
import sagemaker
from urllib.parse import urlparse
import boto3
import logging
from sagemaker.feature_store.feature_group import FeatureGroup
import os

APPROVED_LABELS_QUERY = """
SELECT *
FROM
    (SELECT *, row_number()
        OVER (PARTITION BY source_ref
    ORDER BY event_time desc, Api_Invocation_Time DESC, write_time DESC) AS row_number
    FROM "{table}")
WHERE row_number = 1 AND status = 'APPROVED' AND NOT is_deleted 
"""

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# initialize clients
s3 = boto3.resource("s3")
s3_client = boto3.client("s3")
sagemaker_session = sagemaker.Session()
sagemaker_client = boto3.client("sagemaker")

# initialize config from env variables
LambdaConfig = namedtuple(
    "LambdaConfig",
    [
        "feature_group_name",
        "feature_name_s3uri",
        "input_images_s3uri",
        "query_results_s3uri",
    ],
)


def initialize_lambda_config():
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
    input_images_s3uri = (
        os.environ["INPUT_IMAGES_S3URI"]
        if "INPUT_IMAGES_S3URI" in os.environ
        else "s3://aiopsbucket/pipeline/assets/images/"
    )
    query_results_s3uri = (
        os.environ["QUERY_RESULTS_S3URI"]
        if "QUERY_RESULTS_S3URI" in os.environ
        else "s3://aiopsbucket/tmp/feature_store_query_results"
    )
    return LambdaConfig(
        feature_group_name, feature_name_s3uri, input_images_s3uri, query_results_s3uri
    )


lambda_config = initialize_lambda_config()


def handler(event, context):
    logger.info(
        f"check-missing-labels called with event {event} and lambda config {lambda_config}"
    )

    bucket, key = split_s3_url(lambda_config.input_images_s3uri)
    images = get_list_of_files(bucket=bucket, prefix=key, file_types=[".jpg", ".png"])

    existing_labels = get_existing_labels(
        lambda_config.feature_group_name, lambda_config.query_results_s3uri
    )
    missing_labels = get_images_without_labels(
        images=images, existing_labels=existing_labels
    )

    logger.info(
        f"Finished check-missing-labels lambda with {len(missing_labels)} missing labels"
    )
    output = {
        "missing_labels_count": len(missing_labels),
        "missing_labels": missing_labels,
    }
    return output


def split_s3_url(s3_url):
    bucket = urlparse(s3_url, allow_fragments=False).netloc
    key = urlparse(s3_url, allow_fragments=False).path[1:]
    return bucket, key


def get_list_of_files(bucket=None, prefix=None, file_types=None):
    logger.info(f"Getting list of files for bucket {bucket} and prefix {prefix}")
    filtered_files = []

    bucket = s3.Bucket(bucket)
    files = bucket.objects.filter(Prefix=prefix)

    for file in files:
        if is_allowed_file_type(file.key, file_types):
            filtered_files.append(f"s3://{file.bucket_name}/{file.key}")
    logger.info(f"Found {len(filtered_files)} images")
    return filtered_files


def is_allowed_file_type(file, file_types=None):
    allowed = False
    for file_type in file_types:
        if file.endswith(file_type):
            allowed = True
    return allowed


def feature_group_exists(feature_group_name):
    try:
        sagemaker_client.describe_feature_group(FeatureGroupName=feature_group_name)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFound":
            logger.info(f"No feature group found with name {feature_group_name}")
            return False
    return True


def get_existing_labels(feature_group_name, query_results_s3uri):
    if not feature_group_exists(feature_group_name):
        return []
    feature_group = FeatureGroup(
        name=feature_group_name, sagemaker_session=sagemaker_session
    )
    query = feature_group.athena_query()
    query_string = APPROVED_LABELS_QUERY.format(table=query.table_name)
    logger.debug(f"Running query {query_string} against FeatureGroup {feature_group}")
    query.run(query_string=query_string, output_location=query_results_s3uri)
    query.wait()
    df = query.as_dataframe()
    logger.info(f"Found {len(df[lambda_config.feature_name_s3uri].tolist())} labels")

    return df[lambda_config.feature_name_s3uri].tolist()


def get_images_without_labels(images=None, existing_labels=None):
    missing_labels = []
    for image in images:
        if image not in existing_labels:
            missing_labels.append(image)
    logger.info(
        f"images: {len(images)} , existing_labels: {len(existing_labels)}, missing_labels: {len(missing_labels)}"
    )
    return missing_labels
