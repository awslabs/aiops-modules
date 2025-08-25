from typing import Any, Optional

import aws_cdk
import cdk_nag
from aws_cdk import Aws, Tags
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from constructs import Construct

from settings import RepositoryType
from templates.batch_inference.pipeline_constructs.build_pipeline_construct import BuildPipelineConstruct


class BatchInferenceProject(Construct):
    DESCRIPTION: str = "Creates a SageMaker pipeline for executing batch transforms."
    TEMPLATE_NAME: str = "Invoke Batch Transforms on SageMaker Pipelines"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        build_app_asset: s3_assets.Asset,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        sagemaker_domain_id: str,
        sagemaker_domain_arn: str,
        model_package_group_name: str,
        model_bucket_name: str,
        base_job_prefix: str,
        repository_type: RepositoryType,
        access_token_secret_name: Optional[str],
        aws_codeconnection_arn: Optional[str],
        repository_owner: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id)

        Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)
        if sagemaker_domain_id:
            Tags.of(self).add("sagemaker:domain-id", sagemaker_domain_id)
        if sagemaker_domain_arn:
            Tags.of(self).add("sagemaker:domain-arn", sagemaker_domain_arn)

        # Get Model bucket
        model_bucket = s3.Bucket.from_bucket_name(self, "Model Bucket", model_bucket_name)

        # create kms key to be used by the assets bucket
        kms_key_artifact = kms.Key(
            self,
            "Artifacts Bucket KMS Key",
            description="key used for encryption of data in Amazon S3",
            enable_key_rotation=True,
        )

        pipeline_artifact_bucket = s3.Bucket(
            self,
            "Pipeline Artifacts Bucket",
            bucket_name=f"mlops-{sagemaker_project_name}-{Aws.ACCOUNT_ID}",
            encryption_key=kms_key_artifact,
            versioned=True,
            enforce_ssl=True,  # Blocks insecure requests to the bucket
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )

        BuildPipelineConstruct(
            self,
            "Build",
            project_name=sagemaker_project_name,
            project_id=sagemaker_project_id,
            domain_id=sagemaker_domain_id,
            domain_arn=sagemaker_domain_arn,
            pipeline_artifact_bucket=pipeline_artifact_bucket,
            model_bucket=model_bucket,
            repo_asset=build_app_asset,
            model_package_group_name=model_package_group_name,
            base_job_prefix=base_job_prefix,
            repository_type=repository_type,
            access_token_secret_name=access_token_secret_name,
            aws_codeconnection_arn=aws_codeconnection_arn,
            repository_owner=repository_owner,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            pipeline_artifact_bucket,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": (
                        "S3 access logs are not required for CI/CD pipeline artifact buckets"
                        "as they contain build artifacts, not user access data."
                    ),
                }
            ],
        )
