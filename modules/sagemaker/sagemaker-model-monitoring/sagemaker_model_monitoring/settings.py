"""Defines the stack settings."""

from abc import ABC
from typing import List, Optional

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
    """SeedFarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    endpoint_name: str
    security_group_id: str
    subnet_ids: List[str]
    model_package_arn: str
    model_bucket_arn: str
    kms_key_id: str

    sagemaker_project_id: Optional[str] = Field(default=None)
    sagemaker_project_name: Optional[str] = Field(default=None)

    # Data quality monitoring options.
    data_quality_checkstep_output_prefix: str = Field(default="")
    data_quality_output_prefix: str = Field(default="")
    data_quality_instance_count: int = Field(default=1, ge=1)
    data_quality_instance_type: str = Field(default="ml.m5.large")
    data_quality_instance_volume_size_in_gb: int = Field(default=20, ge=1)
    data_quality_max_runtime_in_seconds: int = Field(default=3600, ge=1)
    data_quality_schedule_expression: str = Field(default="cron(0 * ? * * *)")


class SeedFarmerSettings(CdkBaseSettings):
    """SeedFarmer Settings.

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
    """CDK default Settings.

    These parameters come from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    parameters: SeedFarmerParameters = Field(default_factory=SeedFarmerParameters)  # type: ignore[arg-type]
    default: CdkDefaultSettings = Field(default_factory=CdkDefaultSettings)  # type: ignore[arg-type]
