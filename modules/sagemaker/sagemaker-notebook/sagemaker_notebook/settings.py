"""Defines the stack settings."""

from abc import ABC
from typing import Dict, List, Optional

from pydantic import Field, computed_field, field_validator
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

    notebook_name: str
    instance_type: str

    direct_internet_access: str = Field(default="Enabled")
    root_access: str = Field(default="Disabled")
    volume_size_in_gb: Optional[int] = Field(default=None)
    imds_version: str = Field(default="2")
    subnet_ids: Optional[List[str]] = Field(default=None)
    code_repository: Optional[str] = Field(default=None)
    additional_code_repositories: Optional[List[str]] = Field(default=None)
    vpc_id: Optional[str] = Field(default=None)
    kms_key_arn: Optional[str] = Field(default=None)
    role_arn: Optional[str] = Field(default=None)
    tags: Optional[Dict[str, str]] = Field(default=None)

    @field_validator("notebook_name")
    @classmethod
    def validate_name_length(cls, v: str) -> str:
        """Validate if notebook_name length is valid."""
        if len(v) <= 63:
            return v

        raise ValueError(f"'name' length must be <= 63, got '{len(v)}'")


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
