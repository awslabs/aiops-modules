"""Seedfarmer module to deploy SageMaker Notebooks."""

from typing import Any, Dict, List, Optional

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_sagemaker as sagemaker
import cdk_nag
from aws_cdk import CfnOutput, Stack, Tags
from constructs import Construct


class SagemakerNotebookStack(Stack):
    """Create a Sagemaker Notebook."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        notebook_name: str,
        instance_type: str,
        direct_internet_access: Optional[str] = None,
        root_access: Optional[str] = None,
        volume_size_in_gb: Optional[int] = None,
        imds_version: Optional[str] = None,
        subnet_ids: Optional[List[str]] = None,
        vpc_id: Optional[str] = None,
        kms_key_arn: Optional[str] = None,
        code_repository: Optional[str] = None,
        additional_code_repositories: Optional[List[str]] = None,
        role_arn: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Deploy a SageMaker notebook.

        Parameters
        ----------
        scope
            Parent of this stack, usually an ``App`` or a ``Stage``, but could be any construct
        construct_id
            The construct ID of this stack
        notebook_name
            The name of the new notebook instance.
        instance_type
            The type of ML compute instance to launch for the notebook instance.
        direct_internet_access, optional
            Sets whether SageMaker provides internet access to the notebook instance, by default None
        root_access, optional
            Whether root access is enabled or disabled for users of the notebook instance, by default None
        volume_size_in_gb, optional
            The size, in GB, of the ML storage volume to attach to the notebook instance, by default None
        imds_version, optional
            The Instance Metadata Service (IMDS) version, by default None
        subnet_ids, optional
            A list of subnet IDs in a VPC to which you would like to have a connectivity, by default None.
            Only the first subnet id will be used.
        vpc_id, optional
            The ID of the VPC to which you would like to have a connectivity, by default None
        kms_key_arn, optional
            The ARN of a AWS KMS key that SageMaker uses to encrypt data on the storage volume attached, by default None
        code_repository, optional
            The Git repository associated with the notebook instance as its default code repository, by default None
        additional_code_repositories, optional
            An array of up to three Git repositories associated with the notebook instance, by default None
        role_arn, optional
            An IAM Role ARN that SageMaker assumes to perform tasks on your behalf, by default None
        tags, optional
            Extra tags to apply to the SageMaker notebook instance, by default None
        """
        super().__init__(scope, construct_id, **kwargs)

        self.notebook_name = notebook_name
        self.instance_type = instance_type
        self.direct_internet_access = direct_internet_access
        self.root_access = root_access
        self.volume_size_in_gb = volume_size_in_gb
        self.code_repository = code_repository
        self.imds_version = imds_version
        self.subnet_id = subnet_ids[0] if subnet_ids else None
        self.vpc_id = vpc_id
        self.kms_key_arn = kms_key_arn
        self.role_arn = role_arn
        self.additional_tags = tags

        self.additional_code_repositories = (
            ["https://github.com/aws/amazon-sagemaker-examples.git"]
            if additional_code_repositories is None
            else additional_code_repositories
        )

        self.setup_resources()

        self.setup_outputs()

        self.setup_tags()

        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.role,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for src account roles only",
                ),
            ],
        )
        if not kms_key_arn:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                self.sm_notebook,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-SM2",
                        reason="Customers have the option to disable encryption",
                    ),
                ],
            )
        if direct_internet_access:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                self.sm_notebook,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-SM3",
                        reason="Customers have the option to enable direct internet access",
                    ),
                ],
            )

    def setup_resources(self) -> None:
        """Deploy resources."""
        self.vpc = self.get_vpc()

        self.security_group = self.get_security_group()

        self.role = self.get_role()

        self.sm_notebook = self.get_sm_notebook()

    def setup_tags(self) -> None:
        """Add tags to all resources."""
        Tags.of(self).add("sagemaker:deployment-stage", Stack.of(self).stack_name)
        for k, v in (self.additional_tags or {}).items():
            Tags.of(self).add(k, v)

    def setup_outputs(self) -> None:
        """Setups outputs and metadata."""
        CfnOutput(scope=self, id="SageMakerNotebookArn", value=self.sm_notebook.ref)

        CfnOutput(
            scope=self,
            id="SageMakerNotebookName",
            value=self.notebook_name,
        )
        CfnOutput(
            scope=self,
            id="metadata",
            value=self.to_json_string({"SageMakerNotebookArn": self.sm_notebook.ref}),
        )

    def get_sm_notebook(self) -> sagemaker.CfnNotebookInstance:
        """Deploy a SageMaker Notebook instance.

        Returns
        -------
            A SageMaker Notebook Instance
        """
        security_group_ids: Optional[List[str]] = None
        metadata_config: Optional[Any] = None

        if self.security_group:
            security_group_ids = [self.security_group.security_group_id]

        if self.imds_version:
            metadata_config = sagemaker.CfnNotebookInstance.InstanceMetadataServiceConfigurationProperty(
                minimum_instance_metadata_service_version=self.imds_version
            )

        sm_notebook = sagemaker.CfnNotebookInstance(
            self,
            "SageMakerNotebookInstance",
            instance_type=self.instance_type,
            role_arn=self.role.role_arn,
            additional_code_repositories=self.additional_code_repositories,
            default_code_repository=self.code_repository,
            direct_internet_access=self.direct_internet_access,
            kms_key_id=self.kms_key_arn,
            notebook_instance_name=self.notebook_name,
            instance_metadata_service_configuration=metadata_config,
            root_access=self.root_access,
            security_group_ids=security_group_ids,
            subnet_id=self.subnet_id,
            volume_size_in_gb=self.volume_size_in_gb,
        )

        return sm_notebook

    def get_role(self) -> iam.IRole:
        """Get or create an IAM Role.

        Returns
        -------
            An IAM Role
        """
        if self.role_arn:
            return iam.Role.from_role_arn(self, "NotebookRole", role_arn=self.role_arn)

        role = iam.Role(
            self,
            "NotebookRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
        )

        if self.kms_key_arn:
            kms_key = kms.Key.from_key_arn(self, "KMSKey", key_arn=self.kms_key_arn)
            kms_key.grant_encrypt_decrypt(role)

        return role

    def get_vpc(self) -> Optional[ec2.IVpc]:
        """Get the VPC by ID.

        Returns
        -------
            An VPC, defaults None.
        """
        if self.vpc_id:
            return ec2.Vpc.from_lookup(self, "VPC", vpc_id=self.vpc_id)

        return None

    def get_security_group(self) -> Optional[ec2.SecurityGroup]:
        """Deploy a security group if VPC is not none.

        Returns
        -------
            A Security Group, defaults None.
        """
        if self.vpc:
            security_group = ec2.SecurityGroup(self, "SecurityGroup", vpc=self.vpc, allow_all_outbound=True)
            security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.all_tcp(),
            )

            return security_group

        return None
