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
        enable_jupyterlab_app: bool,
        enable_jupyterlab_app_sharing: bool,
        enable_docker_access: bool,
        vpc_only_trusted_accounts: List[str],
        jupyterlab_app_instance_type: Optional[str],
        idle_timeout_in_minutes: Optional[int],
        max_idle_timeout_in_minutes: Optional[int],
        min_idle_timeout_in_minutes: Optional[int],
        auth_mode: str,
        role_path: Optional[str],
        permissions_boundary_arn: Optional[str],
        mlflow_enabled: bool,
        mlflow_server_name: str,
        mlflow_server_version: Optional[str],
        mlflow_server_size: Optional[str],
        mlflow_artifact_store_bucket_name: Optional[str],
        mlflow_artifact_store_bucket_prefix: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        self.subnets = [ec2.Subnet.from_subnet_id(self, f"SUBNET-{subnet_id}", subnet_id) for subnet_id in subnet_ids]

        domain_name = studio_domain_name or f"{construct_id}-studio-domain"
        s3_bucket_prefix = studio_bucket_name or f"{construct_id}-bucket"

        # create roles to be used for sagemaker user profiles and attached to sagemaker studio domain
        self.sm_roles = SMRoles(
            self,
            "sm-roles",
            s3_bucket_prefix=s3_bucket_prefix,
            mlflow_artifact_store_bucket_name=mlflow_artifact_store_bucket_name,
            role_path=role_path,
            permissions_boundary_arn=permissions_boundary_arn,
            env=kwargs["env"],
        )

        # create sagemaker studio domain
        self.studio_domain = self.sagemaker_studio_domain(
            domain_name,
            self.sm_roles.sagemaker_studio_role,
            vpc_id=self.vpc.vpc_id,
            subnet_ids=[subnet.subnet_id for subnet in self.subnets],
            app_image_config_name=app_image_config_name,
            image_name=image_name,
            auth_mode=auth_mode,
            enable_docker_access=enable_docker_access,
            vpc_only_trusted_accounts=vpc_only_trusted_accounts,
            idle_timeout_in_minutes=idle_timeout_in_minutes,
            max_idle_timeout_in_minutes=max_idle_timeout_in_minutes,
            min_idle_timeout_in_minutes=min_idle_timeout_in_minutes,
        )

        if enable_custom_sagemaker_projects:
            self.enable_sagemaker_projects(
                roles=[
                    self.sm_roles.sagemaker_studio_role.role_arn,
                    self.sm_roles.data_scientist_role.role_arn,
                    self.sm_roles.lead_data_scientist_role.role_arn,
                ],
                vpc=self.vpc,
                subnets=self.subnets,
                role_path=role_path,
                permissions_boundary_arn=permissions_boundary_arn,
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
            self.create_user_profile_and_space(
                id=f"ds-{user}",
                user=user,
                auth_mode=auth_mode,
                role_arn=self.sm_roles.data_scientist_role.role_arn,
                enable_jupyterlab_app=enable_jupyterlab_app,
                enable_jupyterlab_app_sharing=enable_jupyterlab_app_sharing,
                jupyterlab_app_instance_type=jupyterlab_app_instance_type,
            )
            for user in data_science_users
        ]

        [
            self.create_user_profile_and_space(
                id=f"lead-ds-{user}",
                user=user,
                auth_mode=auth_mode,
                role_arn=self.sm_roles.lead_data_scientist_role.role_arn,
                enable_jupyterlab_app=enable_jupyterlab_app,
                enable_jupyterlab_app_sharing=enable_jupyterlab_app_sharing,
                jupyterlab_app_instance_type=jupyterlab_app_instance_type,
            )
            for user in lead_data_science_users
        ]

        self.mlflow_server = None

        if mlflow_enabled:
            self.mlflow_server = self.mlflow_tracking_server(
                mlflow_server_name=mlflow_server_name,
                mlflow_server_version=mlflow_server_version,
                mlflow_server_size=mlflow_server_size,
                mlflow_artifact_store_bucket_name=mlflow_artifact_store_bucket_name,
                mlflow_artifact_store_bucket_prefix=mlflow_artifact_store_bucket_prefix,
            )

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

    def enable_sagemaker_projects(
        self,
        roles: List[str],
        vpc: ec2.IVpc,
        subnets: List[ec2.ISubnet],
        role_path: Optional[str],
        permissions_boundary_arn: Optional[str],
    ) -> None:
        permissions_boundary = (
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "Boundary",
                managed_policy_arn=permissions_boundary_arn,
            )
            if permissions_boundary_arn
            else None
        )

        lambda_role = iam.Role(
            self,
            "enable-projects-lambda-role",
            path=role_path,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            permissions_boundary=permissions_boundary,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole",
                ),
            ],
            inline_policies={
                "EnableSagemakerProjects": iam.PolicyDocument(
                    statements=[
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
                    ],
                ),
            },
        )

        event_handler = PythonFunction(
            self,
            "sg-project-function",
            runtime=lambda_.Runtime.PYTHON_3_11,
            entry="functions/sm_studio/enable_sm_projects",
            timeout=core.Duration.seconds(120),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=subnets),
            role=lambda_role,
        )

        provider_role = iam.Role(
            self,
            "enable-projects-provider-role",
            path=role_path,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            permissions_boundary=permissions_boundary,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole",
                ),
            ],
        )

        provider = Provider(
            self,
            "sg-project-lead-provider",
            on_event_handler=event_handler,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=subnets),
            role=provider_role,
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
            [event_handler],
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Not all partitions support latest runtime (Python 3.12)",
                )
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            [lambda_role, provider_role],  # type: ignore[list-item]
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
                        f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:space/*",
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

    def _create_jupyter_lab_app_settings(
        self,
        app_image_config_name: Optional[str] = None,
        image_name: Optional[str] = None,
        idle_timeout_in_minutes: Optional[int] = None,
        max_idle_timeout_in_minutes: Optional[int] = None,
        min_idle_timeout_in_minutes: Optional[int] = None,
    ) -> Optional[sagemaker.CfnDomain.JupyterLabAppSettingsProperty]:
        """Create JupyterLabAppSettingsProperty with custom images and/or app lifecycle management."""
        # Initialize settings dict
        jupyter_lab_settings_props = {}

        # Add custom images if provided
        if app_image_config_name is not None and image_name is not None:
            jupyter_lab_settings_props["custom_images"] = [
                sagemaker.CfnDomain.CustomImageProperty(
                    app_image_config_name=app_image_config_name,
                    image_name=image_name,
                )
            ]

        # Add app lifecycle management with idle settings
        # First check if min or max is defined without idle_timeout
        if (
            max_idle_timeout_in_minutes is not None or min_idle_timeout_in_minutes is not None
        ) and idle_timeout_in_minutes is None:
            raise ValueError("idle_timeout_in_minutes is required when min or max idle timeout is set")

        # Configure idle settings based on parameter presence
        idle_settings_props = {"lifecycle_management": "ENABLED" if idle_timeout_in_minutes is not None else "DISABLED"}

        # Add timeout parameters if they exist
        if idle_timeout_in_minutes is not None:
            idle_settings_props["idle_timeout_in_minutes"] = idle_timeout_in_minutes
        if max_idle_timeout_in_minutes is not None:
            idle_settings_props["max_idle_timeout_in_minutes"] = max_idle_timeout_in_minutes
        if min_idle_timeout_in_minutes is not None:
            idle_settings_props["min_idle_timeout_in_minutes"] = min_idle_timeout_in_minutes

        # Set the app lifecycle management property
        jupyter_lab_settings_props["app_lifecycle_management"] = sagemaker.CfnDomain.AppLifecycleManagementProperty(
            idle_settings=sagemaker.CfnDomain.IdleSettingsProperty(**idle_settings_props)
        )

        return sagemaker.CfnDomain.JupyterLabAppSettingsProperty(**jupyter_lab_settings_props)

    def sagemaker_studio_domain(
        self,
        domain_name: str,
        sagemaker_studio_role: iam.Role,
        subnet_ids: List[str],
        vpc_id: str,
        app_image_config_name: Optional[str],
        image_name: Optional[str],
        auth_mode: str,
        enable_docker_access: bool,
        vpc_only_trusted_accounts: List[str],
        idle_timeout_in_minutes: Optional[int] = None,
        max_idle_timeout_in_minutes: Optional[int] = None,
        min_idle_timeout_in_minutes: Optional[int] = None,
    ) -> sagemaker.CfnDomain:
        """
        Create the SageMaker Studio Domain

        :param domain_name: - name to assign to the SageMaker Studio Domain
        :param sagemaker_studio_role: - IAM Execution Role for the domain
        :param subnet_ids: - list of comma separated subnet ids
        :param vpc_id: -  VPC Id for the domain
        :param app_image_config_name: - config name
        :param image_name: - image name
        :param auth_mode: - auth mode (IAM or SSO)
        :param enable_docker_access: - flag to enable docker from studio
        :param vpc_only_trusted_accounts: - list of trusted aws account ids in vpc only mode
        :param idle_timeout_in_minutes: - idle timeout in minutes
        :param max_idle_timeout_in_minutes: - maximum idle timeout in minutes
        :param min_idle_timeout_in_minutes: - minimum idle timeout in minutes
        """
        sagemaker_sg = ec2.SecurityGroup(
            self,
            "SecurityGroup",
            vpc=self.vpc,
            description="Security Group for SageMaker Studio Notebook, Training Job and Hosting Endpoint",
        )
        sagemaker_sg.add_ingress_rule(sagemaker_sg, ec2.Port.all_traffic())

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

        # Create user settings
        user_settings_props = {
            "execution_role": sagemaker_studio_role.role_arn,
            "security_groups": [sagemaker_sg.security_group_id],
            "sharing_settings": sagemaker.CfnDomain.SharingSettingsProperty(),
            **custom_kernel_settings,  # type:ignore
        }

        # Get JupyterLab app settings if available
        jupyter_lab_app_settings = self._create_jupyter_lab_app_settings(
            app_image_config_name=app_image_config_name,
            image_name=image_name,
            idle_timeout_in_minutes=idle_timeout_in_minutes,
            max_idle_timeout_in_minutes=max_idle_timeout_in_minutes,
            min_idle_timeout_in_minutes=min_idle_timeout_in_minutes,
        )

        if jupyter_lab_app_settings:
            user_settings_props["jupyter_lab_app_settings"] = jupyter_lab_app_settings

        return sagemaker.CfnDomain(
            self,
            "sagemaker-domain",
            auth_mode=auth_mode,
            app_network_access_type="VpcOnly",
            domain_settings=sagemaker.CfnDomain.DomainSettingsProperty(
                docker_settings=sagemaker.CfnDomain.DockerSettingsProperty(
                    enable_docker_access="ENABLED" if enable_docker_access else "DISABLED",
                    vpc_only_trusted_accounts=vpc_only_trusted_accounts if vpc_only_trusted_accounts else None,
                ),
            ),
            default_user_settings=sagemaker.CfnDomain.UserSettingsProperty(**user_settings_props),
            domain_name=domain_name,
            subnet_ids=subnet_ids,
            vpc_id=vpc_id,
        )

    def mlflow_tracking_server(
        self,
        mlflow_server_name: str,
        mlflow_server_version: Optional[str],
        mlflow_server_size: Optional[str],
        mlflow_artifact_store_bucket_name: Optional[str],
        mlflow_artifact_store_bucket_prefix: str,
    ) -> sagemaker.CfnMlflowTrackingServer:
        return sagemaker.CfnMlflowTrackingServer(
            self,
            "MlflowTrackingServer",
            tracking_server_name=mlflow_server_name,
            role_arn=self.sm_roles.mlflow_tracking_server_role.role_arn,
            artifact_store_uri=f"s3://{mlflow_artifact_store_bucket_name}{mlflow_artifact_store_bucket_prefix}",
            mlflow_version=mlflow_server_version,
            tracking_server_size=mlflow_server_size,
            automatic_model_registration=False,
        )

    def create_user_profile_and_space(
        self,
        id: str,
        user: str,
        auth_mode: str,
        role_arn: str,
        enable_jupyterlab_app: bool,
        enable_jupyterlab_app_sharing: bool,
        jupyterlab_app_instance_type: Optional[str],
    ) -> sagemaker.CfnUserProfile:
        user_profile = sagemaker.CfnUserProfile(
            self,
            id,
            domain_id=self.studio_domain.attr_domain_id,
            user_profile_name=user,
            user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                execution_role=role_arn,
            ),
            single_sign_on_user_identifier="UserName" if auth_mode == "SSO" else None,
            single_sign_on_user_value=user if auth_mode == "SSO" else None,
        )

        if enable_jupyterlab_app:
            user_space = sagemaker.CfnSpace(
                self,
                f"space-{user}",
                domain_id=self.studio_domain.attr_domain_id,
                space_name=f"{user}-JupyterLab-space",
                space_display_name=f"{user}-JupyterLab-space",
                space_settings=sagemaker.CfnSpace.SpaceSettingsProperty(
                    app_type="JupyterLab",
                    jupyter_lab_app_settings=sagemaker.CfnSpace.SpaceJupyterLabAppSettingsProperty(
                        default_resource_spec=sagemaker.CfnSpace.ResourceSpecProperty(
                            instance_type=jupyterlab_app_instance_type,
                        )
                    )
                    if jupyterlab_app_instance_type
                    else None,
                ),
                ownership_settings=sagemaker.CfnSpace.OwnershipSettingsProperty(owner_user_profile_name=user),
                space_sharing_settings=sagemaker.CfnSpace.SpaceSharingSettingsProperty(
                    sharing_type="Shared" if enable_jupyterlab_app_sharing else "Private",
                ),
            )
            user_space.add_dependency(user_profile)
        return user_profile
