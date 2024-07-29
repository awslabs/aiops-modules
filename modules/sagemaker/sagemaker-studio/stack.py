# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List, Optional

import aws_cdk as core
import cdk_nag
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sagemaker as sagemaker
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.custom_resources import Provider
from constructs import Construct

from helper_constructs.sm_roles import SMRoles


class SagemakerStudioStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc_id: str,
        subnet_ids: List[str],
        studio_domain_name: Optional[str],
        studio_bucket_name: Optional[str],
        data_science_users: List[str],
        lead_data_science_users: List[str],
        app_image_config_name: Optional[str],
        image_name: Optional[str],
        enable_custom_sagemaker_projects: bool,
        enable_domain_resource_isolation: bool,
        auth_mode: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        self.subnets = [ec2.Subnet.from_subnet_id(self, f"SUBNET-{subnet_id}", subnet_id) for subnet_id in subnet_ids]

        domain_name = studio_domain_name or f"{construct_id}-studio-domain"
        s3_bucket_prefix = studio_bucket_name or f"{construct_id}-bucket"

        # create roles to be used for sagemaker user profiles and attached to sagemaker studio domain
        self.sm_roles = SMRoles(self, "sm-roles", s3_bucket_prefix, kwargs["env"])

        # setup security group to be used for sagemaker studio domain
        sagemaker_sg = ec2.SecurityGroup(
            self,
            "SecurityGroup",
            vpc=self.vpc,
            description="Security Group for SageMaker Studio Notebook, Training Job and Hosting Endpoint",
        )

        sagemaker_sg.add_ingress_rule(sagemaker_sg, ec2.Port.all_traffic())

        # create sagemaker studio domain
        self.studio_domain = self.sagemaker_studio_domain(
            domain_name,
            self.sm_roles.sagemaker_studio_role,
            vpc_id=self.vpc.vpc_id,
            security_group_ids=[sagemaker_sg.security_group_id],
            subnet_ids=[subnet.subnet_id for subnet in self.subnets],
            app_image_config_name=app_image_config_name,
            image_name=image_name,
            auth_mode=auth_mode,
        )

        if enable_custom_sagemaker_projects:
            self.enable_sagemaker_projects(
                [
                    self.sm_roles.sagemaker_studio_role.role_arn,
                    self.sm_roles.data_scientist_role.role_arn,
                    self.sm_roles.lead_data_scientist_role.role_arn,
                ],
            )

        if enable_domain_resource_isolation:
            self.enable_domain_resource_isolation(
                [
                    self.sm_roles.sagemaker_studio_role,
                    self.sm_roles.data_scientist_role,
                    self.sm_roles.lead_data_scientist_role,
                ],
            )

        [
            sagemaker.CfnUserProfile(
                self,
                f"ds-{user}",
                domain_id=self.studio_domain.attr_domain_id,
                user_profile_name=user,
                user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                    execution_role=self.sm_roles.data_scientist_role.role_arn,
                ),
                single_sign_on_user_identifier="UserName" if auth_mode == "SSO" else None,
                single_sign_on_user_value=user if auth_mode == "SSO" else None,
            )
            for user in data_science_users
        ]

        [
            sagemaker.CfnUserProfile(
                self,
                f"lead-ds-{user}",
                domain_id=self.studio_domain.attr_domain_id,
                user_profile_name=user,
                user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                    execution_role=self.sm_roles.lead_data_scientist_role.role_arn,
                ),
                single_sign_on_user_identifier="UserName" if auth_mode == "SSO" else None,
                single_sign_on_user_value=user if auth_mode == "SSO" else None,
            )
            for user in lead_data_science_users
        ]

        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.sm_roles,
            apply_to_children=True,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for src account roles only",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Resource access restricted to resources",
                ),
            ],
        )

    def enable_sagemaker_projects(self, roles: List[str]) -> None:
        event_handler = PythonFunction(
            self,
            "sg-project-function",
            runtime=lambda_.Runtime.PYTHON_3_12,
            entry="functions/sm_studio/enable_sm_projects",
            timeout=core.Duration.seconds(120),
        )

        event_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:EnableSagemakerServicecatalogPortfolio",
                    "servicecatalog:ListAcceptedPortfolioShares",
                    "servicecatalog:AssociatePrincipalWithPortfolio",
                    "servicecatalog:AcceptPortfolioShare",
                    "iam:GetRole",
                ],
                resources=["*"],
            ),
        )

        provider = Provider(
            self,
            "sg-project-lead-provider",
            on_event_handler=event_handler,
        )

        core.CustomResource(
            self,
            "cs-sg-project",
            service_token=provider.service_token,
            removal_policy=core.RemovalPolicy.DESTROY,
            resource_type="Custom::EnableSageMakerProjects",
            properties={
                "iteration": 1,
                "ExecutionRoles": roles,
            },
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            [event_handler.role, provider],  # type: ignore[list-item]
            apply_to_children=True,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for src account roles only",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Resource access restricted to resources",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            provider,
            apply_to_children=True,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-L1", reason="We don't control the version used by the Provider construct."
                ),
            ],
        )

    def enable_domain_resource_isolation(self, roles: List[iam.Role]) -> None:
        policy = iam.Policy(
            self,
            "sm_domain_resource_isolation_policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=[
                        "sagemaker:Update*",
                        "sagemaker:Delete*",
                        "sagemaker:Describe*",
                    ],
                    not_resources=[
                        f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:domain/{self.studio_domain.attr_domain_id}",
                        f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:user-profile/{self.studio_domain.attr_domain_id}/*",
                        f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:project/*",
                        f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:app/*",
                    ],
                    conditions={
                        "StringNotEquals": {
                            "aws:ResourceTag/sagemaker:domain-arn": (
                                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:"
                                f"domain/{self.studio_domain.attr_domain_id}"
                            )
                        }
                    },
                )
            ],
        )

        for role in roles:
            role.attach_inline_policy(policy)

    def sagemaker_studio_domain(
        self,
        domain_name: str,
        sagemaker_studio_role: iam.Role,
        security_group_ids: List[str],
        subnet_ids: List[str],
        vpc_id: str,
        app_image_config_name: Optional[str],
        image_name: Optional[str],
        auth_mode: str,
    ) -> sagemaker.CfnDomain:
        """
        Create the SageMaker Studio Domain

        :param domain_name: - name to assign to the SageMaker Studio Domain
        :param s3_bucket: - S3 bucket used for sharing notebooks between users
        :param sagemaker_studio_role: - IAM Execution Role for the domain
        :param security_group_ids: - list of comma separated security group ids
        :param subnet_ids: - list of comma separated subnet ids
        :param vpc_id: - VPC Id for the domain
        """
        custom_kernel_settings = {}
        if app_image_config_name is not None and image_name is not None:
            custom_kernel_settings["kernel_gateway_app_settings"] = (
                sagemaker.CfnDomain.KernelGatewayAppSettingsProperty(
                    custom_images=[
                        sagemaker.CfnDomain.CustomImageProperty(
                            app_image_config_name=app_image_config_name,
                            image_name=image_name,
                        ),
                    ],
                )
            )

        return sagemaker.CfnDomain(
            self,
            "sagemaker-domain",
            auth_mode=auth_mode,
            app_network_access_type="VpcOnly",
            default_user_settings=sagemaker.CfnDomain.UserSettingsProperty(
                execution_role=sagemaker_studio_role.role_arn,
                security_groups=security_group_ids,
                sharing_settings=sagemaker.CfnDomain.SharingSettingsProperty(),
                **custom_kernel_settings,  # type:ignore
            ),
            domain_name=domain_name,
            subnet_ids=subnet_ids,
            vpc_id=vpc_id,
        )
