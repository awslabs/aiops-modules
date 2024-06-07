"""Defines the stack settings."""

from abc import ABC
from typing import Dict, List, Optional

from pydantic import Field, computed_field, model_validator
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


class ModuleSettings(CdkBaseSettings):
    """Seedfarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    vpc_id: str
    subnet_ids: List[str]

    sagemaker_project_id: Optional[str] = Field(default=None)
    sagemaker_project_name: Optional[str] = Field(default=None)
    model_package_arn: Optional[str] = Field(default=None)
    model_package_group_name: Optional[str] = Field(default=None)
    model_execution_role_arn: Optional[str] = Field(default=None)
    model_artifacts_bucket_arn: Optional[str] = Field(default=None)
    ecr_repo_arn: Optional[str] = Field(default=None)
    variant_name: str = Field(default="AllTraffic")

    initial_instance_count: int = Field(default=1)
    initial_variant_weight: int = Field(default=1)
    instance_type: str = Field(default="ml.m4.xlarge")
    managed_instance_scaling: bool = Field(default=False)
    scaling_min_instance_count: int = Field(default=1)
    scaling_max_instance_count: int = Field(default=10)

    # Set to a percentage greater than 0 to enable data capture.
    data_capture_sampling_percentage: int = Field(default=0, ge=0, le=100)
    data_capture_prefix: str = Field(default="")

    tags: Optional[Dict[str, str]] = Field(default=None)

    @model_validator(mode="after")
    def check_model_package(self) -> "ModuleSettings":
        if not self.model_package_arn and not self.model_package_group_name:
            raise ValueError("Parameter model-package-arn or model-package-group-name is required")

        return self


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


class CDKSettings(CdkBaseSettings):
    """CDK Default Settings.

    These parameters come from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    seedfarmer_settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    module_settings: ModuleSettings = Field(default_factory=ModuleSettings)
    cdk_settings: CDKSettings = Field(default_factory=CDKSettings)
