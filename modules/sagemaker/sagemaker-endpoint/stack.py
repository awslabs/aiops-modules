# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import constructs
from aws_cdk import Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sagemaker as sagemaker
from cdk_nag import NagPackSuppression, NagSuppressions

from scripts.get_approved_package import get_approved_package


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
        model_artifacts_bucket_arn: Optional[str],
        ecr_repo_arn: Optional[str],
        endpoint_config_prod_variant: Dict[str, Any],
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
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.all_tcp(),
        )

        self.model_execution_role: iam.IRole
        if not model_execution_role_arn:
            # Create model execution role
            self.model_execution_role = iam.Role(
                self,
                f"{app_prefix}-model-exec",
                assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                ],
            )

            if model_artifacts_bucket_arn:
                # Grant model assets bucket read permissions
                model_bucket = s3.Bucket.from_bucket_arn(self, f"{app_prefix}-model-bucket", model_artifacts_bucket_arn)
                model_bucket.grant_read(self.model_execution_role)

            if ecr_repo_arn:
                # Add ECR permissions
                self.model_execution_role.add_to_policy(
                    iam.PolicyStatement(
                        actions=["ecr:Get*"],
                        effect=iam.Effect.ALLOW,
                        resources=[ecr_repo_arn],
                    )
                )
        else:
            self.model_execution_role = iam.Role.from_role_arn(
                self, f"{app_prefix}-model-exec", model_execution_role_arn
            )

        if not model_package_arn:
            # Get latest approved model package from the model registry
            if model_package_group_name:
                model_package_arn = get_approved_package(self.region, model_package_group_name)
            else:
                raise ValueError("Either model_package_arn or model_package_group_name is required")

        self.model_package_arn = model_package_arn

        # Create model instance
        model_name: str = f"{app_prefix}-model-{get_timestamp()}"
        model = sagemaker.CfnModel(
            self,
            f"{app_prefix}-model",
            execution_role_arn=self.model_execution_role.role_arn,
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
        endpoint_config_name: str = f"{app_prefix}-conf-{get_timestamp()}"
        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            f"{app_prefix}-endpoint-conf",
            endpoint_config_name=endpoint_config_name,
            kms_key_id=kms_key.key_id,
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    model_name=model_name,
                    **endpoint_config_prod_variant,
                )
            ],
        )
        endpoint_config.add_dependency(model)

        # Create endpoint
        endpoint = sagemaker.CfnEndpoint(
            self,
            f"{app_prefix}-endpoint",
            endpoint_config_name=endpoint_config.endpoint_config_name,  # type: ignore[arg-type]
        )
        endpoint.add_dependency(endpoint_config)
        self.endpoint = endpoint
        self.endpoint_url = (
            f"https://runtime.sagemaker.{self.region}.amazonaws.com/endpoints/{endpoint.attr_endpoint_name}/invocations"
        )

        # Add CDK nag suppressions
        if not model_execution_role_arn:
            NagSuppressions.add_resource_suppressions(
                self.model_execution_role,
                apply_to_children=True,
                suppressions=[
                    NagPackSuppression(
                        id="AwsSolutions-IAM4",
                        reason="Managed Policies are for service account roles only.",
                    ),
                    NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="Model execution role requires s3 permissions to the bucket.",
                    ),
                ],
            )
