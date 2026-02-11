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
        sagemaker_project_id: Optional[str],
        sagemaker_project_name: Optional[str],
        sagemaker_domain_id: Optional[str],
        sagemaker_domain_arn: Optional[str],
        model_package_arn: Optional[str],
        model_package_group_name: Optional[str],
        model_execution_role_arn: Optional[str],
        vpc_id: str,
        subnet_ids: List[str],
        enable_network_isolation: bool,
        model_artifacts_bucket_arn: Optional[str],
        ecr_repo_arn: Optional[str],
        endpoint_config_prod_variant: Dict[str, Any],
        managed_instance_scaling: bool,
        scaling_min_instance_count: int,
        scaling_max_instance_count: int,
        data_capture_sampling_percentage: int,
        data_capture_prefix: str,
        permissions_boundary_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Apply permissions boundary to all roles in this stack if provided
        if permissions_boundary_name:
            permissions_boundary_policy = iam.ManagedPolicy.from_managed_policy_name(
                self, "PermBoundary", permissions_boundary_name
            )
            iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)

        if sagemaker_project_id:
            Tags.of(self).add("sagemaker:project-id", sagemaker_project_id)
        if sagemaker_project_name:
            Tags.of(self).add("sagemaker:project-name", sagemaker_project_name)
        if sagemaker_domain_id:
            Tags.of(self).add("sagemaker:domain-id", sagemaker_domain_id)
        if sagemaker_domain_arn:
            Tags.of(self).add("sagemaker:domain-arn", sagemaker_domain_arn)

        enable_data_capture = data_capture_sampling_percentage > 0

        # Import VPC, create security group, and add ingress rule
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        self.security_group = ec2.SecurityGroup(self, "Security Group", vpc=vpc, allow_all_outbound=True)
        self.security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.all_tcp(),
        )

        self.model_execution_role: iam.IRole
        if not model_execution_role_arn:
            # Create model execution role
            self.model_execution_role = iam.Role(
                self,
                "Model Execution Role",
                assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            )

            self.model_execution_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "cloudwatch:PutMetricData",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:CreateLogGroup",
                        "logs:DescribeLogStreams",
                        "ecr:GetAuthorizationToken",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateNetworkInterfacePermission",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteNetworkInterfacePermission",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                    ],
                    resources=["*"],
                ),
            )
            self.model_execution_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "kms:Encrypt",
                        "kms:ReEncrypt*",
                        "kms:GenerateDataKey*",
                        "kms:Decrypt",
                        "kms:DescribeKey",
                    ],
                    resources=[f"arn:{self.partition}:kms:{self.region}:{self.account}:key/*"],
                ),
            )

            if model_artifacts_bucket_arn:
                # Grant model assets bucket read permissions
                model_bucket = s3.Bucket.from_bucket_arn(self, "Model Bucket", model_artifacts_bucket_arn)
                model_bucket.grant_read(self.model_execution_role)
                if enable_data_capture:
                    # Ensure the model execution role can write to the data capture prefix.
                    model_bucket.grant_write(self.model_execution_role, f"{data_capture_prefix}/*")
            else:
                self.model_execution_role.add_to_policy(
                    iam.PolicyStatement(
                        actions=["s3:ListBucket", "s3:GetObject"],
                        resources=["*"],
                    )
                )

            # Add ECR permissions
            ecr_repo_arn = ecr_repo_arn if ecr_repo_arn else "*"
            self.model_execution_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[ecr_repo_arn],
                )
            )

        else:
            self.model_execution_role = iam.Role.from_role_arn(self, "Model Execution Role", model_execution_role_arn)

        if not model_package_arn:
            # Get latest approved model package from the model registry
            if model_package_group_name:
                model_package_arn = get_approved_package(self.region, model_package_group_name)
            else:
                raise ValueError("Either model_package_arn or model_package_group_name is required")

        self.model_package_arn = model_package_arn

        # Create model instance
        model_name: str = f"{id[:42]}-model-{get_timestamp()}"
        model = sagemaker.CfnModel(
            self,
            "Model",
            enable_network_isolation=enable_network_isolation,
            execution_role_arn=self.model_execution_role.role_arn,
            model_name=model_name,
            containers=[sagemaker.CfnModel.ContainerDefinitionProperty(model_package_name=model_package_arn)],
            vpc_config=sagemaker.CfnModel.VpcConfigProperty(
                security_group_ids=[self.security_group.security_group_id],
                subnets=subnet_ids,
            ),
        )
        self.model = model

        # Create kms key to be used by the endpoint assets bucket
        self.kms_key = kms.Key(
            self,
            "Endpoint Key",
            description="Key used for encryption of data in Amazon SageMaker Endpoint",
            enable_key_rotation=True,
        )
        self.kms_key.grant_encrypt_decrypt(iam.AccountRootPrincipal())

        # Create endpoint config
        if enable_data_capture:
            if not model_artifacts_bucket_arn:
                raise ValueError("Must provide 'model_artifacts_bucket_arn' to enable data capture")

            destination_s3_uri = f"s3://{model_artifacts_bucket_arn.split(':')[-1]}/{data_capture_prefix}"

            capture_options = [
                sagemaker.CfnEndpointConfig.CaptureOptionProperty(capture_mode="Input"),
                sagemaker.CfnEndpointConfig.CaptureOptionProperty(capture_mode="Output"),
            ]
            data_capture_config = sagemaker.CfnEndpointConfig.DataCaptureConfigProperty(
                capture_options=capture_options,
                destination_s3_uri=destination_s3_uri,
                initial_sampling_percentage=data_capture_sampling_percentage,
                capture_content_type_header=sagemaker.CfnEndpointConfig.CaptureContentTypeHeaderProperty(
                    csv_content_types=["text/csv"],
                    json_content_types=["application/json"],
                ),
                enable_capture=True,
                kms_key_id=self.kms_key.key_id,
            )
        else:
            data_capture_config = None

        endpoint_config_name: str = f"{id[:42]}-conf-{get_timestamp()}"
        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "Endpoint Configuration",
            data_capture_config=data_capture_config,
            endpoint_config_name=endpoint_config_name,
            kms_key_id=self.kms_key.key_id,
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    model_name=model_name,
                    **endpoint_config_prod_variant,
                    managed_instance_scaling=sagemaker.CfnEndpointConfig.ManagedInstanceScalingProperty(
                        max_instance_count=scaling_max_instance_count,
                        min_instance_count=scaling_min_instance_count,
                    )
                    if managed_instance_scaling
                    else None,
                )
            ],
        )
        endpoint_config.add_dependency(model)

        # Create endpoint
        endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
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
                        id="AwsSolutions-IAM5",
                        reason="Model execution role requires some generic permissions.",
                    ),
                ],
            )
