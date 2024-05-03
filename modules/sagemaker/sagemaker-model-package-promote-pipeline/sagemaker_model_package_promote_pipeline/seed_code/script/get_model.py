"""A module to get Sagemaker Models metadata and artifacts."""

import argparse
import json
import logging
import os
import pathlib
import shutil
import tempfile
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

import boto3
from boto3.s3.transfer import TransferConfig
from flatten_json import flatten, unflatten_list


def get_latest_model_from_model_registry(
    boto3_session: Any,
    model_package_group_name: str,
    status_approval: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Get the latest registered model from SageMaker model registry

    Parameters
    ----------
    sm_client : Any
        The SageMaker boto3 client
    model_package_group_name : str
        The Model Package Group name to get model versions
    status_approval : Optional[str]
        To filter based on the model status (e.g. Approved, Rejected)

    Returns
    -------
    Optional[dict]
        The latest registered model.
    """

    sm_client = boto3_session.client("sagemaker")

    paginator = sm_client.get_paginator("list_model_packages")

    operator_args = {
        "ModelPackageGroupName": model_package_group_name,
        "SortBy": "CreationTime",
    }

    if status_approval:
        operator_args["ModelApprovalStatus"] = status_approval

    for p in paginator.paginate(**operator_args):
        models = p["ModelPackageSummaryList"]

        approved_model_package = next(iter(models), None)

        if approved_model_package:
            model: Dict[str, Any] = sm_client.describe_model_package(
                ModelPackageName=approved_model_package["ModelPackageArn"]
            )
            return model
    return None


def download_s3_object(
    boto3_session: Any,
    bucket: str,
    object_key: str,
    path: str = "",
) -> str:
    """Download a object from S3

    Parameters
    ----------
    boto3_session : Any
        The boto3 Session
    bucket : str
        The bucket name
    object_key : str
        The object key
    path : str, optional
        The local path to store the object, by default ""

    Returns
    -------
    str
        The location to the object.
    """

    s3 = boto3_session.resource("s3")
    filepath = os.path.join(path, object_key)

    # Create directory
    pathlib.Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    # Configure multipart parameters
    config = TransferConfig(multipart_threshold=1024**3, max_concurrency=100)  # 1 GB

    # Download file
    s3.Bucket(bucket).download_file(object_key, filepath, Config=config)

    return filepath


def parse_args() -> argparse.Namespace:
    """Define script arguments

    Returns
    -------
    ArgumentParser
        Script keyword arguments.
    """
    parser = argparse.ArgumentParser()

    # Required
    parser.add_argument(
        "-p",
        "--model-artifacts-path",
        type=str,
        required=True,
        help="The path to store model artifacts zip downloaded from S3 (e.g. '/tmp/model_artifacts').",
    )

    parser.add_argument(
        "-o",
        "--output-json-config",
        type=str,
        required=True,
        help="The json file to save metadata (e.g. /tmp/model_config.json)",
    )

    parser.add_argument(
        "-g",
        "--model-package-group",
        type=str,
        required=True,
        help="The model package group name",
    )

    ## Optional
    parser.add_argument(
        "--profile-name",
        type=str,
        required=False,
        default=None,
        help="Optional profile name for boto3 session.",
    )

    args = parser.parse_args()

    return args


def main():  # type: ignore
    args = parse_args()

    boto3_session = boto3.Session(profile_name=args.profile_name)
    logging.getLogger().setLevel(logging.INFO)

    # Get model metadata
    logging.info(f"Getting model metadata from {args.model_package_group}")

    model_metadata = get_latest_model_from_model_registry(
        boto3_session=boto3_session,
        model_package_group_name=args.model_package_group,
        status_approval="Approved",
    )

    logging.debug(f"Received response from sagemaker: {model_metadata}")

    if not model_metadata:
        raise RuntimeError(f"Model metadata not found for `{args.model_package_group}`")

    # Get model artifacts
    logging.info("Downloading model artifacts")
    flatten_metadata = flatten(model_metadata, separator="___")

    tmp_dir = os.path.join(tempfile.gettempdir(), "model_artifacts", args.model_package_group)
    downloaded_files = []
    for k, v in flatten_metadata.items():
        if not (isinstance(v, str) and v.startswith("s3://")):
            continue
        if v in downloaded_files:
            continue

        # Download model artifacts from S3
        logging.info(f"Downloading: {v}")

        url = urlparse(v)

        bucket, object_key = url.netloc, unquote(url.path[1:])

        download_s3_object(
            boto3_session=boto3_session,
            bucket=bucket,
            object_key=object_key,
            path=tmp_dir,
        )
        downloaded_files.append(v)

        # Replace bucket name with template variable
        flatten_metadata[k] = os.path.join("s3://", "${bucket_name}", object_key)

    # Zip model artifacts. We need to zip because aws CDK has a limit of 2 GB (node).
    logging.info("Compressing model artifacts. This may take a while!")
    shutil.make_archive(args.model_artifacts_path, "zip", tmp_dir)

    # Dump model configs
    logging.info("Dumping model metadata into JSON file")
    model_metadata = unflatten_list(flatten_metadata, separator="___")

    json_config = {
        "Artifacts": f"{args.model_artifacts_path}.zip",
        "Model": model_metadata,
    }

    with open(args.output_json_config, "w+") as f:
        json.dump(json_config, f, default=str)


if __name__ == "__main__":
    main()  # type: ignore
