"""Sagemaker Model Package settings."""
from abc import ABC
from typing import Optional

from pydantic import Field
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


class StackParameters(CdkBaseSettings):
    """Seedfarmer Parameters.

    These parameters are required for the module stack.
    """

    app_prefix: str = Field(exclude=True)
    model_metadata_path: str
    bucket_name: str

    retain_on_delete: bool = Field(default=True)
    model_package_group_name: Optional[str] = Field(default=None)
    kms_key_arn: Optional[str] = Field(default=None)


class CdkDefaultSettings(CdkBaseSettings):
    """CDK Default Settings.

    These parameters comes from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    parameters: StackParameters = Field(default_factory=StackParameters)
    default: CdkDefaultSettings = Field(default_factory=CdkDefaultSettings)
