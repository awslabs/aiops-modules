# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from typing import Any, List, Optional, TypedDict

import constructs
from aws_cdk import Aspects, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sagemaker as sagemaker
from cdk_nag import AwsSolutionsChecks, NagPackSuppression, NagSuppressions
from scripts.get_approved_package import get_approved_package
from typing_extensions import NotRequired, Required


class EndpointConfigProductionVariant(TypedDict):
    variant_name: Required[str]
    initial_instance_count: NotRequired[float]
    initial_variant_weight: Required[float]
    instance_type: NotRequired[str]


def get_timestamp() -> str:
    now = datetime.now().replace(tzinfo=timezone.utc)
    return now.strftime("%Y%m%d%H%M%S")


class DeployEndpointStack(Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_prefix: str,
        sagemaker_project_id: Optional[str],
        sagemaker_project_name: Optional[str],
        model_package_arn: Optional[str],
        model_package_group_name: Optional[str],
        model_execution_role_arn: Optional[str],
        vpc_id: str,
        subnet_ids: List[str],
        model_bucket_arn: Optional[str],
        ecr_repo_arn: Optional[str],
        endpoint_config_prod_variant: EndpointConfigProductionVariant,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        if sagemaker_project_id:
            Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        if sagemaker_project_name:
            Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)

        # Import VPC, create security group, and add ingress rule
        vpc = ec2.Vpc.from_lookup(self, f"{app_prefix}-vpc", vpc_id=vpc_id)
        security_group = ec2.SecurityGroup(self, f"{app_prefix}-sg", vpc=vpc, allow_all_outbound=True)
        security_group.add_ingress_rule(peer=ec2.Peer.ipv4(vpc.vpc_cidr_block), connection=ec2.Port.all_tcp())

        if not model_execution_role_arn:
            # Create model execution role
            model_execution_role = iam.Role(
                self,
                f"{app_prefix}-model-exec-role",
                assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                ],
            )

            if model_bucket_arn:
                # Grant model assets bucket read-write permissions
                model_bucket = s3.Bucket.from_bucket_arn(self, f"{app_prefix}-model-bucket", model_bucket_arn)
                model_bucket.grant_read_write(model_execution_role)

            if ecr_repo_arn:
                # Add ECR permissions
                model_execution_role.add_to_policy(
                    iam.PolicyStatement(
                        actions=["ecr:Get*"],
                        effect=iam.Effect.ALLOW,
                        resources=[ecr_repo_arn],
                    )
                )

            model_execution_role_arn: str = model_execution_role.role_arn

        self.model_execution_role_arn = model_execution_role_arn

        if not model_package_arn:
            # Get latest approved model package from the model registry
            model_package_arn = get_approved_package(self.region, model_package_group_name)

        # Create model instance
        model_name = f"{app_prefix}-{get_timestamp()}"
        model = sagemaker.CfnModel(
            self,
            f"{app_prefix}-model",
            execution_role_arn=model_execution_role_arn,
            model_name=model_name,
            containers=[sagemaker.CfnModel.ContainerDefinitionProperty(model_package_name=model_package_arn)],
            vpc_config=sagemaker.CfnModel.VpcConfigProperty(
                security_group_ids=[security_group.security_group_id],
                subnets=subnet_ids,
            ),
        )
        self.model = model

        # Create kms key to be used by the endpoint assets bucket
        kms_key = kms.Key(
            self,
            f"{app_prefix}-endpoint-key",
            description="Key used for encryption of data in Amazon SageMaker Endpoint",
            enable_key_rotation=True,
        )
        kms_key.grant_encrypt_decrypt(iam.AccountRootPrincipal())

        # Create endpoint config
        endpoint_config_name = f"{app_prefix}-endpoint-config"
        endpoint_config_prod_variant = endpoint_config_prod_variant or {}
        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            f"{app_prefix}-endpoint-config",
            endpoint_config_name=endpoint_config_name,
            kms_key_id=kms_key.key_id,
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    model_name=model_name,
                    **endpoint_config_prod_variant,
                )
            ],
        )
        endpoint_config.add_depends_on(model)

        # Create endpoint
        endpoint_name = f"{app_prefix}-endpoint"
        endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
            endpoint_config_name=endpoint_config.endpoint_config_name,
            endpoint_name=endpoint_name,
        )
        endpoint.add_depends_on(endpoint_config)
        self.endpoint = endpoint

        # Add CDK nag solutions checks
        Aspects.of(self).add(AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for service account roles only.",
                )
            ],
        )

        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Model execution role requires s3 permissions to the bucket.",
                )
            ],
        )
