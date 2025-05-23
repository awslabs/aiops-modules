"""Defines the stack settings."""

from abc import ABC
from typing import Dict, List, Literal, Optional

from aws_cdk import DefaultStackSynthesizer
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CdkBaseSettings(BaseSettings, ABC):
    """Defines common configuration for settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        protected_namespaces=(),
        extra="ignore",
        populate_by_name=True,
    )


class SeedFarmerParameters(CdkBaseSettings):
    """Seedfarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    vpc_id: str
    subnet_ids: List[str]

    studio_domain_name: Optional[str] = Field(default=None)
    studio_bucket_name: Optional[str] = Field(default=None)
    app_image_config_name: Optional[str] = Field(default=None)
    image_name: Optional[str] = Field(default=None)
    enable_custom_sagemaker_projects: bool = Field(default=False)
    enable_domain_resource_isolation: bool = Field(default=True)
    enable_jupyterlab_app: bool = Field(default=False)
    enable_jupyterlab_app_sharing: bool = Field(default=False)
    enable_docker_access: bool = Field(default=False)
    vpc_only_trusted_accounts: List[str] = Field(default=[])
    jupyterlab_app_instance_type: Optional[str] = Field(default=None)
    auth_mode: Literal["IAM", "SSO"] = Field(default="IAM")
    role_path: Optional[str] = Field(default=None)
    permissions_boundary_arn: Optional[str] = Field(default=None)

    data_science_users: List[str] = Field(default=[])
    lead_data_science_users: List[str] = Field(default=[])

    idle_timeout_in_minutes: Optional[int] = Field(default=None)
    max_idle_timeout_in_minutes: Optional[int] = Field(default=None)
    min_idle_timeout_in_minutes: Optional[int] = Field(default=None)

    mlflow_enabled: bool = Field(default=False)
    mlflow_server_name: str = Field(default="mlflow")
    mlflow_server_version: Optional[str] = Field(default=None)
    mlflow_server_size: Optional[str] = Field(default=None)
    mlflow_artifact_store_bucket_name: Optional[str] = Field(default=None)
    mlflow_artifact_store_bucket_prefix: str = Field(default="/")

    tags: Optional[Dict[str, str]] = Field(default=None)


class SeedFarmerSettings(CdkBaseSettings):
    """Seedfarmer Settings.

    These parameters comes from seedfarmer by default.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_")

    project_name: str = Field(default="")
    deployment_name: str = Field(default="")
    module_name: str = Field(default="")

    @computed_field  # type: ignore
    @property
    def app_prefix(self) -> str:
        """Application prefix."""
        prefix = "-".join([self.project_name, self.deployment_name, self.module_name])
        return prefix


class CdkDefaultSettings(CdkBaseSettings):
    """CDK Default Settings.

    These parameters comes from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class CdkDefaultSynthesizerProps(CdkBaseSettings):
    """CDK Default Stack Synthesizer Properties."""

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    qualifier: Optional[str] = Field(default=None)
    cloud_formation_execution_role: Optional[str] = Field(default=None)
    deploy_role_arn: Optional[str] = Field(default=None)
    file_asset_publishing_role_arn: Optional[str] = Field(default=None)
    image_asset_publishing_role_arn: Optional[str] = Field(default=None)
    lookup_role_arn: Optional[str] = Field(default=None)

    @computed_field  # type: ignore
    @property
    def default_stack_synthesizer(self) -> Optional[DefaultStackSynthesizer]:
        """Customize stack synthesizer."""
        if any(
            [
                self.qualifier,
                self.cloud_formation_execution_role,
                self.deploy_role_arn,
                self.file_asset_publishing_role_arn,
                self.image_asset_publishing_role_arn,
                self.lookup_role_arn,
            ]
        ):
            return DefaultStackSynthesizer(
                qualifier=self.qualifier,
                cloud_formation_execution_role=self.cloud_formation_execution_role,
                deploy_role_arn=self.deploy_role_arn,
                file_asset_publishing_role_arn=self.file_asset_publishing_role_arn,
                image_asset_publishing_role_arn=self.image_asset_publishing_role_arn,
                lookup_role_arn=self.lookup_role_arn,
            )
        return None


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    parameters: SeedFarmerParameters = Field(default_factory=SeedFarmerParameters)
    default: CdkDefaultSettings = Field(default_factory=CdkDefaultSettings)
    synthesizer: CdkDefaultSynthesizerProps = Field(default_factory=CdkDefaultSynthesizerProps)
