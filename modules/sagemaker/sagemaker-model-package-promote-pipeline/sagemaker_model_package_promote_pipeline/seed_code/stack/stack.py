"""Sagemaker Model Package stack."""
import json
import string
from typing import Optional

import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3deploy
import aws_cdk.aws_sagemaker as sagemaker
from aws_cdk import CfnOutput, RemovalPolicy, Stack
from constructs import Construct
from stack.models import ModelMetadata


class SagemakerModelPackageStack(Stack):
    """Create a Sagemaker Model Package."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        model_metadata_path: str,
        bucket_name: str,
        retain_on_delete: bool = True,
        model_package_group_name: Optional[str] = None,
        kms_key_arn: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Create a Sagemaker Model Package.

        Parameters
        ----------
        scope
            Parent of this stack, usually an ``App`` or a ``Stage``, but could be any construct
        construct_id
            The construct ID of this stack
        model_metadata_path
            The filepath for model metadata.
        bucket_name
            The S3 bucket name to store model artifacts.
        retain_on_delete, optional
            Wether or not to retain resources on delete. Defaults True.
        model_package_group_name, optional
            The SageMaker model package group name to register the model package. Defaults None. If None
            it will use the model package group name that is in the model metadata.
        kms_key_arn, optional
            A KMS Key ARN to encrypt model artifacts in S3. Defaults None.
        """
        super().__init__(scope, construct_id, **kwargs)

        self.model_metadata_path = model_metadata_path
        self.bucket_name = bucket_name

        self.kms_key_arn = kms_key_arn
        self.retain_on_delete = retain_on_delete
        self.removal_policy = (
            RemovalPolicy.RETAIN if retain_on_delete else RemovalPolicy.DESTROY
        )

        self.model_metadata = self.load_model_metadata()
        if not self.model_metadata.model:
            return

        # Upd model package group name in metadata
        if model_package_group_name:
            self.model_metadata.model.model_package_group_name = (
                model_package_group_name
            )

        self.setup_resources()

        self.setup_outputs()

    def setup_outputs(self) -> None:
        """Setups outputs and metadata."""
        metadata = {}
        if self.model_package.attr_model_package_arn:
            metadata[
                "SagemakerModelPackageArn"
            ] = self.model_package.attr_model_package_arn
        if self.model_package.model_package_name:
            metadata[
                "SagemakerModelPackageName"
            ] = self.model_package.model_package_name
        if self.model_package.model_package_group_name:
            metadata[
                "SagemakerModelPackageGroupName"
            ] = self.model_package.model_package_group_name

        for key, value in metadata.items():
            CfnOutput(scope=self, id=key, value=value)

        CfnOutput(scope=self, id="metadata", value=self.to_json_string(metadata))

    def setup_resources(self) -> None:
        """Deploy resources."""
        self.kms_key = self.setup_kms_key()

        self.model_package = self.create_model_package()

    def setup_kms_key(self) -> Optional[kms.IKey]:
        """Setup a KMS Key.

        Returns
        -------
            A KMS Key instance or None.
        """
        if not self.kms_key_arn:
            return None

        kms_key = kms.Key.from_key_arn(self, "KMSKey", key_arn=self.kms_key_arn)

        return kms_key

    def create_model_package(self) -> sagemaker.CfnModelPackage:
        """Create a Model Package.

        Returns
        -------
            A ModelPackage instance.
        """
        artifacts = self.deploy_model_artifacts()

        model_package = sagemaker.CfnModelPackage(
            self, "ModelPackage", **self.model_metadata.model.model_dump()
        )

        model_package.node.add_dependency(artifacts)

        model_package.apply_removal_policy(self.removal_policy)

        return model_package

    def deploy_model_artifacts(self) -> s3deploy.BucketDeployment:
        """Upload model artifacts to S3.

        Returns
        -------
            A BucketDeployment instance.
        """
        bucket_deployment_role = iam.Role(
            self,
            "BucketDeploymentRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )

        self.bucket = s3.Bucket.from_bucket_name(
            self,
            "ModelArtifactsBucket",
            bucket_name=self.bucket_name,
        )

        self.bucket.grant_read_write(bucket_deployment_role)

        encryption, kms_key_arn = s3deploy.ServerSideEncryption.AES_256, None
        if self.kms_key:
            self.kms_key.grant_encrypt_decrypt(bucket_deployment_role)
            encryption = s3deploy.ServerSideEncryption.AWS_KMS
            kms_key_arn = self.kms_key.key_arn

        deployment = s3deploy.BucketDeployment(
            self,
            "DeployModelArtifacts",
            sources=[s3deploy.Source.asset(self.model_metadata.artifacts)],
            destination_bucket=self.bucket,
            extract=True,
            prune=False,
            retain_on_delete=self.retain_on_delete,
            server_side_encryption=encryption,
            server_side_encryption_aws_kms_key_id=kms_key_arn,
            role=bucket_deployment_role,
        )

        return deployment

    def load_model_metadata(self) -> ModelMetadata:
        """Load model metadata template from a JSON file and replace the bucket name.

        The model metadata template contains model metadata with the bucket name as a variable. The
        bucket name is replaced to reflect the target S3 bucket that model artifacts are going to be
        deployed.

        Returns
        -------
            A ModelMetadata instance.
        """
        with open(self.model_metadata_path, "r") as f:
            model_config = f.read()

        model_metadata = string.Template(model_config)
        model_metadata = model_metadata.safe_substitute(bucket_name=self.bucket_name)
        model_metadata = json.loads(model_metadata)

        settings = ModelMetadata(**model_metadata)

        return settings
