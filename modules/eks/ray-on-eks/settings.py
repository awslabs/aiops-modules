"""Defines the stack settings."""

from abc import ABC
from typing import Dict, Optional

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

    eks_cluster_name: str = Field(default="Disabled")
    eks_cluster_admin_role_arn: str = Field(default="Disabled")
    eks_oidc_arn: str = Field(default="Disabled")
    eks_openid_issuer: str = Field(default="Disabled")
    eks_cluster_endpoint: str = Field(default="Disabled")
    eks_cert_auth_data: str = Field(default="Disabled")
    namespace: str = Field(default="Disabled")
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


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    parameters: SeedFarmerParameters = Field(default_factory=SeedFarmerParameters)
    default: CdkDefaultSettings = Field(default_factory=CdkDefaultSettings)
